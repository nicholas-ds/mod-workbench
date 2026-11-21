# Claude Agent SDK dictionary

Package `claude-agent-sdk` 0.2.180. It bundles Claude Code CLI 2.1.321.

Generated from the package source by `scripts/sdk_surfaces.py`. Do not edit by hand.

## Map: every exported name by group

- **Hooks (run your code on SDK events)** (39): `BaseHookInput`, `CwdChangedHookSpecificOutput`, `ElicitationHookSpecificOutput`, `ElicitationResultHookSpecificOutput`, `FileChangedHookSpecificOutput`, `HookCallback`, `HookContext`, `HookEffort`, `HookEventMessage`, `HookInput`, `HookJSONOutput`, `HookMatcher`, `MessageDisplayHookSpecificOutput`, `NotificationHookInput`, `NotificationHookSpecificOutput`, `PermissionDeniedHookSpecificOutput`, `PermissionRequestHookInput`, `PermissionRequestHookSpecificOutput`, `PostModelSwitchHookSpecificOutput`, `PostToolBatchHookSpecificOutput`, `PostToolUseFailureHookInput`, `PostToolUseFailureHookSpecificOutput`, `PostToolUseHookInput`, `PostToolUseHookSpecificOutput`, `PreCompactHookInput`, `PreModelSwitchHookSpecificOutput`, `PreToolUseHookInput`, `PreToolUseHookSpecificOutput`, `SessionStartHookSpecificOutput`, `StopHookInput`, `StopHookSpecificOutput`, `SubagentStartHookInput`, `SubagentStartHookSpecificOutput`, `SubagentStopHookInput`, `SubagentStopHookSpecificOutput`, `UserPromptExpansionHookSpecificOutput`, `UserPromptSubmitHookInput`, `UserPromptSubmitHookSpecificOutput`, `WorktreeCreateHookSpecificOutput`
- **Permissions (approve or deny tool use)** (9): `CanUseTool`, `CanUseToolShadowedWarning`, `DeferredToolUse`, `PermissionMode`, `PermissionResult`, `PermissionResultAllow`, `PermissionResultDeny`, `PermissionUpdate`, `ToolPermissionContext`
- **Messages (what the session streams to you)** (16): `AssistantMessage`, `ConversationResetMessage`, `Message`, `MessageOrigin`, `MessageOriginKind`, `MirrorErrorMessage`, `RateLimitEvent`, `ResultMessage`, `SessionMessage`, `StreamEvent`, `SystemMessage`, `TaskNotificationMessage`, `TaskProgressMessage`, `TaskStartedMessage`, `TaskUpdatedMessage`, `UserMessage`
- **Content blocks (parts of a message)** (7): `ContentBlock`, `ServerToolResultBlock`, `ServerToolUseBlock`, `TextBlock`, `ThinkingBlock`, `ToolResultBlock`, `ToolUseBlock`
- **MCP and custom tools (give Claude your own tools)** (13): `McpSdkServerConfig`, `McpServerConfig`, `McpServerConnectionStatus`, `McpServerInfo`, `McpServerStatus`, `McpServerStatusConfig`, `McpStatusResponse`, `McpToolAnnotations`, `McpToolInfo`, `SdkMcpTool`, `ToolAnnotations`, `create_sdk_mcp_server`, `tool`
- **Session history and storage** (29): `SessionCronSummary`, `SessionKey`, `SessionListSubkeysKey`, `SessionStore`, `SessionStoreEntry`, `SessionStoreFlushMode`, `SessionStoreListEntry`, `SessionSummaryEntry`, `delete_session`, `delete_session_via_store`, `fold_session_summary`, `fork_session`, `fork_session_via_store`, `get_session_info`, `get_session_info_from_store`, `get_session_messages`, `get_session_messages_from_store`, `get_subagent_messages`, `get_subagent_messages_from_store`, `import_session_to_store`, `list_sessions`, `list_sessions_from_store`, `list_subagents`, `list_subagents_from_store`, `project_key_for_directory`, `rename_session`, `rename_session_via_store`, `tag_session`, `tag_session_via_store`
- **Errors** (7): `CLIConnectionError`, `CLIJSONDecodeError`, `CLINotFoundError`, `ClaudeSDKError`, `ProcessError`, `ResultError`, `SystemInitPluginError`
- **Sandbox** (3): `SandboxIgnoreViolations`, `SandboxNetworkConfig`, `SandboxSettings`
- **Thinking and effort** (7): `EffortLevel`, `FastModeDisabledReason`, `FastModeState`, `ThinkingConfig`, `ThinkingConfigAdaptive`, `ThinkingConfigDisabled`, `ThinkingConfigEnabled`
- **Tasks and subagents** (7): `AgentDefinition`, `BackgroundTaskSummary`, `TaskBudget`, `TaskNotificationOriginSubkind`, `TaskNotificationStatus`, `TaskUpdatedStatus`, `TaskUsage`
- **Clients and options** (10): `ClaudeAgentOptions`, `ClaudeSDKClient`, `SdkBeta`, `SdkPluginConfig`, `SettingSource`, `SystemInitData`, `SystemInitMcpServer`, `SystemInitPlugin`, `Transport`, `query`
- **Other** (12): `ContextUsageCategory`, `ContextUsageResponse`, `ForkSessionResult`, `InMemorySessionStore`, `ModelUsage`, `RateLimitInfo`, `RateLimitStatus`, `RateLimitType`, `SDKSessionInfo`, `ServerToolName`, `TERMINAL_TASK_STATUSES`, `__version__`

