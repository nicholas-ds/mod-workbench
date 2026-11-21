"""Tests for ThreadRegistry: chat threads per orchestrator, atomic save."""

import json
from pathlib import Path

from workbench.thread_registry import ChatThread, ThreadRegistry


def test_empty_list_when_no_file(tmp_path: Path) -> None:
    registry = ThreadRegistry(tmp_path / "threads.json")
    assert registry.list_threads("Workbench") == ()


def test_add_twice_gives_t1_then_t2(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    registry = ThreadRegistry(path)
    first = registry.add("Workbench")
    second = registry.add("Workbench")
    assert first == ChatThread("Workbench", "t1", "thread 1")
    assert second == ChatThread("Workbench", "t2", "thread 2")
    assert first.name == "Workbench~t1"
    assert registry.list_threads("Workbench") == (first, second)


def test_file_format_matches_spec(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    ThreadRegistry(path).add("Workbench")
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "Workbench": [{"id": "t1", "label": "thread 1"}],
    }


def test_ids_number_per_orchestrator(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    registry = ThreadRegistry(path)
    assert registry.add("Workbench").thread_id == "t1"
    assert registry.add("Other").thread_id == "t1"
    assert registry.add("Workbench").thread_id == "t2"


def test_id_choice_reuse_only_after_highest_removed(tmp_path: Path) -> None:
    """Documented choice: the next id is one more than the highest id still
    present, so removing the highest id may reuse its number (t1, t2, remove
    t2, add -> t2 again), while removing a lower id never renumbers or frees
    its number while a higher id exists (t1, t2, remove t1, add -> t3)."""
    path = tmp_path / "threads.json"
    registry = ThreadRegistry(path)
    registry.add("Workbench")
    registry.add("Workbench")
    assert registry.remove("Workbench~t2") is True
    assert registry.add("Workbench").thread_id == "t2"
    assert registry.remove("Workbench~t1") is True
    assert registry.add("Workbench").thread_id == "t3"


def test_remove_unknown_name_returns_false(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    assert ThreadRegistry(path).remove("Workbench~t9") is False
    registry = ThreadRegistry(path)
    registry.add("Workbench")
    assert registry.remove("Workbench~t9") is False
    assert registry.remove("Workbench") is False


def test_remove_deletes_only_that_thread(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    registry = ThreadRegistry(path)
    first = registry.add("Workbench")
    second = registry.add("Workbench")
    other = registry.add("Other")
    assert registry.remove(first.name) is True
    assert registry.list_threads("Workbench") == (second,)
    assert registry.list_threads("Other") == (other,)
    assert registry.contains(second.name) is True


def test_persists_across_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    added = ThreadRegistry(path).add("Workbench")
    second = ThreadRegistry(path)
    assert second.list_threads("Workbench") == (added,)
    assert second.contains("Workbench~t1") is True


def test_corrupt_file_loads_empty_and_add_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "threads.json"
    path.write_text("{not json", encoding="utf-8")
    registry = ThreadRegistry(path)
    assert registry.list_threads("Workbench") == ()
    assert registry.contains("Workbench~t1") is False
    assert registry.remove("Workbench~t1") is False
    assert registry.add("Workbench").thread_id == "t1"


def test_disabled_store_none_path_is_a_no_op(tmp_path: Path) -> None:
    registry = ThreadRegistry(None)
    assert registry.list_threads("Workbench") == ()
    added = registry.add("Workbench")
    assert added == ChatThread("Workbench", "t1", "thread 1")
    assert registry.list_threads("Workbench") == ()
    assert registry.contains(added.name) is False
    assert registry.remove(added.name) is False


def test_split_name() -> None:
    assert ChatThread.split_name("Workbench~t1") == ("Workbench", "t1")
    assert ChatThread.split_name("Workbench") == ("Workbench", "")
    # Split at the last separator, the inverse of `name` even when the
    # orchestrator itself contains a separator.
    assert ChatThread.split_name("a~b~t2") == ("a~b", "t2")
    thread = ChatThread("Starfield", "t12", "thread 12")
    assert ChatThread.split_name(thread.name) == ("Starfield", "t12")


def test_old_file_with_backend_key_loads_and_ignores_it(tmp_path: Path) -> None:
    """Old rows carry a backend key; they load, and the key is dropped."""
    path = tmp_path / "threads.json"
    path.write_text(json.dumps({"Workbench": [
        {"id": "t1", "label": "no key"},
        {"id": "t2", "label": "string key", "backend": "opencode"},
        {"id": "t3", "label": "odd key", "backend": 7},
    ]}), encoding="utf-8")
    registry = ThreadRegistry(path)
    assert registry.list_threads("Workbench") == (
        ChatThread("Workbench", "t1", "no key"),
        ChatThread("Workbench", "t2", "string key"),
        ChatThread("Workbench", "t3", "odd key"),
    )
    registry.add("Workbench")
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "Workbench": [
            {"id": "t1", "label": "no key"},
            {"id": "t2", "label": "string key"},
            {"id": "t3", "label": "odd key"},
            {"id": "t4", "label": "thread 4"},
        ],
    }
