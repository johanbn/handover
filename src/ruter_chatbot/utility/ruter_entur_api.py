from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import unicodedata

import requests


JOURNEY_PLANNER_URL = "https://api.entur.io/journey-planner/v3/graphql"
GEOCODER_URL = "https://api.entur.io/geocoder/v1/autocomplete"


@dataclass
class Departure:
    line_code: str | None
    line_name: str | None
    transport_mode: str | None
    destination: str | None
    quay_code: str | None
    realtime: bool
    cancelled: bool
    aimed_departure_time: str | None
    expected_departure_time: str | None


@dataclass
class JourneyLeg:
    mode: str | None
    from_place: str | None
    to_place: str | None
    aimed_start_time: str | None
    expected_start_time: str | None
    aimed_end_time: str | None
    expected_end_time: str | None
    line_code: str | None
    line_name: str | None
    transport_submode: str | None


@dataclass
class JourneyOption:
    duration_seconds: int | None
    walk_distance: float | None
    start_time: str | None
    end_time: str | None
    legs: list[JourneyLeg]


@dataclass
class LineStop:
    stop_id: str | None
    stop_name: str | None
    quay_id: str | None
    quay_name: str | None
    quay_code: str | None


@dataclass
class LinePattern:
    id: str
    name: str | None
    direction_type: str | None
    stops: list[LineStop]