## The two central classes

### `ClaudeAgentOptions`

Query options for Claude SDK.

| Field | Type | Default | What it does |
|---|---|---|---|
| `tools` | `list[str] \| ToolsPreset \| None` | `None` | Specify the base set of available built-in tools. |
| `allowed_tools` | `list[str]` | `field(default_factory=list)` | Tool names that are auto-allowed without prompting for permission. |
| `system_prompt` | `str \| SystemPromptPreset \| SystemPromptCustom \| SystemPromptFile \| None` | `None` | System prompt configuration. |
| `mcp_servers` | `dict[str, McpServerConfig] \| str \| Path` | `field(default_factory=dict)` | MCP (Model Context Protocol) server configurations. |
| `strict_mcp_config` | `bool` | `False` | When ``True``, only use MCP servers passed via :attr:`mcp_servers`, |
| `permission_mode` | `PermissionMode \| None` | `None` | Permission mode for the session. |
| `continue_conversation` | `bool` | `False` | Continue the most recent conversation in the current directory instead of |
| `resume` | `str \| None` | `None` | Session ID to resume. Loads the conversation history from the specified session. |
| `session_id` | `str \| None` | `None` | Use a specific session ID for the conversation instead of an auto-generated one. |
| `max_turns` | `int \| None` | `None` | Maximum number of conversation turns before the query stops. |
| `max_budget_usd` | `float \| None` | `None` | Maximum budget in USD for the query. |
| `disallowed_tools` | `list[str]` | `field(default_factory=list)` | Tool names that are disallowed. |
| `model` | `str \| None` | `None` | Claude model to use. Defaults to the CLI default model. |
| `fallback_model` | `str \| None` | `None` | Fallback model to use if the primary model fails or is unavailable. |
| `betas` | `list[SdkBeta]` | `field(default_factory=list)` | Enable beta features. |
| `permission_prompt_tool_name` | `str \| None` | `None` | MCP tool name to use for permission prompts. |
| `cwd` | `str \| Path \| None` | `None` | Current working directory for the session. Defaults to the process cwd. |
| `cli_path` | `str \| Path \| None` | `None` | Path to the Claude Code CLI executable. |
| `settings` | `str \| None` | `None` | Path to an additional settings JSON file to load, or an inline JSON string. |
| `add_dirs` | `list[str \| Path]` | `field(default_factory=list)` | Additional directories Claude can access beyond the current working directory. |
| `env` | `dict[str, str]` | `field(default_factory=dict)` | Environment variables to pass to the Claude Code subprocess. |
| `extra_args` | `dict[str, str \| None]` | `field(default_factory=dict)` | Additional CLI arguments to pass to Claude Code. |
| `max_buffer_size` | `int \| None` | `None` | Maximum bytes to buffer when reading the CLI subprocess stdout. |
| `debug_stderr` | `Any` | `sys.stderr` | Deprecated and no longer read by the transport. Use the ``stderr`` callback. |
| `stderr` | `Callable[[str], None] \| None` | `None` | Callback for stderr output from the Claude Code subprocess. |
| `can_use_tool` | `CanUseTool \| None` | `None` | Custom permission handler for tool calls that would otherwise prompt the user. |
| `hooks` | `dict[HookEvent, list[HookMatcher]] \| None` | `None` | Hook callbacks for responding to various events during execution. |
| `user` | `str \| None` | `None` | Optional user identifier associated with the session. |
| `include_partial_messages` | `bool` | `False` | Include partial/streaming message events in the output. |
| `include_hook_events` | `bool` | `False` | Include hook lifecycle events in the message stream. |
| `forward_subagent_text` | `bool` | `False` | Forward subagent text and thinking blocks as messages in the stream. |
| `verbatim_prompts` | `bool` | `False` | Deliver every prompt to Claude as written. |
| `fork_session` | `bool` | `False` | When true, resumed sessions fork to a new session ID rather than |
| `resume_session_at` | `str \| None` | `None` | When resuming, only load the conversation up to and including the |
| `resume_drops_turn` | `str \| None` | `None` | With ``resume_session_at``: the UUID of the user prompt whose turn this |
| `agents` | `dict[str, AgentDefinition] \| None` | `None` | Programmatically define custom subagents invokable via the Agent tool. |
| `setting_sources` | `list[SettingSource] \| None` | `None` | Control which filesystem settings to load. |
| `skills` | `list[str] \| Literal['all'] \| None` | `None` | Skills to enable for the main session. |
| `sandbox` | `SandboxSettings \| None` | `None` | Sandbox settings for command execution isolation. |
| `plugins` | `list[SdkPluginConfig]` | `field(default_factory=list)` | Load plugins for this session. |
| `max_thinking_tokens` | `int \| None` | `None` | Maximum tokens the model may use for its thinking/reasoning process. |
| `thinking` | `ThinkingConfig \| None` | `None` | Controls Claude's thinking/reasoning behavior. |
| `effort` | `EffortLevel \| None` | `None` | Controls how much effort Claude puts into its response. |
| `output_format` | `dict[str, Any] \| None` | `None` | Output format configuration for structured responses. |
| `enable_file_checkpointing` | `bool` | `False` | Enable file checkpointing to track file changes during the session. |
| `session_store` | `SessionStore \| None` | `None` | Mirror session transcripts to an external store. |
| `session_store_flush` | `SessionStoreFlushMode` | `'batched'` | When to flush mirrored transcript entries to ``session_store``. |
| `load_timeout_ms` | `int` | `60000` | Timeout for each ``session_store.load()`` / ``list_subkeys()`` call during |
| `task_budget` | `TaskBudget \| None` | `None` | API-side task budget in tokens. |

