"""Tests for the chat session note."""

from workbench.chat_session_note import ChatSessionNote


def test_note_names_the_chat() -> None:
    text = ChatSessionNote().text("main")
    assert 'named "main"' in text


def test_note_tells_how_to_raise_a_board() -> None:
    text = ChatSessionNote().text("main")
    assert "raised_by: chat-main" in text


def test_note_tells_to_surface_work_upfront() -> None:
    text = ChatSessionNote().text("main")
    assert "Surface work upfront" in text


def test_note_has_exactly_five_lines() -> None:
    text = ChatSessionNote().text("main")
    assert len(text.split("\n")) == 5
