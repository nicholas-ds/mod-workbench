"""Tests for ChatRecipient."""

from workbench.notices.chat_recipient import ChatRecipient
from workbench.notices.owner_id import OwnerId, OwnerKind

CHAT = OwnerId(OwnerKind.CHAT, "review")


class Harness:
    """Records every injected call with configurable answers."""

    def __init__(self, known: bool = True, send_ok: bool = True,
                 context: float | None = 42.0) -> None:
        self.known = known
        self.send_ok = send_ok
        self.context = context
        self.turns: list[tuple[str, str]] = []
        self.threads: list[str] = []

    def send_turn(self, chat: str, text: str) -> bool:
        self.turns.append((chat, text))
        return self.send_ok

    def context_of(self, chat: str) -> float | None:
        return self.context

    def is_known(self, chat: str) -> bool:
        return self.known

    def orchestrator_of(self, chat: str) -> str:
        return "orchestrator"

    def add_thread(self, orchestrator: str) -> str:
        self.threads.append(orchestrator)
        return "thread-1"


def recipient(harness: Harness | None = None) -> tuple[ChatRecipient, Harness]:
    h = harness if harness is not None else Harness()
    obj = ChatRecipient(send_turn=h.send_turn, context_of=h.context_of,
                        is_known=h.is_known,
                        orchestrator_of=h.orchestrator_of,
                        add_thread=h.add_thread)
    return obj, h


def test_traits_describe_the_chat() -> None:
    traits = recipient()[0].traits
    assert (traits.kind, traits.label, traits.measures_context,
            traits.fresh_mode, traits.retry_limit) == (
        OwnerKind.CHAT, "App chat", True, "new-thread", 5)


def test_reachable_when_chat_is_known() -> None:
    assert recipient(Harness(known=True))[0].is_reachable(CHAT) is True
    assert recipient(Harness(known=False))[0].is_reachable(CHAT) is False


def test_context_percent_delegates_to_context_of() -> None:
    assert recipient(Harness(context=61.5))[0].context_percent(CHAT) == 61.5
    assert recipient(Harness(context=None))[0].context_percent(CHAT) is None


def test_send_line_sends_a_turn() -> None:
    obj, h = recipient()
    assert obj.send_line(CHAT, "[workbench] hello") is True
    assert h.turns == [("review", "[workbench] hello")]
    assert recipient(Harness(send_ok=False))[0].send_line(CHAT, "x") is False


def test_start_fresh_adds_thread_then_sends_prompt() -> None:
    obj, h = recipient()
    assert obj.start_fresh(CHAT, "fresh prompt") is True
    assert h.threads == ["orchestrator"]
    assert h.turns == [("thread-1", "fresh prompt")]


def test_start_fresh_blocked_when_unknown() -> None:
    obj, h = recipient(Harness(known=False))
    assert obj.start_fresh(CHAT, "fresh prompt") is False
    assert h.threads == []
    assert h.turns == []


def test_start_fresh_fails_when_send_fails() -> None:
    obj, h = recipient(Harness(send_ok=False))
    assert obj.start_fresh(CHAT, "fresh prompt") is False
    assert h.turns == [("thread-1", "fresh prompt")]