### `ClaudeSDKClient`

Client for bidirectional, interactive conversations with Claude Code.

| Name | Signature | What it does |
|---|---|---|
| `async connect` | `(self, prompt: str \| AsyncIterable[dict[str, Any]] \| None=None) -> None` | Connect to Claude with a prompt or message stream. |
| `async receive_messages` | `(self) -> AsyncIterator[Message]` | Receive all messages from Claude. |
| `async query` | `(self, prompt: str \| AsyncIterable[dict[str, Any]], session_id: str='default') -> None` | Send a new request in streaming mode. |
| `async interrupt` | `(self) -> None` | Send interrupt signal (only works with streaming mode). |
| `async set_permission_mode` | `(self, mode: PermissionMode) -> None` | Change permission mode during conversation (only works with streaming mode). |
| `async set_model` | `(self, model: str \| None=None) -> None` | Change the AI model during conversation (only works with streaming mode). |
| `async rewind_files` | `(self, user_message_id: str) -> None` | Rewind tracked files to their state at a specific user message. |
| `async reconnect_mcp_server` | `(self, server_name: str) -> None` | Reconnect a disconnected or failed MCP server (only works with streaming mode). |
| `async toggle_mcp_server` | `(self, server_name: str, enabled: bool) -> None` | Enable or disable an MCP server (only works with streaming mode). |
| `async stop_task` | `(self, task_id: str) -> None` | Stop a running task (only works with streaming mode). |
| `async get_mcp_status` | `(self) -> McpStatusResponse` | Get current MCP server connection status (only works with streaming mode). |
| `async get_context_usage` | `(self) -> ContextUsageResponse` | Get a breakdown of current context window usage by category. |
| `async get_server_info` | `(self) -> dict[str, Any] \| None` | Get server initialization info including available commands and output styles. |
| `async receive_response` | `(self) -> AsyncIterator[Message]` | Receive messages from Claude until and including a ResultMessage. |
| `async disconnect` | `(self) -> None` | Disconnect from Claude. |

