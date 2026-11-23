"""Tests for the permission card builder."""

import json
from dataclasses import asdict

from workbench.chat.chat_event import (
    KIND_PERMISSION,
    KIND_PERMISSION_SETTLED,
    ChatEvent,
)
from workbench.chat.permission_card_builder import PermissionCardBuilder


def make_builder() -> PermissionCardBuilder:
    return PermissionCardBuilder()


def make_card(title: str | None, display_name: str | None, tool_input: dict | None = None) -> object:
    return make_builder().build(
        request_id="req-1",
        tool_name="Bash",
        tool_input={"command": "git status"} if tool_input is None else tool_input,
        title=title,
        display_name=display_name,
    )


def test_title_is_the_card_text() -> None:
    card = make_card("Run git", "Bash")
    assert card.text == "Run git"
    assert card.kind == KIND_PERMISSION


def test_display_name_is_used_without_title() -> None:
    card = make_card("", "Bash")
    assert card.text == "Bash\ngit status"


def test_tool_name_and_input_detail_are_the_fallback() -> None:
    card = make_card("", "")
    assert card.text == "Bash\ngit status"


def test_empty_tool_input_gives_the_name_only() -> None:
    card = make_card("", "", tool_input={})
    assert card.text == "Bash"


def test_request_id_travels_in_detail() -> None:
    card = make_card(None, None)
    assert card.detail == "req-1"


def test_settle_event_names_request_and_outcome() -> None:
    event = make_builder().settle("req-9", "approved")
    assert event == ChatEvent(kind=KIND_PERMISSION_SETTLED, text="approved", detail="req-9")


def test_card_event_survives_json() -> None:
    card = make_card(None, None)
    restored = json.loads(json.dumps(asdict(card)))
    assert restored == asdict(card)
