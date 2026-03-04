"""
Config-driven LangGraph + LangChain + Ollama RAG demo.

Pipeline (single graph invocation):

  START
    ↓
  extract_question   (kind: passthrough)
      - Reads the latest human message
      - Normalizes/cleans it
      - Writes state["question"]
      - Pure state transformation (no external systems)

    ↓
  retrieve           (kind: retriever)
      - Uses state["question"]
      - Queries the vector store (Chroma)
      - Writes state["docs"]
      - External data lookup

    ↓
  format_context     (kind: prompt)
      - Converts retrieved Documents into a single context string
      - Truncates if needed
      - Writes state["context"]
      - Structured data → text transformation

    ↓
  generate           (kind: llm)
      - Builds final prompt using {question} + {context}
      - Calls the chat model (Ollama)
      - Writes state["answer"] and appends assistant message
      - Generative model invocation

    ↓
  END


Node kinds (behavior categories):

  passthrough  → Pure state transformation (no external calls)
  retriever    → External knowledge lookup (e.g., vector DB)
  prompt       → Structured data → formatted prompt text
  llm          → LLM invocation (text generation)

NOTE:
LangGraph nodes can return *partial updates* to the shared state (RagState).
Each node should return only the fields it updates (e.g., {"docs": docs}),
and LangGraph will merge these updates into the current state.
"""

from __future__ import annotations

import os
import re
import json
from typing import Any, Callable, Literal, TypedDict, Optional

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.graph import StateGraph, START, END
from langchain_community.vectorstores import Chroma, FAISS


# -----------------------------
# State definition for RAG pipeline
# this is what is shared across all nodes, and what the graph operates on.
# each node decides what fields it needs to read/write.
# -----------------------------
class RagState(TypedDict):
    messages: list[AnyMessage]
    question: str
    docs: list[Document]
    context: str
    answer: str


# -----------------------------
# IaC spec types
# -----------------------------
NodeKind = Literal["passthrough", "retriever", "prompt", "llm"]


class NodeSpec(TypedDict):
    name: str
    kind: NodeKind
    config: dict[str, Any]


class EdgeSpec(TypedDict):
    source: str
    target: str


class GraphSpecification(TypedDict):
    nodes: list[NodeSpec]
    edges: list[EdgeSpec]
    compile_args: dict[str, Any]


# -----------------------------
# Vector store setup
# -----------------------------
if True:
    DEMO_DOCS = [
        Document(page_content="Auticon is a company focused on employing autistic IT consultants."),
        Document(page_content="LangGraph is a library for building stateful, multi-step LLM applications as graphs."),
        Document(page_content="In LangChain, a Document contains page_content and optional metadata."),
        Document(page_content="Ollama lets you run LLMs locally and exposes a local HTTP API (usually on port 11434)."),
        Document(page_content="Chroma is a vector database that can run locally and is often used for prototyping RAG."),
    ]
else:
    from confluence_ingest import chunks
    DEMO_DOCS = chunks


class VectorStore:
    def __init__(self, spec: dict[str, Any]) -> None:
        self.vector_factory: dict[str, Callable[[dict[str, Any]], Any]] = {
            "chroma": self._make_chroma_db,
            # "faiss": self._make_FAISS_db, # TODO?
        }
        self.vector_store = self._build_vector_store(spec)

    def _build_vector_store(self, spec: dict[str, Any]) -> Any:
        vs_spec = spec["vector_store_spec"]
        maker = self.vector_factory[vs_spec["vector_store"]]
        return maker(spec)

    def _make_chroma_db(self, spec: dict[str, Any]) -> Chroma:
        cfg = dict(spec["vector_store_spec"]["cfg"])  # don’t mutate original
        cfg["embedding_function"] = OllamaEmbeddings(model=spec["embed_spec"]["name"])
        cfg["persist_directory"] = os.path.join(os.getcwd(), ".local", cfg["persist_directory"])
        os.makedirs(cfg["persist_directory"], exist_ok=True)
        return Chroma(**cfg)

    def similarity_search(self, query: str, k: int = 4):
        return self.vector_store.similarity_search(query, k=k)

    def add_documents(self, docs):
        return self.vector_store.add_documents(docs)


