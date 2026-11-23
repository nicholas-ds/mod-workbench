"""Tests for PaneRecipient."""

from pathlib import Path

from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.pane_context_reader import PaneContextReader
from workbench.notices.pane_recipient import PaneRecipient
from workbench.panes.pane_registry import OrchestratorPane


class FakeSender:
    """PaneSender stub that records every send."""

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.sent: list[tuple[str, str]] = []

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        self.sent.append((pane.surface, text))
        return self.ok


MAIN = OwnerId(OwnerKind.PANE, "main")


def recipient(sender: FakeSender | None = None, panes: bool = True,
              idle: bool = True) -> tuple[PaneRecipient, FakeSender]:
    found = sender if sender is not None else FakeSender()
    pane = OrchestratorPane(surface="0") if panes else None
    reader = PaneContextReader(status_file_of=lambda _owner: None)
    obj = PaneRecipient(lambda _owner: pane, found, reader, lambda _o: idle)
    return obj, found


def test_traits_describe_the_pane() -> None:
    traits = recipient()[0].traits
    assert (traits.kind, traits.label, traits.measures_context,
            traits.fresh_mode, traits.retry_limit) == (
        OwnerKind.PANE, "Claude Code pane", True, "clear-pane", 5)


def test_reachable_when_a_pane_is_found() -> None:
    assert recipient(panes=True)[0].is_reachable(MAIN) is True
    assert recipient(panes=False)[0].is_reachable(MAIN) is False


def test_context_percent_delegates_to_reader(tmp_path: Path) -> None:
    status = tmp_path / "status.toml"
    status.write_text("context_percent = 61.5\n", encoding="utf-8")
    reader = PaneContextReader(status_file_of=lambda _owner: status)
    obj = PaneRecipient(lambda _owner: OrchestratorPane(surface="0"),
                        FakeSender(), reader, lambda _owner: True)
    assert obj.context_percent(MAIN) == 61.5


def test_send_line_types_into_the_pane() -> None:
    obj, sender = recipient()
    assert obj.send_line(MAIN, "[workbench] hello") is True
    assert sender.sent == [("0", "[workbench] hello")]


def test_send_line_without_pane_fails() -> None:
    obj, sender = recipient(panes=False)
    assert obj.send_line(MAIN, "[workbench] hello") is False
    assert sender.sent == []


def test_start_fresh_sends_clear_then_prompt() -> None:
    obj, sender = recipient(idle=True)
    assert obj.start_fresh(MAIN, "fresh prompt") is True
    assert sender.sent == [("0", "/clear"), ("0", "fresh prompt")]


def test_start_fresh_blocked_when_busy() -> None:
    obj, sender = recipient(idle=False)
    assert obj.start_fresh(MAIN, "fresh prompt") is False
    assert sender.sent == []


def test_start_fresh_blocked_without_pane() -> None:
    obj, sender = recipient(panes=False)
    assert obj.start_fresh(MAIN, "fresh prompt") is False
    assert sender.sent == []


def test_start_fresh_fails_when_clear_fails() -> None:
    obj, sender = recipient(sender=FakeSender(ok=False))
    assert obj.start_fresh(MAIN, "fresh prompt") is False
    assert sender.sent == [("0", "/clear")]
