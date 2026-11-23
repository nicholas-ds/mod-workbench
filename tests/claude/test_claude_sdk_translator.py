"""Tests for the Claude SDK message translator."""

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)

from workbench.chat.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_RESULT,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
)
from workbench.claude.claude_sdk_translator import ClaudeSdkTranslator


def make_translator() -> ClaudeSdkTranslator:
    return ClaudeSdkTranslator()


def make_result(is_error: bool, total_cost_usd: float | None, result: str) -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=is_error,
        num_turns=1, session_id="s", total_cost_usd=total_cost_usd, result=result,
    )


def test_text_block_becomes_text_event() -> None:
    message = AssistantMessage(content=[TextBlock(text="hi")], model="m")
    events = make_translator().translate(message)
    assert events == (ChatEvent(KIND_TEXT, "hi"),)


def test_thinking_block_becomes_thinking_event_with_empty_text() -> None:
    message = AssistantMessage(content=[ThinkingBlock(thinking="", signature="s")], model="m")
    events = make_translator().translate(message)
    assert events == (ChatEvent(KIND_THINKING, ""),)


def test_tool_use_block_becomes_tool_event_with_detail() -> None:
    block = ToolUseBlock(id="1", name="Bash", input={"command": "git status"})
    message = AssistantMessage(content=[block], model="m")
    events = make_translator().translate(message)
    assert events == (ChatEvent(KIND_TOOL, tool_name="Bash", detail="git status"),)


def test_unknown_block_gives_no_events() -> None:
    message = AssistantMessage(content=[object()], model="m")
    assert make_translator().translate(message) == ()


def test_error_result_becomes_error_event() -> None:
    message = make_result(is_error=True, total_cost_usd=None, result="")
    events = make_translator().translate(message)
    assert events == (ChatEvent(KIND_ERROR, "error"),)


def test_success_result_becomes_bare_result_event() -> None:
    message = make_result(is_error=False, total_cost_usd=0.14, result="done")
    events = make_translator().translate(message)
    assert events == (ChatEvent(KIND_RESULT),)


def test_unknown_message_gives_no_events() -> None:
    assert make_translator().translate(object()) == ()
