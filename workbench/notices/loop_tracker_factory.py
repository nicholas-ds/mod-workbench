"""Assemble a LoopTracker for one mod from real parts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from workbench.core.config import ModConfig
from workbench.mods.pane_directory import PaneDirectory
from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.loop_stage_deriver import LoopStageDeriver
from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_types import StallLimits
from workbench.notices.new_board_detector import NewBoardDetector
from workbench.notices.owner_id import OwnerId
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.pane_signal_reader import PaneSignalReader


class LoopTrackerFactory:
    """Wire the loop tracking pipeline for one mod from injected parts."""

    def __init__(self, pane_directory: PaneDirectory,
                 clock: Callable[[], datetime]) -> None:
        self._pane_directory = pane_directory
        self._clock = clock

    def build(self, cfg: ModConfig) -> LoopTracker:
        """Build the tracker: inbox, signal reader, detector and deriver."""
        def status_file_of(owner: OwnerId) -> Path | None:
            entry = self._pane_directory.find(owner.key)
            return None if entry is None else entry.status_file

        return LoopTracker(
            inbox=OwnerInbox.of_mod(cfg.repo),
            signal_reader=PaneSignalReader(status_file_of),
            detector=NewBoardDetector(BoardOwnerStore()),
            deriver=LoopStageDeriver(StallLimits()),
            boards_open_dir=cfg.repo / "boards" / "open",
            clock=self._clock)
