"""Tests for the SDK client factory."""

from workbench.claude.sdk_client_factory import SdkClientFactory


class FakeDirectory:
    def __init__(self) -> None:
        self.folders = {
            "mod-a": "E:/repos/mods/mod-a",
            "mod-b": "E:/repos/mods/mod-b",
        }

    def folder_of(self, name: str) -> str:
        return self.folders[name]


def make_factory() -> SdkClientFactory:
    return SdkClientFactory(FakeDirectory())


def test_options_use_folder_of_the_given_name() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.cwd == "E:/repos/mods/mod-a"


def test_each_name_gets_its_own_folder() -> None:
    factory = make_factory()
    first = factory.create("mod-a", resume="")
    second = factory.create("mod-b", resume="")
    assert first.options.cwd == "E:/repos/mods/mod-a"
    assert second.options.cwd == "E:/repos/mods/mod-b"


def test_options_load_user_and_project_settings() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.setting_sources == ["user", "project"]


def test_empty_resume_becomes_none() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.resume is None


def test_resume_id_is_passed_through() -> None:
    client = make_factory().create("mod-a", resume="session-42")
    assert client.options.resume == "session-42"


def test_options_accept_edits_inside_the_working_directory() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.permission_mode == "auto"


def test_chat_sessions_are_marked_so_terminal_hooks_skip_them() -> None:
    client = make_factory().create("mod-a", "")
    assert client.options.env == {"WORKBENCH_CHAT_SESSION": "1",
                                  "WORKBENCH_CHAT_OWNER": "mod-a"}


def test_can_use_tool_is_passed_to_the_options() -> None:
    async def callback(name: str, tool_input: dict, context: object) -> object:
        return None

    client = make_factory().create("mod-a", "", can_use_tool=callback)
    assert client.options.can_use_tool is callback


def test_system_prompt_appends_to_the_claude_code_preset() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.system_prompt["type"] == "preset"
    assert client.options.system_prompt["preset"] == "claude_code"


def test_system_prompt_append_carries_the_chat_name() -> None:
    client = make_factory().create("mod-a", resume="")
    assert "raised_by: chat-mod-a" in client.options.system_prompt["append"]


def test_ask_user_question_is_disallowed() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.disallowed_tools == ["AskUserQuestion"]


def test_app_chats_run_on_sonnet_by_default() -> None:
    client = make_factory().create("mod-a", "")
    assert client.options.model == "sonnet"


def test_model_can_be_overridden_in_the_constructor() -> None:
    factory = SdkClientFactory(FakeDirectory(), model="opus")
    client = factory.create("mod-a", "")
    assert client.options.model == "opus"


def test_stream_buffer_holds_a_pasted_image_read() -> None:
    client = make_factory().create("mod-a", resume="")
    assert client.options.max_buffer_size >= 32 * 1024 * 1024