## Exported functions

| Name | Signature | What it does |
|---|---|---|
| `async query` | `(*, prompt: str \| AsyncIterable[dict[str, Any]], options: ClaudeAgentOptions \| None=None, transport: Transport \| None=None) -> AsyncIterator[Message]` | Query Claude Code for one-shot or unidirectional streaming interactions. |
| `list_sessions` | `(directory: str \| None=None, limit: int \| None=None, offset: int=0, include_worktrees: bool=True) -> list[SDKSessionInfo]` | Lists sessions with metadata extracted from stat + head/tail reads. |
| `get_session_info` | `(session_id: str, directory: str \| None=None) -> SDKSessionInfo \| None` | Reads metadata for a single session by ID. |
| `get_session_messages` | `(session_id: str, directory: str \| None=None, limit: int \| None=None, offset: int=0) -> list[SessionMessage]` | Reads a session's conversation messages from its JSONL transcript file. |
| `list_subagents` | `(session_id: str, directory: str \| None=None) -> list[str]` | Lists subagent IDs for a given session by scanning the subagents directory. |
| `get_subagent_messages` | `(session_id: str, agent_id: str, directory: str \| None=None, limit: int \| None=None, offset: int=0) -> list[SessionMessage]` | Reads a subagent's conversation messages from its JSONL transcript file. |
| `project_key_for_directory` | `(directory: str \| Path \| None=None) -> str` | Derive the :class:`SessionStore` ``project_key`` for a directory. |
| `async import_session_to_store` | `(session_id: str, store: SessionStore, *, directory: str \| None=None, include_subagents: bool=True, batch_size: int=MAX_PENDING_ENTRIES) -> None` | Replay a local session transcript into a :class:`SessionStore`. |
| `async list_sessions_from_store` | `(session_store: SessionStore, directory: str \| None=None, limit: int \| None=None, offset: int=0) -> list[SDKSessionInfo]` | List sessions from a :class:`SessionStore`. |
| `async get_session_info_from_store` | `(session_store: SessionStore, session_id: str, directory: str \| None=None) -> SDKSessionInfo \| None` | Read metadata for a single session from a :class:`SessionStore`. |
| `async get_session_messages_from_store` | `(session_store: SessionStore, session_id: str, directory: str \| None=None, limit: int \| None=None, offset: int=0) -> list[SessionMessage]` | Read a session's conversation messages from a :class:`SessionStore`. |
| `async list_subagents_from_store` | `(session_store: SessionStore, session_id: str, directory: str \| None=None) -> list[str]` | List subagent IDs for a session from a :class:`SessionStore`. |
| `async get_subagent_messages_from_store` | `(session_store: SessionStore, session_id: str, agent_id: str, directory: str \| None=None, limit: int \| None=None, offset: int=0) -> list[SessionMessage]` | Read a subagent's conversation messages from a :class:`SessionStore`. |
| `rename_session` | `(session_id: str, title: str, directory: str \| None=None) -> None` | Rename a session by appending a custom-title entry. |
| `tag_session` | `(session_id: str, tag: str \| None, directory: str \| None=None) -> None` | Tag a session. Pass ``None`` to clear the tag. |
| `delete_session` | `(session_id: str, directory: str \| None=None) -> None` | Delete a session by removing its JSONL file and subagent transcripts. |
| `fork_session` | `(session_id: str, directory: str \| None=None, up_to_message_id: str \| None=None, title: str \| None=None) -> ForkSessionResult` | Fork a session into a new branch with fresh UUIDs. |
| `async rename_session_via_store` | `(session_store: SessionStore, session_id: str, title: str, directory: str \| None=None) -> None` | Rename a session by appending a custom-title entry to a :class:`SessionStore`. |
| `async tag_session_via_store` | `(session_store: SessionStore, session_id: str, tag: str \| None, directory: str \| None=None) -> None` | Tag a session by appending a tag entry to a :class:`SessionStore`. |
| `async delete_session_via_store` | `(session_store: SessionStore, session_id: str, directory: str \| None=None) -> None` | Delete a session from a :class:`SessionStore`. |
| `async fork_session_via_store` | `(session_store: SessionStore, session_id: str, directory: str \| None=None, up_to_message_id: str \| None=None, title: str \| None=None) -> ForkSessionResult` | Fork a session into a new branch with fresh UUIDs via a :class:`SessionStore`. |
| `create_sdk_mcp_server` | `(name: str, version: str='1.0.0', tools: list[SdkMcpTool[Any]] \| None=None) -> McpSdkServerConfig` | Create an in-process MCP server that runs within your Python application. |
| `tool` | `(name: str, description: str, input_schema: type \| dict[str, Any], annotations: _McpToolAnnotations \| None=None) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]` | Decorator for defining MCP tools with type safety. |

