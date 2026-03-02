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
from typing import Any, Callable, Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.graph import StateGraph, START, END
from langchain_community.vectorstores import Chroma


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

class PromptSpec(TypedDict):
    prompt: str

class ChatNodeConfig(TypedDict):
    model_key: dict[str, str]  # Reference to a model in AppConfig.models
    include_history: bool
    history_window: int
    prompt: PromptSpec

class GraphSpecification(TypedDict):
    nodes: list[NodeSpec]
    edges: list[EdgeSpec]
    compile_args: dict[str, Any]


# -----------------------------
# IaC App Config (models + runtime knobs)
# This is the place a new user should edit to swap models, etc.
# (No env overrides in this version; pure IaC defaults.)
# -----------------------------
class ModelConfig(TypedDict):
    chat: str
    embed: str


class AppConfig(TypedDict):
    models: ModelConfig
    top_k: int
    show_docs: bool
    draw_graph: bool


# -----------------------------
# Orchestrator
# -----------------------------
class Orchestrator:
    def __init__(self, cfg: dict[str, Any]):
        self.vector_store = cfg["vector_store"]

        # Model registry / IaC-controlled defaults
        self.models: dict[str, str] = cfg.get("models", {})
        self.default_model: str = cfg.get("model", self.models.get("chat", "qwen2.5:3b"))

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

        def retrieve(state: RagState) -> dict[str, Any]:
            question = state["question"]
            docs = self.vector_store.similarity_search(question, k=k)
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
        """
        IaC model resolution:
        - if config has "model": use it directly (explicit override)
        - else if config has "model_key": look up in orchestrator cfg models (e.g. "chat")
        - else: fall back to orchestrator default_model
        """
        if "model" in config and config["model"]:
            return str(config["model"])
        model_key = config.get("model_key")
        if model_key:
            return self.models.get(str(model_key), self.default_model)
        return self.default_model

    def _make_llm_node(
        self, config: dict[str, Any]
    ) -> Callable[[RagState], dict[str, Any]]:
        model_name = self._resolve_model_name(config)
        prompt = config["prompt"]
        # This should support other interfaces eg. HF?? How to resolve if needed?
        llm = ChatOllama(model=model_name)
        """
        Ollama and Hugging Face are both pivotal tools in the AI ecosystem,
        but they serve different primary purposes: Ollama is a tool for easily
        running LLMs locally, while Hugging Face is the central repository and
        platform for finding, training, and deploying models.
        They are often used together: Hugging Face acts as the source for models,
        which are then downloaded and run locally using Ollama

        Given this post; we maybe can only use Ollama only? Or we are compute bound and need HF?
        """

        include_history = bool(config.get("include_history", True))
        history_window = int(config.get("history_window", 6))

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

            if True:
                print("\n--- LLM Prompt ---")
                for i, m in enumerate(messages):
                    print(f"Content of message {i}:")
                    print(m.content)
                    print("type:", type(m))
                    print("-----------------------")
                print("--- End Prompt ---\n")

            history: list[AnyMessage] = []
            if include_history:
                history = state.get("messages", [])[-history_window:]

            resp = llm.invoke(messages)

            print("********************")
            print("RESPONSE from LLM:")
            print(resp)
            print("type:", type(resp))
            print("********************")

             # Return ONLY what this node updates
            return {
                "answer": getattr(resp, "content", ""),  # "" if content is missing or None
                "messages": state["messages"] + [resp],
            }

        return generate


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

def get_or_build_vector_store(
    embed_model: str,
    persist_subdir: str = "chroma_demo",
) -> Chroma:
    """
    Dev-friendly persistent Chroma DB inside .local/
    - Loads if exists
    - Builds if missing
    """

    embeddings = OllamaEmbeddings(model=embed_model)

    # Base .local directory in project root
    project_root = os.getcwd()
    local_dir = os.path.join(project_root, ".local")
    persist_dir = os.path.join(local_dir, persist_subdir)

    # Ensure .local exists
    os.makedirs(local_dir, exist_ok=True)

    # If DB already exists, load it
    if os.path.isdir(persist_dir) and os.listdir(persist_dir):
        print(f"Loading existing vector store from: {persist_dir}")
        return Chroma(
            collection_name="demo",
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )

    # Otherwise build and persist
    print(f"Building new vector store at: {persist_dir}")
    print(f"Embedding {len(DEMO_DOCS)} documents using model: {embed_model}")

    os.makedirs(persist_dir, exist_ok=True)

    return Chroma.from_documents(
        documents=DEMO_DOCS,
        embedding=embeddings,
        collection_name="demo",
        persist_directory=persist_dir,
    )
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