# -----------------------------
# Orchestrator
# -----------------------------
class Orchestrator:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg

        # Node config may override this explicitly.
        self.default_model: str = self.cfg.get("default_model", "qwen2.5:3b")

        # Factory pattern for node function builders.
        # Maps node kinds to functions that take a config and return a node function.
        self.node_factory: dict[
            NodeKind, Callable[[dict[str, Any]], Callable[[RagState], dict[str, Any]]]
        ] = {
            "passthrough": self._make_passthrough_node,
            "retriever": self._make_retriever_node,
            "prompt": self._make_prompt_node,
            "llm": self._make_llm_node,
        }

        if self.cfg.get("vector_db_spec"):
            self.vector_stores = self.get_vector_stores(self.cfg["vector_db_spec"]["nodes"])

        if self.cfg.get("graph_spec"):
            self.graph = self.build_graph(self.cfg["graph_spec"])

    def get_vector_stores(self, spec):
        d = {}
        for s in spec:
            d[s["vector_store_spec"]["name"]] = VectorStore(s)
        return d

    def build_graph(self, graph_spec: GraphSpecification):
        builder = StateGraph(RagState)

        for node in graph_spec["nodes"]:
            builder.add_node(node["name"], self._build_node_fn(node))

        for e in graph_spec["edges"]:
            builder.add_edge(e["source"], e["target"])

        if not graph_spec["edges"]:
            raise ValueError("GraphSpecification.edges is empty")

        builder.add_edge(START, graph_spec["edges"][0]["source"])
        builder.add_edge(graph_spec["edges"][-1]["target"], END)

        return builder.compile(**graph_spec.get("compile_args", {}))

    def _build_node_fn(self, node_spec: NodeSpec) -> Callable[[RagState], dict[str, Any]]:
        maker = self.node_factory[node_spec["kind"]]
        return maker(node_spec["config"])

    # --- Node makers for the factory ---

    def _make_passthrough_node(
        self, config: dict[str, Any]
    ) -> Callable[[RagState], dict[str, Any]]:
        """
        Extract last human message -> state["question"] (whitespace-normalized).
        """
        field = config.get("field", "question")

        def extract(state: RagState) -> dict[str, Any]:
            q = ""
            for m in reversed(state["messages"]):
                if getattr(m, "type", None) == "human":
                    q = (getattr(m, "content", "") or "").strip()
                    break

            q_norm = re.sub(r"\s+", " ", q).strip()
            return {field: q_norm}

        return extract

    def _make_retriever_node(
        self, config: dict[str, Any]
    ) -> Callable[[RagState], dict[str, Any]]:
        k = int(config.get("k", 4))

        # Allow choosing which store to use.
        # If omitted, we default to "the first configured store".
        store_name: Optional[str] = config.get("vector_store")
        if store_name is None:
            store_name = next(iter(self.vector_stores.keys()), None)

        if not store_name or store_name not in self.vector_stores:
            raise ValueError(
                f"Retriever node needs a valid vector_store name. "
                f"Got {store_name!r}. Available: {list(self.vector_stores.keys())}"
            )

        store = self.vector_stores[store_name]

        def retrieve(state: RagState) -> dict[str, Any]:
            question = state["question"]
            docs = store.similarity_search(question, k=k)
            return {"docs": docs}

        return retrieve

    def _make_prompt_node(
        self, config: dict[str, Any]
    ) -> Callable[[RagState], dict[str, Any]]:
        max_chars = int(config.get("max_chars", 6000))

        def format_context(state: RagState) -> dict[str, Any]:
            docs = state.get("docs", [])
            context = "\n\n".join(
                f"[Doc {i}]\n{(d.page_content or '').strip()}"
                for i, d in enumerate(docs, start=1)
            )
            return {"context": context[:max_chars]}

        return format_context

    def _resolve_model_name(self, config: dict[str, Any]) -> str:
        if config.get("model_name"):
            return str(config["model_name"])
        return self.default_model

    def _make_llm_node(
        self, config: dict[str, Any]
    ) -> Callable[[RagState], dict[str, Any]]:
        model_name = self._resolve_model_name(config)
        prompt = config["prompt"]
        llm = ChatOllama(model=model_name)

        include_history = bool(config.get("include_history", True))
        history_window = int(config.get("history_window", 6))
        debug_prompt = bool(config.get("debug_prompt", False))

        def generate(state: RagState) -> dict[str, Any]:
            # string template prompt formatting with {question} and {context}
            question_and_retrived_context = prompt.format(
                question=state["question"],
                context=state.get("context", ""),
            )

            history: list[AnyMessage] = []
            if include_history:
                history = state.get("messages", [])[-history_window:]

            messages = [
                *history,
                HumanMessage(content=question_and_retrived_context),
            ]

            if debug_prompt:
                print("\n--- LLM Prompt ---")
                for i, m in enumerate(messages):
                    print(f"Content of message {i}:")
                    print(m.content)
                    print("type:", type(m))
                    print("-----------------------")
                print("--- End Prompt ---\n")

            resp = llm.invoke(messages)

            return {
                "answer": getattr(resp, "content", ""),  # "" if content is missing or None
                "messages": state["messages"] + [resp],
            }

        return generate


