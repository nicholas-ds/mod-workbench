"""Validate board front matter and build one Board."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from workbench.board_types import (
    Board,
    BoardError,
    BoardItem,
    FrontMatter,
    Option,
    Question,
    ResolvedItem,
)

_NAMED_KEYS = ("title", "raised_by", "created", "tags", "items", "questions", "resolved")
_QUESTION_TYPES = ("choice", "yes", "text")


class BoardBuilder:
    """Validate front matter and build the Board for one board folder."""

    def build(self, folder: Path, front_matter: FrontMatter) -> Board:
        fields = front_matter.fields
        return Board(
            id=folder.name,
            folder=folder,
            title=self._title(fields, folder),
            raised_by=self._optional_string(fields.get("raised_by"), folder, "raised_by"),
            created=self._optional_string(fields.get("created"), folder, "created"),
            tags=self._string_list(fields.get("tags"), folder, "tags"),
            items=self._items(fields, folder),
            questions=self._questions(fields, folder),
            resolved=self._resolved(fields, folder),
            body=front_matter.body,
            extra=self._extra(fields),
        )

    def _title(self, fields: Mapping[str, object], folder: Path) -> str:
        title = fields.get("title")
        if not isinstance(title, str) or not title:
            raise BoardError(folder, "front matter misses title")
        return title

    def _items(self, fields: Mapping[str, object], folder: Path) -> tuple[BoardItem, ...]:
        raw_items = fields.get("items")
        if raw_items is None:
            return ()
        if not isinstance(raw_items, list):
            raise BoardError(folder, "items must be a list")
        return tuple(self._item(raw, folder) for raw in raw_items)

    def _item(self, raw: object, folder: Path) -> BoardItem:
        if not isinstance(raw, dict):
            raise BoardError(folder, "each item must be a mapping")
        file = self._item_file(raw.get("file"), folder)
        caption = raw.get("caption")
        if not isinstance(caption, str) or not caption:
            raise BoardError(folder, "each item needs a caption string")
        group = raw.get("group")
        if group is not None and not isinstance(group, str):
            raise BoardError(folder, "item group must be a string")
        return BoardItem(file=file, caption=caption, group=group)

    def _item_file(self, value: object, folder: Path) -> str:
        if not isinstance(value, str) or not value:
            raise BoardError(folder, "each item needs a file string")
        candidate = Path(value)
        # A rooted path ("/x", "C:/x") escapes the folder even without a drive letter.
        if candidate.anchor or ".." in candidate.parts:
            raise BoardError(folder, f"item file escapes the board folder: {value}")
        return value

    def _questions(self, fields: Mapping[str, object], folder: Path) -> tuple[Question, ...]:
        raw_questions = fields.get("questions")
        if not isinstance(raw_questions, list):
            raise BoardError(folder, "questions must be a list")
        questions = tuple(self._question(raw, folder) for raw in raw_questions)
        return self._unique_question_ids(questions, folder)

    def _resolved(self, fields: Mapping[str, object], folder: Path) -> tuple[ResolvedItem, ...]:
        raw_resolved = fields.get("resolved")
        if raw_resolved is None:
            return ()
        if not isinstance(raw_resolved, list):
            raise BoardError(folder, "resolved must be a list")
        return tuple(self._resolved_item(raw, folder) for raw in raw_resolved)

    def _resolved_item(self, raw: object, folder: Path) -> ResolvedItem:
        if not isinstance(raw, dict):
            raise BoardError(folder, "each resolved item must be a mapping")
        values = {key: raw.get(key) for key in ("id", "prompt", "note", "date")}
        if not all(isinstance(value, str) and value for value in values.values()):
            raise BoardError(folder, "each resolved item needs id, prompt, note and date strings")
        return ResolvedItem(**values)

    def _unique_question_ids(
        self, questions: tuple[Question, ...], folder: Path
    ) -> tuple[Question, ...]:
        seen: set[str] = set()
        for question in questions:
            if question.id in seen:
                raise BoardError(folder, f"duplicate question id: {question.id}")
            seen.add(question.id)
        return questions

    def _question(self, raw: object, folder: Path) -> Question:
        if not isinstance(raw, dict):
            raise BoardError(folder, "each question must be a mapping")
        question_id = raw.get("id")
        if not isinstance(question_id, str) or not question_id:
            raise BoardError(folder, "each question needs an id string")
        qtype = raw.get("type")
        if not isinstance(qtype, str) or qtype not in _QUESTION_TYPES:
            raise BoardError(folder, f"unknown question type: {qtype}")
        prompt = raw.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise BoardError(folder, "each question needs a prompt string")
        options = self._question_options(qtype, raw.get("options"), folder)
        default = self._question_default(qtype, raw.get("default"), options, folder)
        return Question(
            id=question_id,
            type=qtype,
            prompt=prompt,
            options=options,
            default=default,
            suggestion=self._question_suggestion(qtype, raw.get("suggestion"), folder),
            blocking=self._question_blocking(raw.get("blocking"), folder),
            affects=self._string_list(raw.get("affects"), folder, "affects"),
        )

    def _question_options(
        self, qtype: str, raw_options: object, folder: Path
    ) -> tuple[Option, ...]:
        if qtype != "choice":
            return ()
        if not isinstance(raw_options, list) or len(raw_options) not in (2, 3):
            raise BoardError(folder, "choice needs 2 or 3 options")
        return tuple(self._option(raw, folder) for raw in raw_options)

    def _option(self, raw: object, folder: Path) -> Option:
        if not isinstance(raw, dict):
            raise BoardError(folder, "each option must be a mapping")
        option_id = raw.get("id")
        label = raw.get("label")
        if not isinstance(option_id, str) or not isinstance(label, str):
            raise BoardError(folder, "each option needs id and label strings")
        item = raw.get("item")
        if item is not None and not isinstance(item, str):
            raise BoardError(folder, "option item must be a string")
        return Option(id=option_id, label=label, item=item)

    def _question_default(
        self, qtype: str, raw_default: object, options: tuple[Option, ...], folder: Path
    ) -> str | None:
        if qtype != "choice":
            return None
        if not isinstance(raw_default, str):
            raise BoardError(folder, "choice needs a default option id")
        if raw_default not in {option.id for option in options}:
            raise BoardError(folder, f"default is not an option id: {raw_default}")
        return raw_default

    def _question_suggestion(
        self, qtype: str, raw_suggestion: object, folder: Path
    ) -> str | None:
        if qtype != "yes":
            return None
        if not isinstance(raw_suggestion, str) or not raw_suggestion:
            raise BoardError(folder, "yes question needs a suggestion")
        return raw_suggestion

    def _question_blocking(self, raw_blocking: object, folder: Path) -> bool:
        if raw_blocking is None:
            return False
        if not isinstance(raw_blocking, bool):
            raise BoardError(folder, "blocking must be true or false")
        return raw_blocking

    def _string_list(self, value: object, folder: Path, key: str) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise BoardError(folder, f"{key} must be a list of strings")
        return tuple(value)

    def _optional_string(self, value: object, folder: Path, key: str) -> str | None:
        if value is None or isinstance(value, str):
            return value
        raise BoardError(folder, f"{key} must be a string")

    def _extra(self, fields: Mapping[str, object]) -> Mapping[str, object]:
        return MappingProxyType({k: v for k, v in fields.items() if k not in _NAMED_KEYS})
