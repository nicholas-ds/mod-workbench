"""Policy settings for the done-board archive.

Spec: docs/board-archive-design.md, revision 1. Frozen settings shared by
the scanner and archiver.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchivePolicy:
    min_age_days: int = 30
