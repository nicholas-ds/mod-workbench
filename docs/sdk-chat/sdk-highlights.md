# SDK highlights: what the dictionaries offer that we could use

Date: 2026-11-12. Asked by the author: list every connection point so nothing interesting is missed. The full lists are generated from the source, so they are exact: `sdk-surfaces.md` (Claude Agent SDK 0.2.180) and `opencode-surfaces.md` (OpenCode server, 188 operations). This file is my reading of them. Nothing below is built unless it says so. Every use is unverified until tried.

## Claude Agent SDK

| Surface | What it gives us | Idea for the workbench |
|---|---|---|
| `can_use_tool` | Our code decides each tool permission | Allow and Deny buttons in chat (Phase 2) |
| `permission_mode`, `set_permission_mode` | Change the mode during a session | A mode chip in the chat header |
| `hooks` (10 events, in process) | Our Python runs on `PreToolUse`, `Stop`, `PermissionRequest` and more | Guard rails in code: refuse edits outside the repo, refuse `git push`. Could replace the HTTP hooks in `settings.json` |
| `create_sdk_mcp_server`, `tool` | Our own tools, in process | Tools for `raise_board`, `read_answers`, `update_tracking`. Agents would ask you through a typed call, not through files and skills |
| `get_server_info` | The list of available slash commands | The slash picker already on the task list |
| `get_context_usage` | Context window by category | Context meter (Phase 2) |
| `include_partial_messages` | Streaming of partial text | Typing effect in the chat |
| `enable_file_checkpointing`, `rewind_files` | Restore files to an earlier turn | An "undo this turn" button |
| `fork_session`, `resume_session_at` | Branch or go back in a conversation | "Redo from here" on any message |
| `list_sessions`, `get_session_messages`, `rename_session`, `tag_session` | Read and manage saved sessions, including terminal ones | A history list in the chat page |
| `session_store` | Mirror transcripts to our own store | Keep chat history in plain files we control (rule R1) |
| `system_prompt`, `agents`, `skills`, `plugins` | Shape the session in code | Send the view context (which board you look at) as part of the prompt, not a `[workbench]` line |
| `model`, `fallback_model`, `effort`, `thinking`, `max_budget_usd`, `max_turns`, `task_budget` | Per-session limits and model choice | A model picker and spending guards, hidden until you want them |
| `sandbox`, `add_dirs` | Isolate commands, widen folder access | Enforce "edits only inside the repo" in the SDK, not by habit |
| `query()` | One-shot calls | Small background jobs on a cheap model (summaries, board drafts) |
| `output_format` | Structured JSON answers | Boards or status written by the model in a fixed shape |
| `RateLimitEvent` | Usage and reset times in the stream | A quiet usage warning (the spike showed 81% of the weekly limit) |
| `TaskStartedMessage`, `TaskProgressMessage`, `stop_task` | Subagent progress and stop | Show and stop subagents from the chat |
| `get_mcp_status`, `toggle_mcp_server`, `reconnect_mcp_server` | Control MCP servers | An MCP status line, for example when Ghidra fails to connect |

## OpenCode server

Groups with the most operations: `/api` (58), `/session` (27), `/experimental` (25), `/tui` (13), `/mcp` (8), `/pty` (8), `/global` (6). Useful for GLM chat (Phase 3):

- `/session`, `/event`: create, prompt, stream (already planned in `glm-chat.md`).
- `/permission`, `/question`: answer worker permission and question prompts from the chat, instead of the `session.ps1` supervisor.
- `/file`, `/find`, `/vcs`: read files and see the diff a worker made. The review step ("the diff is the evidence") could be one click.
- `/provider`, `/config`, `/agent`, `/skill`, `/command`: list models, agents and commands for pickers.
- `/pty`: terminal sessions over HTTP (a live shell view is possible).
- `/tui`: drive an OpenCode terminal UI from outside.

## Update awareness

The SDK bundles its own copy of Claude Code (CLI 2.1.321 inside SDK 0.2.180). The installed `claude` is 2.1.322 and OpenCode is 1.19.3. A version check for all three is being built (see tracking). After any update, run `scripts/sdk_surfaces.py` again and read the diff of the two dictionary files to see what is new.
