"""Sort exported SDK names into readable groups by their naming pattern."""

from __future__ import annotations

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Hooks (run your code on SDK events)", ("HookInput", "HookSpecificOutput", "HookCallback", "HookContext", "HookEvent", "HookJSONOutput", "HookMatcher", "HookEffort")),
    ("Permissions (approve or deny tool use)", ("Permission", "CanUseTool", "ToolPermissionContext", "DeferredToolUse")),
    ("Messages (what the session streams to you)", ("Message", "StreamEvent", "RateLimitEvent")),
    ("Content blocks (parts of a message)", ("Block",)),
    ("MCP and custom tools (give Claude your own tools)", ("Mcp", "SdkMcp", "Tool", "create_sdk_mcp_server", "build_tool_server", "tool")),
    ("Session history and storage", ("Session", "list_", "get_session", "delete_session", "fork_session", "rename_session", "tag_session", "import_session", "get_subagent", "fold_session", "project_key")),
    ("Errors", ("Error",)),
    ("Sandbox", ("Sandbox",)),
    ("Thinking and effort", ("Thinking", "Effort", "FastMode")),
    ("Tasks and subagents", ("Task", "AgentDefinition", "BackgroundTask")),
    ("Clients and options", ("ClaudeSDKClient", "ClaudeAgentOptions", "query", "Transport", "SdkPluginConfig", "SettingSource", "SdkBeta", "SystemInit")),
)
_OTHER = "Other"


class ExportGrouper:
    """Group names. The first matching rule wins. Pure."""

    def group(self, names: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
        groups: dict[str, list[str]] = {title: [] for title, _ in _RULES}
        groups[_OTHER] = []
        for name in names:
            groups[self._title_for(name)].append(name)
        return {title: tuple(sorted(items)) for title, items in groups.items() if items}

    def _title_for(self, name: str) -> str:
        for title, patterns in _RULES:
            if any(name == pattern or name.startswith(pattern) or name.endswith(pattern) for pattern in patterns):
                return title
        return _OTHER
