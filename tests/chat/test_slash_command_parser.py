"""Tests for SlashCommandParser: prompt vs clear command detection."""

import pytest

from workbench.chat.chat_command import ChatCommand, SlashCommandParser


def test_plain_text_becomes_prompt_command() -> None:
    parser = SlashCommandParser()
    assert parser.parse("hello there") == ChatCommand(kind="prompt", text="hello there")


def test_clear_text_becomes_clear_command() -> None:
    parser = SlashCommandParser()
    assert parser.parse("/clear") == ChatCommand(kind="clear", text="")


def test_blank_text_is_rejected() -> None:
    parser = SlashCommandParser()
    with pytest.raises(ValueError, match="empty message"):
        parser.parse("   ")


def test_other_slash_commands_stay_prompts() -> None:
    parser = SlashCommandParser()
    assert parser.parse("/compact now") == ChatCommand(kind="prompt", text="/compact now")


def test_surrounding_whitespace_is_stripped() -> None:
    parser = SlashCommandParser()
    assert parser.parse("  hi  ") == ChatCommand(kind="prompt", text="hi")
