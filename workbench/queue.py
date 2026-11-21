"""Blocking rule and sort order of the open board queue."""

from __future__ import annotations

from workbench.board_types import BoardEntry


class BlockingRule:
    """Tell whether one board still has an unanswered blocking question."""

    def is_blocking(self, entry: BoardEntry) -> bool:
        answered = {answer.question_id for answer in entry.answers}
        return any(question.blocking and question.id not in answered
                   for question in entry.board.questions)


class QueueSorter:
    """Orders open boards: blocking first, then widest affect, then oldest."""

    def __init__(self, blocking: BlockingRule | None = None) -> None:
        self._blocking = blocking if blocking is not None else BlockingRule()

    def sort(self, entries: list[BoardEntry]) -> list[BoardEntry]:
        return sorted(entries, key=self._order_key)

    def _order_key(self, entry: BoardEntry) -> tuple[bool, int, str]:
        affect_count = sum(len(question.affects)
                           for question in entry.board.questions)
        # A board without created sorts as the oldest possible entry.
        return (not self._blocking.is_blocking(entry), -affect_count,
                entry.board.created or "")
