"""Tests for SlashCommandLister shapes and the GET chat commands endpoint."""

from pathlib import Path

from workbench.slash_command_lister import SlashCommandInfo, SlashCommandLister

from routes_chat_fakes import make_chat_client


def listed(server_info: dict[str, object] | None) -> tuple[SlashCommandInfo, ...]:
    return SlashCommandLister().list(server_info)


def test_list_reads_name_and_description() -> None:
    server_info = {"commands": [
        {"name": "clear", "description": "Clear the chat"},
        {"name": "asd-ste100", "description": "Rewrite text"},
    ]}
    assert listed(server_info) == (
        SlashCommandInfo(name="asd-ste100", description="Rewrite text"),
        SlashCommandInfo(name="clear", description="Clear the chat"),
    )


def test_list_strips_leading_slashes_and_sorts_by_name() -> None:
    server_info = {"commands": [
        {"name": "/zulu", "description": "z"},
        {"name": "/alpha", "description": "a"},
    ]}
    assert listed(server_info) == (
        SlashCommandInfo(name="alpha", description="a"),
        SlashCommandInfo(name="zulu", description="z"),
    )


def test_list_de_duplicates_keeping_the_first_entry() -> None:
    server_info = {"commands": [
        {"name": "/clear", "description": "first"},
        {"name": "clear", "description": "second"},
    ]}
    assert listed(server_info) == (
        SlashCommandInfo(name="clear", description="first"),
    )


def test_list_empty_commands_gives_empty_tuple() -> None:
    assert listed({"commands": []}) == ()


def test_list_none_gives_empty_tuple() -> None:
    assert listed(None) == ()


def test_list_odd_data_gives_empty_tuple() -> None:
    assert listed({}) == ()
    assert listed({"commands": None}) == ()
    assert listed({"commands": "nope"}) == ()
    assert listed({"commands": [42, "also nope", {"nope": 1}, {"name": ""}]}) == ()


def test_commands_endpoint_returns_normalized_commands(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].command_rows = (
        SlashCommandInfo(name="asd-ste100", description="Rewrite text"),
        SlashCommandInfo(name="clear", description="Clear the chat"),
    )
    response = client.get("/api/chat/main/commands")
    assert response.status_code == 200
    assert fakes["claude"].commands_calls == ["main"]
    assert response.json() == {"commands": [
        {"name": "asd-ste100", "description": "Rewrite text"},
        {"name": "clear", "description": "Clear the chat"},
    ]}


def test_commands_endpoint_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/other/commands")
    assert response.status_code == 404
    assert fakes["claude"].commands_calls == []
