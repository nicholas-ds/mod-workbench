"""Factory for Claude SDK client instances."""

from typing import Protocol

from claude_agent_sdk import CanUseTool, ClaudeAgentOptions, ClaudeSDKClient

from workbench.chat.chat_session_note import ChatSessionNote


CHAT_PERMISSION_MODE = "auto"
CHAT_SESSION_ENV = "WORKBENCH_CHAT_SESSION"
CHAT_OWNER_ENV = "WORKBENCH_CHAT_OWNER"
ASK_TOOL = "AskUserQuestion"
CHAT_MODEL = "sonnet"


class FolderLookup(Protocol):
    def folder_of(self, name: str) -> str: ...


class SdkClientFactory:
    """Builds ClaudeSDKClient instances in a named orchestrator's folder."""

    def __init__(
        self,
        directory: FolderLookup,
        note: ChatSessionNote = ChatSessionNote(),
        model: str = CHAT_MODEL,
    ) -> None:
        self._directory = directory
        self._note = note
        self._model = model

    def create(
        self, name: str, resume: str, can_use_tool: CanUseTool | None = None
    ) -> ClaudeSDKClient:
        options = ClaudeAgentOptions(
            model=self._model,
            cwd=self._directory.folder_of(name),
            setting_sources=["user", "project"],
            permission_mode=CHAT_PERMISSION_MODE,
            env={CHAT_SESSION_ENV: "1", CHAT_OWNER_ENV: name},
            resume=resume or None,
            can_use_tool=can_use_tool,
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": self._note.text(name),
            },
            disallowed_tools=[ASK_TOOL],
        )
        return ClaudeSDKClient(options=options)
