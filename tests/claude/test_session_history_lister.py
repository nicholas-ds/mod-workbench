"""Tests for SessionHistoryLister mapping of SDK session entries to rows."""

from types import SimpleNamespace

from workbench.claude.session_history_lister import SessionHistoryLister
from workbench.chat.session_summary import SessionSummary


def entry(**fields: object) -> object:
    base: dict[str, object] = {
        "session_id": "s1",
        "summary": "",
        "last_modified": 1000,
        "custom_title": None,
        "first_prompt": None,
    }
    base.update(fields)
    return SimpleNamespace(**base)


def listed(
    folder: str,
    entries: list[object],
    calls: list[dict[str, object]] | None = None,
    limit: int = 30,
) -> tuple[SessionSummary, ...]:
    seen = calls if calls is not None else []

    def fake(**kwargs: object) -> list:
        seen.append(kwargs)
        return entries

    return SessionHistoryLister(list_function=fake, limit=limit).list(folder)


def test_title_prefers_custom_title_then_summary_then_first_prompt() -> None:
    entries = [
        entry(custom_title="custom", summary="sum", first_prompt="first"),
        entry(summary="sum", first_prompt="first"),
        entry(first_prompt="first"),
        entry(),
    ]
    assert [row.title for row in listed("f", entries)] == [
        "custom",
        "sum",
        "first",
        "(untitled)",
    ]


def test_title_cuts_to_80_chars_and_replaces_line_breaks() -> None:
    rows = listed("f", [entry(summary="a\r\nb\nc"), entry(summary="x" * 100)])
    assert rows[0].title == "a b c"
    assert rows[1].title == "x" * 80


def test_skips_entries_without_session_id_string() -> None:
    entries = [
        entry(session_id=None),
        entry(session_id=""),
        SimpleNamespace(summary="no id field"),
        42,
        entry(session_id="real"),
    ]
    assert listed("f", entries) == (
        SessionSummary(session_id="real", title="(untitled)", last_modified_ms=1000),
    )


def test_empty_folder_returns_empty_tuple_without_calling() -> None:
    calls: list[dict[str, object]] = []
    assert listed("", [], calls=calls) == ()
    assert calls == []


def test_passes_directory_and_limit_to_list_function() -> None:
    calls: list[dict[str, object]] = []
    listed("E:/repo", [entry()], calls=calls, limit=5)
    assert calls == [{"directory": "E:/repo", "limit": 5}]
    default_calls: list[dict[str, object]] = []
    listed("E:/repo", [entry()], calls=default_calls)
    assert default_calls == [{"directory": "E:/repo", "limit": 30}]


def test_keeps_newest_first_order_and_maps_fields() -> None:
    entries = [
        entry(session_id="new", summary="newer", last_modified=200),
        entry(session_id="old", summary="older", last_modified=100),
    ]
    assert listed("f", entries) == (
        SessionSummary(session_id="new", title="newer", last_modified_ms=200),
        SessionSummary(session_id="old", title="older", last_modified_ms=100),
    )