## Types by group (fields in brackets)

### Hooks (run your code on SDK events)
- `BaseHookInput` [session_id, transcript_path, cwd, permission_mode, prompt_id, effort] Base hook input fields present across many hook events.
- `CwdChangedHookSpecificOutput` [hookEventName, watchPaths] Hook-specific output for CwdChanged events.
- `ElicitationHookSpecificOutput` [hookEventName, action, content] Hook-specific output for Elicitation events.
- `ElicitationResultHookSpecificOutput` [hookEventName, action, content] Hook-specific output for ElicitationResult events.
- `FileChangedHookSpecificOutput` [hookEventName, watchPaths] Hook-specific output for FileChanged events.
- `HookContext` [signal] Context information for hook callbacks.
- `HookEffort` [level] Reasoning effort in effect when a hook fires.
- `HookEventMessage` [hook_event_name, session_id, uuid] Hook event emitted by the CLI when ``include_hook_events`` is enabled.
- `HookMatcher` [matcher, hooks, timeout, on_failure] Hook matcher configuration.
- `MessageDisplayHookSpecificOutput` [hookEventName, displayContent] Hook-specific output for MessageDisplay events.
- `NotificationHookInput` [hook_event_name, message, title, notification_type] Input data for Notification hook events.
- `NotificationHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for Notification events.
- `PermissionDeniedHookSpecificOutput` [hookEventName, retry] Hook-specific output for PermissionDenied events.
- `PermissionRequestHookInput` [hook_event_name, tool_name, tool_input, permission_suggestions] Input data for PermissionRequest hook events.
- `PermissionRequestHookSpecificOutput` [hookEventName, decision] Hook-specific output for PermissionRequest events.
- `PostModelSwitchHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for PostModelSwitch events.
- `PostToolBatchHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for PostToolBatch events.
- `PostToolUseFailureHookInput` [hook_event_name, tool_name, tool_input, tool_use_id, error, is_interrupt, duration_ms] Input data for PostToolUseFailure hook events.
- `PostToolUseFailureHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for PostToolUseFailure events.
- `PostToolUseHookInput` [hook_event_name, tool_name, tool_input, tool_response, tool_use_id, duration_ms] Input data for PostToolUse hook events.
- `PostToolUseHookSpecificOutput` [hookEventName, additionalContext, updatedToolOutput, updatedMCPToolOutput] Hook-specific output for PostToolUse events.
- `PreCompactHookInput` [hook_event_name, trigger, custom_instructions] Input data for PreCompact hook events.
- `PreModelSwitchHookSpecificOutput` [hookEventName, permissionDecision, permissionDecisionReason] Hook-specific output for PreModelSwitch events.
- `PreToolUseHookInput` [hook_event_name, tool_name, tool_input, tool_use_id] Input data for PreToolUse hook events.
- `PreToolUseHookSpecificOutput` [hookEventName, permissionDecision, permissionDecisionReason, updatedInput, additionalContext] Hook-specific output for PreToolUse events.
- `SessionStartHookSpecificOutput` [hookEventName, additionalContext, initialUserMessage, sessionTitle, watchPaths, reloadSkills] Hook-specific output for SessionStart events.
- `StopHookInput` [hook_event_name, stop_hook_active, last_assistant_message, background_tasks, session_crons] Input data for Stop hook events.
- `StopHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for Stop events.
- `SubagentStartHookInput` [hook_event_name, agent_id, agent_type] Input data for SubagentStart hook events.
- `SubagentStartHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for SubagentStart events.
- `SubagentStopHookInput` [hook_event_name, stop_hook_active, agent_id, agent_transcript_path, agent_type, last_assistant_message, background_tasks, session_crons] Input data for SubagentStop hook events.
- `SubagentStopHookSpecificOutput` [hookEventName, additionalContext] Hook-specific output for SubagentStop events.
- `UserPromptExpansionHookSpecificOutput` [hookEventName, additionalContext, suppressOriginalPrompt] Hook-specific output for UserPromptExpansion events.
- `UserPromptSubmitHookInput` [hook_event_name, prompt] Input data for UserPromptSubmit hook events.
- `UserPromptSubmitHookSpecificOutput` [hookEventName, additionalContext, sessionTitle, suppressOriginalPrompt] Hook-specific output for UserPromptSubmit events.
- `WorktreeCreateHookSpecificOutput` [hookEventName, worktreePath] Hook-specific output for WorktreeCreate events.

