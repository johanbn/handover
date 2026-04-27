from __future__ import annotations

import os
from dataclasses import asdict
from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command

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


def build_request_docs_tool():

    @tool
    def  request_docs(query: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> dict:
        """
        Requests additional documentation by routing to standard retrieval with requested query.
        NOTE: This tool is single-use per turn. One call retrieves up to several (k) documents, where (k) is not hardcoded.
        Use this for fares, ticketing, rules, products, customer service, and other knowledge questions.
        """

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Routing to retrieval with query: {query}",
                        tool_call_id=tool_call_id
                    )
                ],
                "route": "retrieval",
                "query": query,
            }
        )

    return request_docs