# -----------------------------
# Optional graph visualization
# -----------------------------
def draw_graph_png(graph, file_path: str = "graph.png") -> None:
    import sys

    try:
        g = graph.get_graph(xray=True)
        png_bytes = g.draw_mermaid_png()

        with open(file_path, "wb") as f:
            f.write(png_bytes)

        print(f"\nGraph visualization saved to: {file_path}")

        if sys.platform.startswith("win"):
            os.startfile(file_path)

    except Exception as e:
        print("\nCould not render graph visualization.")
        print("Error:", e)


def print_spec(spec: dict) -> None:
    print("\n================= IaC APP CONFIG =================")
    print(json.dumps(spec, indent=2))
    print("==================================================")


# -----------------------------
# Main
# -----------------------------
def main():
    # --- Pure IaC defaults (edit here to swap models / knobs) ---
    debug_spec = {  # fix type here
        "show_docs": False,
        "draw_graph": True,
    }

    vector_db_spec = {
        "nodes": [
            {
                "embed_spec": {"name": "nomic-embed-text", "type": "ollama"},
                "vector_store_spec": {
                    "name": "chroma-nomic",
                    "vector_store": "chroma",
                    "cfg": {"persist_directory": "chroma_demo", "collection_name": "demo"},
                },
            },
            {
                "embed_spec": {"name": "nomic-embed-text", "type": "ollama"},
                "vector_store_spec": {
                    "name": "chroma-nomic2",
                    "vector_store": "chroma",
                    "cfg": {"persist_directory": "chroma_demo", "collection_name": "demo"},
                },
            },
        ]
    }

    defualt_prompt = {
        "prompt": (
            "You are a helpful assistant.\n\n"
            "You may use BOTH:\n"
            "1) The retrieved context below\n"
            "2) The prior conversation history\n\n"
            "Rules:\n"
            "- For factual questions, rely on the retrieved context.\n"
            "- For questions about the user or prior conversation, rely on the conversation history.\n"
            "- If the answer cannot be found in either, say you don't know.\n\n"
            "Retrieved Context:\n{context}\n\n"
            "Current Question:\n{question}\n\n"
            "Answer:"
        )
    }

    defualt_chat_node_config = {
        "model_name": "qwen2.5:3b",
        "include_history": True,
        "history_window": 6,  # Make even to make sure of QA pairs in history
        "prompt": defualt_prompt["prompt"],
        # optional, to get your old printouts back
        "debug_prompt": False,
    }

    graph_spec: GraphSpecification = {
        "nodes": [
            {"name": "extract_question", "kind": "passthrough", "config": {"field": "question"}},
            # With multiple vector stores configured, pick one explicitly.
            {"name": "retrieve", "kind": "retriever", "config": {"k": 6, "vector_store": "chroma-nomic"}},
            {"name": "format_context", "kind": "prompt", "config": {"max_chars": 6000}},
            {
                "name": "generate",
                "kind": "llm",
                "config": defualt_chat_node_config,
            },
        ],
        "edges": [
            {"source": "extract_question", "target": "retrieve"},
            {"source": "retrieve", "target": "format_context"},
            {"source": "format_context", "target": "generate"},
        ],
        "compile_args": {},
    }

    full_spec = {
        "vector_db_spec": vector_db_spec,
        "graph_spec": graph_spec,
    }

    print_spec(full_spec)
    orch = Orchestrator(full_spec)

    # Should go into orchestrator?
    if debug_spec["draw_graph"] and orch.graph is not None:
        draw_graph_png(orch.graph, "graph.png")

    print("\nIaC LangGraph RAG demo. Type a question and press Enter. Type 'exit' to quit.\n")

    state: RagState = {"messages": [], "question": "", "docs": [], "context": "", "answer": ""}

    # If you want true "no demo behavior", delete this block.
    try:
        for store in orch.vector_stores.values():
            store.add_documents(DEMO_DOCS)
    except Exception:
        pass

    while True:
        q = input("You: ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break

        # Only update messages here; the graph updates question/docs/context/answer.
        state = {**state, "messages": state["messages"] + [HumanMessage(content=q)]}
        out = orch.graph.invoke(state)
        state = out

        if debug_spec["show_docs"]:
            print("\n--- Retrieved docs ---")
            for i, d in enumerate(out.get("docs", []), start=1):
                print(f"{i}. {d.page_content}")
            print("---")

        print("\nAssistant:", out.get("answer", ""))
        print("")


if __name__ == "__main__":
    main()