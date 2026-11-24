"""Loop routes of one mod: return the active loops as JSON."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.notices.active_loop_filter import ActiveLoopFilter
from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_types import LoopSnapshot
from workbench.notices.owner_inbox import OwnerInbox


class LoopRoutes:
    """Loop routes of one mod: return the active loops as JSON."""

    def __init__(self, registry: ModRegistry,
                 tracker_of: Callable[[ModConfig], LoopTracker],
                 inbox_of: Callable[[ModConfig], OwnerInbox],
                 loop_filter: ActiveLoopFilter,
                 clock: Callable[[], datetime]) -> None:
        self._registry, self._tracker_of, self._inbox_of = registry, tracker_of, inbox_of
        self._loop_filter, self._clock = loop_filter, clock
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods/{name}/loops", self.loops, methods=["GET"])

    def loops(self, name: str) -> dict[str, object]:
        """Track every recent notice of the mod and return the active loops."""
        cfg = self._registry.require(name)
        records = self._inbox_of(cfg).all_records()
        tracker = self._tracker_of(cfg)
        snapshots = [s for s in (tracker.track(r) for r in records) if s is not None]
        active = self._loop_filter.select(snapshots, self._clock())
        return {"loops": [self._as_json(s) for s in active]}

    @staticmethod
    def _as_json(snapshot: LoopSnapshot) -> dict[str, object]:
        """The snapshot fields as a JSON dict, with `stage` as its value."""
        data: dict[str, object] = asdict(snapshot)
        data["stage"] = snapshot.stage.value
        return data
