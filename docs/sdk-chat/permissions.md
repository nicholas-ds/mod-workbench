# SDK chat: permissions (Phase 2)

Status: draft 1, 2026-11-11. SDK facts from `claude-agent-sdk` 0.2.180 source; paths below. See `design.md` and `docs/sdk-notes.md`.

## Problem

The SDK runs Claude with no terminal, so the CLI permission prompt has no screen. A tool that needs approval stalls the turn with no way to answer. The chat must show the request and send the answer back.

## How the SDK asks

`ClaudeAgentOptions.can_use_tool` (types.py:2526) replaces the interactive prompt. The CLI calls it when its permission rules evaluate to "ask". Signature (types.py:278):

```python
CanUseTool = Callable[[str, dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]]
```

The arguments are `tool_name`, `tool_input`, `context`. `ToolPermissionContext` (types.py:223) carries `title` ("Claude wants to read foo.txt"), `display_name` ("Read file"), `description`, `blocked_path`, `decision_reason`, `tool_use_id`. Use `title` as the card text; fall back to `display_name` plus input.

The callback returns one of (types.py:259, 268):

- `PermissionResultAllow(updated_input=None, updated_permissions=None)`
- `PermissionResultDeny(message="", interrupt=False)`; `interrupt=True` also ends the turn.

The callback never fires for tools already allowed by `allowed_tools`, `permission_mode`, or `permissions.allow` settings.

## Design

`PermissionCardBuilder` (pure) turns a callback call into a display card.

- `build_card(tool_name: str, tool_input: dict, context: ToolPermissionContext) -> ChatEvent`, with `kind="permission"`, `text=context.title or display_name`, `tool_name`, `detail=request_id`.

`PendingPermissionStore` (edge) holds open requests and wakes the waiting callback.

- `hold(card: ChatEvent) -> str` registers the request and returns its id.
- `answer(request_id: str, allowed: bool) -> bool` resolves the future; False means unknown or stale id.
- `await_decision(request_id: str, timeout_s: float) -> PermissionResult` returns Allow on a click, Deny on timeout.
- `fail_all(reason: str) -> None` resolves every open request as deny.

Flow: `ClaudeSessionRunner` (edge) sets `can_use_tool`. The callback builds the card, pushes the event to the stream, then awaits the decision. The runner converts the decision to a `PermissionResult`.

Chat box: a card shows the title, a tool chip, and Allow and Deny buttons. A click POSTs `{"request_id", "decision"}` to the new route `POST /chat/<name>/permission` in `routes_chat.py`, which calls `PendingPermissionStore.answer`. The card then shows the outcome as plain text.

## Permission modes

`set_permission_mode` (client.py:314) accepts these values per its docstring:

| Mode | Behavior |
|---|---|
| `default` | CLI prompts for dangerous tools; "ask" calls reach `can_use_tool` |
| `acceptEdits` | Auto-accepts file edits |
| `plan` | Plan-only; no tool execution |
| `bypassPermissions` | Allows all tools; callback never fires |
| `dontAsk` | Denies anything not pre-approved by allow rules |
| `auto` | A model classifier approves or denies each call |

Decided by the author (board sdk-design-review, 2026-11-12): `acceptEdits`, and only edits inside the repo or mod directory. Phase 1 sets `permission_mode="acceptEdits"` with the session folder as `cwd`. Whether the SDK asks for edits outside `cwd` is unverified: check it live. Other tools (shell commands) that settings do not allow ask through a chat card from Phase 2. Until then they are refused.

## Timeout, Stop, restart

- Timeout: an open request denies itself after 10 minutes; the card shows "timed out".
- Stop: the Stop button calls `interrupt()` (client.py:308), then the runner calls `fail_all("turn stopped")`, so no callback hangs.
- Restart: the process dies and open requests die with it. A resumed session continues after the last finished turn; the interrupted turn is lost, so the author re-sends the message. The session id survives in `SessionIdStore`.

## Risks

- `allowed_tools=["Read", ...]` alongside `can_use_tool` emits a shadow warning (types.py:2534). Use settings `permissions.allow` instead. Unverified that settings rules stay warning-free.
- Two orchestrators may ask at the same time. Each card carries its own request id. Untested.
- `context.title` may be absent for some tools. The fallback text is unverified in a live run.
- The SDK may rename these types between versions. Pin 0.2.180.

## Open questions for the author

- Timeout for an unanswered card (default: 10 minutes, then deny).
- Deny behavior: continue the turn with the deny message, or end it (default: continue, `interrupt=False`).
- Card look and button placement (default: card in the chat flow, buttons inline).
