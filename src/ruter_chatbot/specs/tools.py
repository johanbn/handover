from ruter_chatbot.types.iac.tool_spec import ToolSpec

ruter_search_stops = ToolSpec(
    key="search_ruter_stops",
    type="builtin",
    args={"client_name": "mycompany-ruter-demo"},
)

ruter_get_departures = ToolSpec(
    key="get_ruter_departures",
    type="builtin",
    args={"client_name": "mycompany-ruter-demo"},
)

ruter_plan_journey = ToolSpec(
    key="plan_ruter_journey",
    type="builtin",
    args={"client_name": "mycompany-ruter-demo"},
)

ruter_lookup_line = ToolSpec(
    key="lookup_ruter_line",
    type="builtin",
    args={"client_name": "mycompany-ruter-demo"},
)

ruter_search_docs = ToolSpec(
    key="search_ruter_docs",
    type="builtin",
    args={
        "store_key": "ruter_store_aws",
        "search_type": "mmr",
        "top_k": 5,
        "fetch_k": 20,
        "lambda_mult": 0.5,
    },
)


TOOLS: dict[str, ToolSpec] = {
    "search_ruter_stops": ruter_search_stops,
    "get_ruter_departures": ruter_get_departures,
    "plan_ruter_journey": ruter_plan_journey,
    "lookup_ruter_line": ruter_lookup_line,
    "search_ruter_docs": ruter_search_docs,
}
