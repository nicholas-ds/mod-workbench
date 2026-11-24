"""Tests for RepoSessionRecipient."""

from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.repo_session_recipient import RepoSessionRecipient

REPO = OwnerId(OwnerKind.REPO, "StarfieldLogistics")


class Harness:
    def __init__(self, send_ok: bool = True) -> None:
        self.send_ok = send_ok
        self.turns: list[tuple[str, str]] = []
        self.threads: list[str] = []

    def send_turn(self, chat: str, text: str) -> bool:
        self.turns.append((chat, text))
        return self.send_ok

    def add_thread(self, orchestrator: str) -> str:
        self.threads.append(orchestrator)
        return f"{orchestrator}~t1"


def build(harness: Harness) -> RepoSessionRecipient:
    return RepoSessionRecipient(harness.send_turn, harness.add_thread)


def test_repo_session_is_always_reachable() -> None:
    assert build(Harness()).is_reachable(REPO) is True


def test_send_line_opens_a_new_thread_in_the_repo_and_sends() -> None:
    harness = Harness()

    assert build(harness).send_line(REPO, "notice") is True
    assert harness.threads == ["StarfieldLogistics"]
    assert harness.turns == [("StarfieldLogistics~t1", "notice")]


def test_start_fresh_also_opens_a_new_thread() -> None:
    harness = Harness()

    assert build(harness).start_fresh(REPO, "prompt") is True
    assert harness.turns == [("StarfieldLogistics~t1", "prompt")]


def test_failed_send_returns_false() -> None:
    assert build(Harness(send_ok=False)).send_line(REPO, "x") is False


def test_context_is_unknown_and_traits_name_the_repo_kind() -> None:
    recipient = build(Harness())

    assert recipient.context_percent(REPO) is None
    assert recipient.traits.kind is OwnerKind.REPO
