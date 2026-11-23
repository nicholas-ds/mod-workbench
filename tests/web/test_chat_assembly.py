"""Tests for ChatAssembly: one build call wires the whole chat stack."""

from pathlib import Path

from workbench.web.chat_assembly import ChatAssembly, ChatStack
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.permission_card_builder import PermissionCardBuilder


class FakeDirectory:
    """Duck-typed OrchestratorDirectory: build only calls folder_of."""

    def folder_of(self, name: str) -> str:
        return "E:/repos/mods/fake-repo"


def _build(tmp_path: Path) -> ChatStack:
    return ChatAssembly().build(
        FakeDirectory(),
        tmp_path,
        tmp_path / "status",
        PendingPermissionStore(),
        PermissionCardBuilder(),
    )


def test_stack_builds_a_resolver_with_both_backends(tmp_path: Path) -> None:
    stack = _build(tmp_path)
    assert [traits.key for traits in stack.resolver.all_traits()] == [
        "claude",
        "opencode",
    ]


def test_resolver_defaults_to_the_claude_backend(tmp_path: Path) -> None:
    stack = _build(tmp_path)
    assert stack.resolver.backend_of("Workbench").traits.key == "claude"


def test_thread_registry_persists_to_chat_threads_json(tmp_path: Path) -> None:
    stack = _build(tmp_path)
    stack.threads.add("Workbench")
    assert (tmp_path / "status" / "chat_threads.json").is_file()


def test_claude_session_ids_persist_to_session_ids_json(tmp_path: Path) -> None:
    stack = _build(tmp_path)
    stack.claude_session_ids.save("Workbench", "sid-1")
    assert (tmp_path / "status" / "session_ids.json").is_file()
    assert stack.claude_session_ids.known_ids() == frozenset({"sid-1"})