class EnturRealtimeClient:
    """
    Minimal client for stop-based realtime departures through Entur Journey Planner v3.
    Works well for Ruter stops because Entur aggregates Norway-wide public transport.
    """

    def __init__(self, client_name: str, timeout: int = 20) -> None:
        if not client_name or "-" not in client_name:
            raise ValueError(
                "client_name must look like '<company>-<application>', "
                "for example 'acme-ruter-monitor'"
            )

        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "ET-Client-Name": client_name,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": client_name,
            }
        )

    def _post_graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            JOURNEY_PLANNER_URL,
            json={"query": query, "variables": variables},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        if "errors" in payload:
            raise RuntimeError(f"GraphQL error: {payload['errors']}")

        return payload["data"]

    def search_stops(self, text: str, size: int = 10) -> list[dict[str, Any]]:
        response = self.session.get(
            GEOCODER_URL,
            params={"text": text, "lang": "no", "size": size},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        stops: list[dict[str, Any]] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            stop_id = props.get("id")
            label = props.get("label")
            if stop_id and label:
                stops.append(
                    {
                        "id": stop_id,
                        "label": label,
                        "category": props.get("category"),
                    }
                )
        return stops

    def _resolve_place_id(self, text: str) -> dict[str, Any]:
        matches = self.search_stops(text=text, size=1)
        if not matches:
            raise ValueError(f"No stop/place found for query={text!r}")
        return matches[0]

    def _normalize_text(self, text: str | None) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text.casefold())
        return "".join(ch for ch in normalized if ch.isalnum())

    def get_departures(
        self,
        stop_id: str,
        time_range_seconds: int = 3600,
        limit: int = 10,
    ) -> dict[str, Any]:
        query = """
        query GetDepartures($stopId: String!, $timeRange: Int!, $limit: Int!) {
          stopPlace(id: $stopId) {
            id
            name
            estimatedCalls(
              timeRange: $timeRange
              numberOfDepartures: $limit
            ) {
              realtime
              cancellation
              aimedDepartureTime
              expectedDepartureTime
              destinationDisplay {
                frontText
              }
              serviceJourney {
                line {
                  publicCode
                  name
                  transportMode
                }
              }
              quay {
                publicCode
              }
            }
          }
        }
        """

        data = self._post_graphql(
            query,
            {
                "stopId": stop_id,
                "timeRange": time_range_seconds,
                "limit": limit,
            },
        )

        stop = data.get("stopPlace")
        if not stop:
            return {
                "found": False,
                "retryable": False,
                "stop_id": stop_id,
                "stop_name": None,
                "departures": [],
                "error": (
                    f"No stopPlace found for stop_id={stop_id!r}. "
                    "Use search_ruter_stops to find a valid stop before retrying departures."
                ),
            }

        departures: list[Departure] = []
        for call in stop.get("estimatedCalls", []):
            line = ((call.get("serviceJourney") or {}).get("line") or {})
            destination_display = call.get("destinationDisplay") or {}
            quay = call.get("quay") or {}

            departures.append(
                Departure(
                    line_code=line.get("publicCode"),
                    line_name=line.get("name"),
                    transport_mode=line.get("transportMode"),
                    destination=destination_display.get("frontText"),
                    quay_code=quay.get("publicCode"),
                    realtime=bool(call.get("realtime")),
                    cancelled=bool(call.get("cancellation")),
                    aimed_departure_time=call.get("aimedDepartureTime"),
                    expected_departure_time=call.get("expectedDepartureTime"),
                )
            )

        return {
            "found": True,
            "retryable": True,
            "stop_id": stop["id"],
            "stop_name": stop["name"],
            "departures": departures,
        }

    def plan_journey(
        self,
        from_text: str,
        to_text: str,
        *,
        num_trip_patterns: int = 10,
        walk_reluctance: float = 1.0,
    ) -> dict[str, Any]:
        try:
            origin = self._resolve_place_id(from_text)
        except ValueError as exc:
            return {
                "found": False,
                "retryable": False,
                "from": None,
                "to": None,
                "journeys": [],
                "error": (
                    f"{exc} Use search_ruter_stops to find a valid origin before retrying journey planning."
                ),
                "invalid_place": "from",
            }

        try:
            destination = self._resolve_place_id(to_text)
        except ValueError as exc:
            return {
                "found": False,
                "retryable": False,
                "from": origin,
                "to": None,
                "journeys": [],
                "error": (
                    f"{exc} Use search_ruter_stops to find a valid destination before retrying journey planning."
                ),
                "invalid_place": "to",
            }

        query = """
        query PlanJourney(
          $fromPlace: String!,
          $toPlace: String!,
          $numTripPatterns: Int!,
          $walkReluctance: Float!
        ) {
          trip(
            from: { place: $fromPlace }
            to: { place: $toPlace }
            numTripPatterns: $numTripPatterns
            walkReluctance: $walkReluctance
          ) {
            tripPatterns {
              duration
              walkDistance
              startTime
              endTime
              legs {
                mode
                transportSubmode
                aimedStartTime
                expectedStartTime
                aimedEndTime
                expectedEndTime
                fromPlace {
                  name
                }
                toPlace {
                  name
                }
                line {
                  publicCode
                  name
                }
              }
            }
          }
        }
        """

        data = self._post_graphql(
            query,
            {
                "fromPlace": origin["id"],
                "toPlace": destination["id"],
                "numTripPatterns": num_trip_patterns,
                "walkReluctance": walk_reluctance,
            },
        )

        trip = data.get("trip") or {}
        patterns = trip.get("tripPatterns") or []

        journeys: list[JourneyOption] = []
        for pattern in patterns:
            legs: list[JourneyLeg] = []
            for leg in pattern.get("legs", []):
                line = leg.get("line") or {}
                from_place = leg.get("fromPlace") or {}
                to_place = leg.get("toPlace") or {}

                legs.append(
                    JourneyLeg(
                        mode=leg.get("mode"),
                        from_place=from_place.get("name"),
                        to_place=to_place.get("name"),
                        aimed_start_time=leg.get("aimedStartTime"),
                        expected_start_time=leg.get("expectedStartTime"),
                        aimed_end_time=leg.get("aimedEndTime"),
                        expected_end_time=leg.get("expectedEndTime"),
                        line_code=line.get("publicCode"),
                        line_name=line.get("name"),
                        transport_submode=leg.get("transportSubmode"),
                    )
                )

            journeys.append(
                JourneyOption(
                    duration_seconds=pattern.get("duration"),
                    walk_distance=pattern.get("walkDistance"),
                    start_time=pattern.get("startTime"),
                    end_time=pattern.get("endTime"),
                    legs=legs,
                )
            )

        return {
            "found": True,
            "retryable": True,
            "from": origin,
            "to": destination,
            "journeys": journeys,
        }

    def get_line_patterns(
        self,
        public_code: str,
        *,
        authority_id: str = "RUT:Authority:RUT",
        transport_modes: list[str] | None = None,
        via_stop_text: str | None = None,
    ) -> dict[str, Any]:
        query = """
        query GetLinePatterns(
          $publicCode: String!,
          $authorityIds: [String!],
          $transportModes: [TransportMode!]
        ) {
          lines(
            publicCode: $publicCode
            authorities: $authorityIds
            transportModes: $transportModes
          ) {
            id
            publicCode
            name
            authority {
              id
              name
            }
            transportMode
            journeyPatterns {
              id
              name
              directionType
              quays {
                id
                name
                publicCode
                stopPlace {
                  id
                  name
                }
              }
            }
          }
        }
        """

        data = self._post_graphql(
            query,
            {
                "publicCode": public_code,
                "authorityIds": [authority_id],
                "transportModes": transport_modes
                or ["bus", "tram", "metro", "rail", "water"],
            },
        )

        lines = data.get("lines") or []
        if not lines:
            raise ValueError(
                f"No line found for public_code={public_code!r} authority_id={authority_id!r}"
            )

        line = lines[0]
        patterns: list[LinePattern] = []

        for pattern in line.get("journeyPatterns", []):
            stops: list[LineStop] = []
            seen_stop_ids: set[str] = set()

            for quay in pattern.get("quays", []):
                stop_place = quay.get("stopPlace") or {}
                stop_id = stop_place.get("id")
                if stop_id and stop_id in seen_stop_ids:
                    continue
                if stop_id:
                    seen_stop_ids.add(stop_id)

                stops.append(
                    LineStop(
                        stop_id=stop_id,
                        stop_name=stop_place.get("name"),
                        quay_id=quay.get("id"),
                        quay_name=quay.get("name"),
                        quay_code=quay.get("publicCode"),
                    )
                )

            patterns.append(
                LinePattern(
                    id=pattern["id"],
                    name=pattern.get("name"),
                    direction_type=pattern.get("directionType"),
                    stops=stops,
                )
            )

        result: dict[str, Any] = {
            "line": {
                "id": line["id"],
                "public_code": line.get("publicCode"),
                "name": line.get("name"),
                "authority_id": ((line.get("authority") or {}).get("id")),
                "authority_name": ((line.get("authority") or {}).get("name")),
                "transport_mode": line.get("transportMode"),
            },
            "patterns": patterns,
        }

        if via_stop_text:
            normalized_query = self._normalize_text(via_stop_text)
            matching_patterns: list[dict[str, Any]] = []

            for pattern in patterns:
                matched_stops = [
                    stop.stop_name
                    for stop in pattern.stops
                    if normalized_query
                    and (
                        self._normalize_text(stop.stop_name) == normalized_query
                        or normalized_query in self._normalize_text(stop.stop_name)
                    )
                ]
                if matched_stops:
                    matching_patterns.append(
                        {
                            "pattern_id": pattern.id,
                            "pattern_name": pattern.name,
                            "direction_type": pattern.direction_type,
                            "matched_stops": matched_stops,
                        }
                    )

            result["via_stop_check"] = {
                "query": via_stop_text,
                "matches_any_pattern": bool(matching_patterns),
                "matching_patterns": matching_patterns,
            }

        return result
