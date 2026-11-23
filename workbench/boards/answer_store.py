"""answers.json in one board folder: read, merge, write atomically."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workbench.boards.board_types import Answer, BoardError

ANSWERS_FILE = "answers.json"


class AnswerStore:
    """Read and write answers.json for one board folder."""

    def read(self, folder: Path) -> tuple[Answer, ...]:
        folder = Path(folder)
        path = folder / ANSWERS_FILE
        if not path.is_file():
            return ()
        data = self._load_json(folder, path)
        return self._parse_answers(folder, data)

    def write(self, folder: Path, answer: Answer) -> None:
        folder = Path(folder)
        merged = self._merge(self.read(folder), answer)
        payload = {"answers": [self._to_dict(item) for item in merged]}
        self._write_json(folder, payload)

    def _merge(self, existing: tuple[Answer, ...], answer: Answer) -> list[Answer]:
        kept = [item for item in existing if item.question_id != answer.question_id]
        kept.append(answer)
        return kept

    def _to_dict(self, answer: Answer) -> dict[str, str | None]:
        return {
            "question_id": answer.question_id,
            "picked": answer.picked,
            "text": answer.text,
            "comment": answer.comment,
            "answered_at": answer.answered_at,
        }

    def _load_json(self, folder: Path, path: Path) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BoardError(folder, f"cannot read {ANSWERS_FILE}: {exc}") from exc

    def _parse_answers(self, folder: Path, data: object) -> tuple[Answer, ...]:
        if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
            raise BoardError(folder, f"{ANSWERS_FILE} must hold an answers list")
        return tuple(self._parse_answer(folder, raw) for raw in data["answers"])

    def _parse_answer(self, folder: Path, raw: object) -> Answer:
        if not isinstance(raw, dict):
            raise BoardError(folder, "each answer must be a mapping")
        question_id = raw.get("question_id")
        if not isinstance(question_id, str) or not question_id:
            raise BoardError(folder, "each answer needs a question_id string")
        return Answer(
            question_id=question_id,
            picked=self._optional_string(raw.get("picked")),
            text=self._optional_string(raw.get("text")),
            comment=self._optional_string(raw.get("comment")),
            answered_at=self._optional_string(raw.get("answered_at")) or "",
        )

    def _optional_string(self, value: object) -> str | None:
        if value is None or isinstance(value, str):
            return value
        return None

    # os.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write_json(self, folder: Path, payload: dict[str, list[dict[str, str | None]]]) -> None:
        target = folder / ANSWERS_FILE
        temp = folder / f"{ANSWERS_FILE}.tmp"
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp, target)
