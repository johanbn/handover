from pydantic import BaseModel, Field, model_validator

from ruter_chatbot.types.iac.edge_spec import EdgeSpec, RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.node_spec import NodeSpec


class GraphCompileArgs(BaseModel):
    use_memory: bool = False


class GraphSpec(BaseModel):
    state_key: str
    """Key to state registry in specs"""

    nodes: list[NodeSpec]
    edges: list[EdgeSpec]
    compile_args: GraphCompileArgs = Field(default_factory=GraphCompileArgs)

    @model_validator(mode="after")
    def validate_graph(self):
        node_names: set[str] = {n.name for n in self.nodes}

        if len(node_names) != len(self.nodes):
            raise ValueError("Duplicate node names detected.")

        for edge in self.edges:
            if edge.source not in node_names:
                raise ValueError(f"Edge source '{edge.source}' not found.")

            if isinstance(edge, SimpleEdgeSpec):
                if edge.target not in node_names:
                    raise ValueError(f"Edge target '{edge.target}' not found.")

            elif isinstance(edge, RouterEdgeSpec):
                for label, target in edge.routes.items():
                    if target not in node_names:
                        raise ValueError(
                            f"Router route '{label}' points to unknown node '{target}'."
                        )

                if edge.default_target and edge.default_target not in node_names:
                    raise ValueError(
                        f"Detected edge with fallback to unknown node: '{edge.default_target}'"
                    )

            else:
                raise ValueError(f"Invalid edge type detected: {type(edge)}")

        return self