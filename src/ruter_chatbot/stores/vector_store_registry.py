from __future__ import annotations

from datetime import datetime, timedelta

from ruter_chatbot.stores.vector_store_runtime import VectorStoreRuntime
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.spec_based_registry import SpecBasedRegistry
from ruter_chatbot.types.app.vector_store import (
    VectorStoreInfo,
    VectorStoreListResponse,
)

class VectorStoreRegistry(
    SpecBasedRegistry[
        VectorStoreRuntime, VectorStoreSpec
    ]
):
    runtime_class = VectorStoreRuntime

    def initialize(self, key: str) -> None:
        self.get(key).initialize()

    def initialize_all(self) -> None:
        for store in self._items.values():
            store.initialize()

    def refresh(self, key: str) -> None:
        self.get(key).refresh()

    def start_refresh(self, key: str):
        return self.get(key).start_refresh()

    def list_stores(self) -> VectorStoreListResponse:
        stores: list[VectorStoreRuntime] = list(self._items.values())
        return VectorStoreListResponse(
            stores=[
                VectorStoreInfo(
                    name=store.key,
                    state=store.state.value,
                )
                for store in stores
            ]
        )

    def start_daily_refreshes(
        self,
        start_hour: int,
        start_minute: int,
        stagger_by: dict[str, int] = { "hours": 0, "minutes": 30 }
    ) -> dict[str, str]:
        """
        Starts daily refresh loops for stores in registry.
        Does not expect store list in registry to change after starting.
        Changing it may result in surprises.

        Args:
            start_hour (int): The hour (0-23) that the first refresh should start.
            start_minute (int): The minute (0-59) that the first refresh should start.
            stagger_by (dict[str, int]):
                How many `hours` and `minutes` should be between one refresh start and the next.
                Additional fields will be ignored. Missing fields are treated as 0.
                Both values must be non-negative integers.

                NOTE: Excessive staggering can cause unexpected behavior.
                Keep the cumulative stagger within a 24-hour cycle.
        
        Returns:
            dict[str, str]:
                Overview per store key of when refreshes will occur (as "HH:MM").
                If scheduling failed for a store, the value will be the error string instead.
        """
        if not isinstance(start_hour, int) or not 0 <= start_hour <= 23:
            raise ValueError(f"start_hour must be an integer between 0 and 23, got {start_hour}")

        if not isinstance(start_minute, int) or not 0 <= start_minute <= 59:
            raise ValueError(f"start_minute must be an integer between 0 and 59, got {start_minute}")

        if not isinstance(stagger_by, dict):
            raise TypeError(f"stagger_by must be a dict, got {type(stagger_by).__name__}")

        stagger_hours = stagger_by.get("hours", 0)
        stagger_minutes = stagger_by.get("minutes", 0)

        if not isinstance(stagger_hours, int) or stagger_hours < 0:
            raise ValueError(f"stagger_by['hours'] must be a non-negative integer, got {stagger_hours}")

        if not isinstance(stagger_minutes, int) or stagger_minutes < 0:
            raise ValueError(f"stagger_by['minutes'] must be a non-negative integer, got {stagger_minutes}")

        now = datetime.now().replace(microsecond=0, second=0)
        base_time = now.replace(hour=start_hour, minute=start_minute)
        
        local_refresh_times: dict[str, str] = {}
        delta = timedelta(hours=stagger_hours, minutes=stagger_minutes)

        for key, store in self.items():
            scheduled_time = base_time + (delta * len(local_refresh_times))

            hour = scheduled_time.hour
            minute = scheduled_time.minute
            try:
                store.start_daily_refresh_loop(
                    hour=hour,
                    minute=minute
                )
                local_refresh_times[key] = f"{hour:02d}:{minute:02d}"
            except Exception as e:
                local_refresh_times[key] = str(e)
        
        return local_refresh_times
