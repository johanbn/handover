from __future__ import annotations

from typing import Any

from ruter_chatbot.graph.routers.state_field_router import StateFieldRouter
from ruter_chatbot.types.iac.router_spec import StateFieldRouterSpec


class RouterRegistry:
    def __init__(self) -> None:
        self._routers: dict[str, Any] = {}

    def register(self, key: str, router: Any) -> None:
        self._routers[key] = router

    def get(self, key: str) -> Any:
        if key not in self._routers:
            raise KeyError(f"Unknown router key: {key}")
        return self._routers[key]

    def from_spec(self, spec: Any) -> None:
        if isinstance(spec, StateFieldRouterSpec):
            self.register(spec.name, StateFieldRouter(field=spec.field))
            return

        raise TypeError(f"Unsupported router spec type: {type(spec).__name__}")