import ruter_chatbot.specs.nodes.generators as g
import ruter_chatbot.specs.nodes.retrievers as r
import ruter_chatbot.specs.nodes.tools as t

from ruter_chatbot.types.iac.graph_spec import GraphSpec, GraphCompileArgs
from ruter_chatbot.types.iac.edge_spec import (
    SimpleEdgeSpec,
    RouterEdgeSpec,
    ToolsConditionEdgeSpec,
)

demo = GraphSpec( 
        state_key="structured_rag",
        compile_args=GraphCompileArgs(use_memory=False),
        nodes=[
            r.retriever_ruter_aws,
            g.llm_qwen_medium_answer,
        ],
        edges=[
            SimpleEdgeSpec(
                source=r.retriever_ruter_aws.name,
                target=g.llm_qwen_medium_answer.name,
            )
        ],
    )
''' Different demo setup'''

conditional_demo = GraphSpec(
        state_key="structured_rag",
        compile_args=GraphCompileArgs(use_memory=True),
        nodes=[
            g.llm_claude_route_choice,
            r.retriever_ruter_aws_big,
            g.llm_claude_rag_answer,
        ],
        edges=[
            RouterEdgeSpec(
                source=g.llm_claude_route_choice.name,
                state_route_field="route",
                routes={
                    "search": r.retriever_ruter_aws_big.name,
                    "chat": g.llm_claude_rag_answer.name,
                },
                default_target=g.llm_claude_rag_answer.name,
            ),
            SimpleEdgeSpec(
                source=r.retriever_ruter_aws_big.name,
                target=g.llm_claude_rag_answer.name,
            ),
        ],
    )
'''Demo of conditional branching'''
    
aws_demo = GraphSpec(
        state_key="structured_rag",
        compile_args=GraphCompileArgs(use_memory=False),
        nodes=[
            r.retriever_ruter_aws,
            g.llm_claude_rag_no_history_answer,
        ],
        edges=[
            SimpleEdgeSpec(
                source=r.retriever_ruter_aws.name,
                target=g.llm_claude_rag_no_history_answer.name,
            ),
        ],
    )
'''AWS Bedrock DEMO'''

ruter_tools_demo = GraphSpec(
        state_key="structured_rag",
        compile_args=GraphCompileArgs(use_memory=True),
        nodes=[
            g.llm_claude_ruter_tool_chat,
            t.ruter_tools,
        ],
        edges=[
            ToolsConditionEdgeSpec(
                source=g.llm_claude_ruter_tool_chat.name,
                tool_target=t.ruter_tools.name,
            ),
            SimpleEdgeSpec(
                source=t.ruter_tools.name,
                target=g.llm_claude_ruter_tool_chat.name,
            ),
        ],
    )
'''Demo of a Ruter-specific realtime departures tool loop.'''



GRAPHS: dict[str, GraphSpec] = {
    #"demo": demo,
    "conditional_demo": conditional_demo,
    "aws_demo": aws_demo,
    "ruter_tools_demo": ruter_tools_demo,
}
'''Registry of Graphs that are in active use.'''