def print_configs(app_cfg: AppConfig, graph_spec: GraphSpecification) -> None:
    print("\n================= IaC APP CONFIG =================")
    print(json.dumps(app_cfg, indent=2))
    print("==================================================")

    print("\n================= GRAPH SPEC =====================")
    print(json.dumps(graph_spec, indent=2))
    print("==================================================\n")


# -----------------------------
# Main
# -----------------------------
def main():
    # --- Pure IaC defaults (edit here to swap models / knobs) ---
    # Not so sure if we need both AppConfig and GraphSpecification? Maybe we can merge them?
    # Or is it nice to have the separation of "runtime configs" vs "graph structure" at least from a
    # readability perspective?
    app_cfg: AppConfig = {
        "models": {
            "chat": "qwen2.5:3b",
            "embed": "nomic-embed-text",
        },
        "top_k": 6,
        "show_docs": False,
        "draw_graph": True,
    }

    # IaC-controlled models embedder and retriver setup
    chat_model = app_cfg["models"]["chat"]
    embed_model = app_cfg["models"]["embed"]
    top_k = app_cfg["top_k"]
    show_docs = app_cfg["show_docs"]
    draw = app_cfg["draw_graph"]

    # This is done on a time scheduele? Eg. once per night? Or on demand.
    vs = get_or_build_vector_store(embed_model)
    print("Vector store built and ready.")

    orch = Orchestrator(
        {
            "models": app_cfg["models"],
            "model": chat_model,
            "vector_store": vs,
        }
    )

    defualt_prompt: PromptSpec = {
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

    defualt_chat_node_config: ChatNodeConfig = {
                    # IaC model reference (instead of hardcoding a model string here)
                    # "model_key": "chat" means: use app_cfg["models"]["chat"]
                    "model_key": "chat",
                    "include_history": True,
                    "history_window": 6, # Make even to make sure of QA pairs in history
                    "prompt": defualt_prompt["prompt"],
                }

    graph_spec: GraphSpecification = {
        "nodes": [
            {"name": "extract_question", "kind": "passthrough", "config": {"field": "question"}},
            {"name": "retrieve", "kind": "retriever", "config": {"k": top_k}},
            {"name": "format_context", "kind": "prompt", "config": {"max_chars": 6000}},
            {
                "name": "generate",
                "kind": "llm",
                "config": {
                    # IaC model reference (instead of hardcoding a model string here)
                    # "model_key": "chat" means: use app_cfg["models"]["chat"]
                    "model_key": "chat",
                    "include_history": True,
                    "history_window": 6, # Make even to make sure of QA pairs in history
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
                    ),
                },
            },
        ],
        "edges": [
            {"source": "extract_question", "target": "retrieve"},
            {"source": "retrieve", "target": "format_context"},
            {"source": "format_context", "target": "generate"},
        ],
        "compile_args": {},
    }

    print_configs(app_cfg, graph_spec)

    graph = orch.build_graph(graph_spec)

    print("--------Type Graph------->", type(graph))

    if draw:
        draw_graph_png(graph, "graph.png")

    print("\nIaC LangGraph RAG demo. Type a question and press Enter. Type 'exit' to quit.\n")

    state: RagState = {"messages": [], "question": "", "docs": [], "context": "", "answer": ""}

    while True:
        q = input("You: ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break

        # Only update messages here; the graph updates question/docs/context/answer.
        state = {**state, "messages": state["messages"] + [HumanMessage(content=q)]}
        out = graph.invoke(state)
        state = out

        if show_docs:
            print("\n--- Retrieved docs ---")
            for i, d in enumerate(out.get("docs", []), start=1):
                print(f"{i}. {d.page_content}")
            print("---")

        print("\nAssistant:", out.get("answer", ""))
        print("")


if __name__ == "__main__":
    main()