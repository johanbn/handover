from __future__ import annotations

import os
from dataclasses import asdict

from langchain_core.tools import tool

from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.utility.ruter_entur_api import EnturRealtimeClient


def _resolve_client_name(client_name: str | None = None) -> str:
    resolved = client_name or os.getenv("RUTER_ENTUR_CLIENT_NAME") or "mycompany-ruter-demo"
    if "-" not in resolved:
        raise ValueError(
            "Ruter/Entur client name must contain '-' and look like '<company>-<application>'."
        )
    return resolved


def build_search_ruter_stops_tool(client_name: str | None = None):
    client = EnturRealtimeClient(client_name=_resolve_client_name(client_name))

    @tool
    def search_ruter_stops(query: str, size: int = 5) -> list[dict]:
        """
        Search for public transport stops by name.
        Use this when the user provides a stop name and you need a stop ID first.
        """

        return client.search_stops(text=query, size=size)

    return search_ruter_stops


def build_get_ruter_departures_tool(client_name: str | None = None):
    client = EnturRealtimeClient(client_name=_resolve_client_name(client_name))

    @tool
    def get_ruter_departures(
        stop_id: str,
        time_range_seconds: int = 1800,
        limit: int = 8,
    ) -> dict:
        """
        Get realtime departures for a stop ID.
        Use this after you have found the stop ID with search_ruter_stops.
        If the result says found=false, do not retry the same stop_id.
        Find a better stop with search_ruter_stops or ask for clarification instead.
        """

        board = client.get_departures(
            stop_id=stop_id,
            time_range_seconds=time_range_seconds,
            limit=limit,
        )
        return {
            "found": board.get("found", True),
            "retryable": board.get("retryable", True),
            "stop_id": board["stop_id"],
            "stop_name": board["stop_name"],
            "error": board.get("error"),
            "departures": [asdict(dep) for dep in board["departures"]],
        }

    return get_ruter_departures


def build_plan_ruter_journey_tool(client_name: str | None = None):
    client = EnturRealtimeClient(client_name=_resolve_client_name(client_name))

    @tool
    def plan_ruter_journey(
        from_place: str,
        to_place: str,
        # Ask Entur for a broader default set so the assistant can present
        # multiple realistic choices instead of only the top few.
        num_trip_patterns: int = 10,
        walk_reluctance: float = 1.0,
    ) -> dict:
        """
        Plan a public transport journey between two places in Norway.
        Use this when the user asks how to travel from one place to another.
        If the result says found=false, do not retry the same place names blindly.
        Resolve the missing place with search_ruter_stops or ask for clarification instead.
        """

        journey = client.plan_journey(
            from_text=from_place,
            to_text=to_place,
            num_trip_patterns=num_trip_patterns,
            walk_reluctance=walk_reluctance,
        )
        return {
            "found": journey.get("found", True),
            "retryable": journey.get("retryable", True),
            "from": journey["from"],
            "to": journey["to"],
            "error": journey.get("error"),
            "invalid_place": journey.get("invalid_place"),
            "journeys": [
                {
                    **asdict(option),
                    "legs": [asdict(leg) for leg in option.legs],
                }
                for option in journey["journeys"]
            ],
        }

    return plan_ruter_journey


def build_lookup_ruter_line_tool(client_name: str | None = None):
    client = EnturRealtimeClient(client_name=_resolve_client_name(client_name))

    @tool
    def lookup_ruter_line(
        line_code: str,
        via_stop: str | None = None,
    ) -> dict:
        """
        Look up a Ruter line and its stop patterns across transport types.
        Use this for questions about whether a line goes via a stop,
        or which stops a specific line serves.
        """

        normalized_line_code = line_code.strip()
        try:
            line = client.get_line_patterns(
                public_code=normalized_line_code,
                authority_id="RUT:Authority:RUT",
                transport_modes=["bus", "tram", "metro", "rail", "water"],
                via_stop_text=via_stop,
            )
        except ValueError as exc:
            return {
                "found": False,
                "line_code": normalized_line_code,
                "via_stop": via_stop,
                "error": str(exc),
                "line": None,
                "patterns": [],
                "via_stop_check": None,
            }
        return {
            "found": True,
            "line": line["line"],
            "patterns": [
                {
                    **asdict(pattern),
                    "stops": [asdict(stop) for stop in pattern.stops],
                }
                for pattern in line["patterns"]
            ],
            "via_stop_check": line.get("via_stop_check"),
        }

    return lookup_ruter_line


def build_search_ruter_docs_tool(
    vector_stores: VectorStoreRegistry,
    *,
    store_key: str | None = None,
    search_type: str = "mmr",
    top_k: int | None = None,
    fetch_k: int | None = None,
    lambda_mult: float | None = None,
):
    if store_key is None:
        store_keys = list(vector_stores.keys())
        if len(store_keys) == 1:
            store_key = store_keys[0]
        else:
            raise ValueError(
                "search_ruter_docs requires an explicit store_key when multiple vector stores are available."
            )

    @tool
    def search_ruter_docs(query: str) -> dict:
        """
        Search Ruter documentation and return the most relevant passages.
        Use this for fares, ticketing, rules, products, customer service, and other knowledge questions.
        """

        store = vector_stores.get(store_key)

        if search_type == "mmr":
            mmr_kwargs: dict[str, float | int] = {}
            if top_k is not None:
                mmr_kwargs["k"] = top_k
            if fetch_k is not None:
                mmr_kwargs["fetch_k"] = fetch_k
            if lambda_mult is not None:
                mmr_kwargs["lambda_mult"] = lambda_mult
            docs = store.max_marginal_relevance_search(query, **mmr_kwargs)
        elif search_type == "similarity":
            similarity_kwargs: dict[str, int | bool] = {"with_score": False}
            if top_k is not None:
                similarity_kwargs["k"] = top_k
            docs = store.similarity_search(query, **similarity_kwargs)
        else:
            raise ValueError(f"Unsupported search_type for search_ruter_docs: {search_type}")

        return {
            "store_key": store_key,
            "query": query,
            "hits": [
                {
                    "page_content": doc.page_content,
                    "metadata": dict(doc.metadata),
                }
                for doc in docs
            ],
        }

    return search_ruter_docs
