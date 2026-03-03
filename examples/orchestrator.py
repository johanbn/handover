from typing import TypedDict, NotRequired, Any, Union, Literal

class GraphSpecification(TypedDict):
    nodes: list
    edges: list
    state_type: NotRequired[type[TypedDict]]
    conditions: NotRequired[dict[str, callable]]
    compile_args: NotRequired[dict[str, Any]]

class LLMNode(TypedDict):
    type: Literal["llm"]
    prompt: str
    output_key: str
    model: str

class RetrieverNode(TypedDict):

NodeSpecification = Union[LLMNode, RetrieverNode]

class Orchestrator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = cfg["model"]
        self.vector_store = cfg["vector_store"]
        self.graph = None

        if self.cfg["graph_specifications"]:
            self.graph = self.build_graph()

        # her vil sette model, og graf.

    def build_graph(self, graph_spec : GraphSpecification):
        # her bygger vi grafen basert på spesifikasjonene, og returnerer den
        builder = GraphBuilder()

        for node_spec in graph_spec["nodes"]:
            builder.add_node(node_spec["name"], node_spec["function"])

        for edge_spec in graph_spec["edges"]:
            builder.add_edge(edge_spec["from_node"], edge_spec["to_node"])

        return builder.compile()
