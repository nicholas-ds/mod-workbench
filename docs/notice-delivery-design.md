# Notice delivery design (Opus design agent, 2026-11-23)

Goal: board answers, notes and messages reach the session that raised the board. See tracking.md, "Board answers reach the owner session".

## Why BoardNotifier fails
It branches on the `raised_by` string. An unknown owner returns False and nothing shows. It has no inbox, retry or record. Note text goes inline. There is no context rule. `MessagesRoutes._deliver` copies pane delivery.

## Classes (new package `workbench/notices/`)
- `OwnerId` (frozen: `OwnerKind` PANE or CHAT, `key`). `parse()` reads old `raised_by` values.
- `BoardOwnerStore` (edge): `boards/<state>/<id>/owner.toml`, written once by the server.
- `BoardOwnerStamper`: on PostToolUse of a `boards/open/*/board.md` edit, reads the session env (`WMUX_SURFACE_ID` or `WORKBENCH_OWNER=chat:<name>`) and returns the `OwnerId`. The agent never types an owner.
- `OwnerResolver`: owner.toml, then old `raised_by`, then main-orchestrator with `known=False`. Never None.
- `Notice` (frozen) and `NoticeComposer`: one line with a file path. No answer text.
- `DeliveryRecord` (frozen): state pending, delivered, fresh_started, failed, unknown_owner. Attempts, last try, error.
- `OwnerInbox` (edge): `status/inbox/<owner>/<notice-id>.toml`, written before any send.
- `RecipientTraits` (frozen descriptor for the UI).
- `Recipient` (abstract base): shared `deliver(notice, route)`. Abstract: `is_reachable`, `context_percent`, `send_line`, `start_fresh`, `traits`.
- `PaneRecipient`, `ChatRecipient`. Claude vs GLM needs no subclass: GLM returns no context percent, so it always gets SEND.
- `RecipientResolver`: the one place that picks the variant.
- `ContextPolicy`: above 25.0 percent returns FRESH. Below or unknown returns SEND.
- `FreshStartPrompt`: latest handoff plus the notice file.
- `NoticeDispatcher`: the pipeline. Replaces `BoardNotifier`.
- `DeliveryRetrier`: async retry with backoff in the server lifespan.
- `PaneContextReader`, `routes_notices.py` (list, retry).

## Pipeline
resolve owner, compose notice, write inbox record, resolve recipient, read context percent, pick route, deliver, update record, show state in the UI.

## Gap
No context meter exists for CLI panes. The statusline script reads `used_percentage` and only shows it. Fix: `scripts/context_recorder.py` writes it to `status/<stem>.toml`. It changes a user-level file, so the author must agree.

## Build order (each step: 3 to 5 files, one test file each)
1. owner_id, notice types, context_policy
2. board_owner_store, owner_resolver, owner_inbox
3. notice_composer, fresh_start_prompt
4. recipient, pane_recipient, pane_context_reader
5. chat_recipient, recipient_resolver
6. notice_dispatcher, delivery_retrier, routes_boards, api, delete board_notifier
7. board_owner_stamper, activity_hook, sdk_client_factory, chat_session_note, board_check
8. context_recorder, routes_notices, routes_messages, UI chip (orchestrator design review)

## Unchecked
`folder_of` with `orchestrator~tN` names. Hooks inside SDK chat sessions. Stamping GLM chats. A wmux pane spawner (none exists, so a pane fresh start uses `/clear`).
