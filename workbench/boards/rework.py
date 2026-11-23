"""Rework brief and log line for one board entry (design.md)."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.board_types import Board, BoardEntry, Question
from workbench.core.config import ModConfig


class LogAppender:
    """Append one line to a log file."""

    def append(self, log: Path, line: str) -> None:
        if not log.parent.exists():
            log.parent.mkdir(parents=True)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


class ReworkBriefWriter:
    """Write the rework brief and the log line for one board entry."""

    def __init__(self, log_appender: LogAppender) -> None:
        self._log_appender = log_appender

    def write(self, cfg: ModConfig, entry: BoardEntry) -> Path | None:
        changed = self._changed_picks(entry)
        if not changed:
            return None
        brief_path = self._write_brief(cfg, entry.board, changed)
        log_line = self._log_line(entry.board, brief_path)
        self._log_appender.append(cfg.log, log_line)
        return brief_path

    def _changed_picks(self, entry: BoardEntry) -> tuple[tuple[Question, str], ...]:
        picked = {answer.question_id: answer.picked for answer in entry.answers}
        return tuple(
            (question, picked[question.id])
            for question in entry.board.questions
            if question.type == "choice"
            and picked.get(question.id) not in (None, question.default)
        )

    def _write_brief(
        self, cfg: ModConfig, board: Board, changed: tuple[tuple[Question, str], ...]
    ) -> Path:
        cfg.briefs.mkdir(parents=True, exist_ok=True)
        brief_path = cfg.briefs / f"rework-{board.id}.md"
        brief_path.write_text(self._brief_text(board, changed), encoding="utf-8")
        return brief_path

    def _brief_text(self, board: Board, changed: tuple[tuple[Question, str], ...]) -> str:
        sections = [self._section(question, picked) for question, picked in changed]
        return f"# Rework: {board.id}\n\n" + "\n\n".join(sections)

    def _section(self, question: Question, picked: str) -> str:
        lines = [
            f"## {question.prompt}",
            "",
            f"Default: {question.default}",
            f"Picked: {picked}",
            "",
            "Reworks:",
        ]
        lines.extend(f"- {affect}" for affect in question.affects)
        return "\n".join(lines)

    def _log_line(self, board: Board, brief_path: Path) -> str:
        return f"rework {board.id}: brief {brief_path.name}"