### Permissions (approve or deny tool use)
- `CanUseToolShadowedWarning` [] can_use_tool is set but some tool calls are auto-approved before it runs.
- `DeferredToolUse` [id, name, input] Tool use that was deferred by a PreToolUse hook returning ``"defer"``.
- `PermissionResultAllow` [behavior, updated_input, updated_permissions] Allow permission result.
- `PermissionResultDeny` [behavior, message, interrupt] Deny permission result.
- `PermissionUpdate` [type, rules, behavior, mode, directories, destination] Permission update configuration.
- `ToolPermissionContext` [signal, suggestions, tool_use_id, agent_id, blocked_path, decision_reason, title, display_name, description] Context information for tool permission callbacks.

### Messages (what the session streams to you)
- `AssistantMessage` [content, model, parent_tool_use_id, error, usage, message_id, stop_reason, session_id, uuid] Assistant message with content blocks.
- `ConversationResetMessage` [new_conversation_id, uuid, session_id] Emitted when the session's conversation is replaced without ending the
- `MirrorErrorMessage` [key, error] System message emitted when a :meth:`SessionStore.append` call fails.
- `RateLimitEvent` [rate_limit_info, uuid, session_id] Rate limit event emitted when rate limit info changes.
- `ResultMessage` [subtype, duration_ms, duration_api_ms, is_error, num_turns, session_id, stop_reason, total_cost_usd, usage, result, structured_output, model_usage, permission_denials, deferred_tool_use, errors, api_error_status, uuid, terminal_reason, origin] Result message with cost and usage information.
- `SessionMessage` [type, uuid, session_id, message, parent_tool_use_id, parent_agent_id] A user or assistant message from a session transcript.
- `StreamEvent` [uuid, session_id, event, parent_tool_use_id] Stream event for partial message updates during streaming.
- `SystemMessage` [subtype, data] System message with metadata.
- `TaskNotificationMessage` [task_id, status, output_file, summary, uuid, session_id, tool_use_id, usage] System message emitted when a task completes, fails, or is stopped.
- `TaskProgressMessage` [task_id, description, usage, uuid, session_id, tool_use_id, last_tool_name] System message emitted while a task is in progress.
- `TaskStartedMessage` [task_id, description, uuid, session_id, tool_use_id, task_type] System message emitted when a task starts.
- `TaskUpdatedMessage` [task_id, patch, status, session_id, uuid] System message emitted when a background task's state changes.
- `UserMessage` [content, uuid, parent_tool_use_id, tool_use_result, origin] User message.

### Content blocks (parts of a message)
- `ServerToolResultBlock` [tool_use_id, content] Result block returned for a server-side tool call.
- `ServerToolUseBlock` [id, name, input] Server-side tool use block (e.g. advisor, web_search, web_fetch).
- `TextBlock` [text] Text content block.
- `ThinkingBlock` [thinking, signature] Thinking content block.
- `ToolResultBlock` [tool_use_id, content, is_error] Tool result content block.
- `ToolUseBlock` [id, name, input] Tool use content block.
