'''
Provides ToolNodeSpecs.
Note that node names must be unique within a GraphSpec.
However, they can be reused between GraphSpecs.
'''
from ruter_chatbot.types.iac.node_spec import NodeSpec, ToolNodeSpec


ruter_tools: NodeSpec = ToolNodeSpec(
    name="ruter_tools",
    kind="tool",
    tool_keys=["search_ruter_stops", "get_ruter_departures", "plan_ruter_journey", "lookup_ruter_line", "request_docs"],
)
'''Executes the Ruter stop search, departure lookup, journey planning, line lookup, and docs search tools.'''
