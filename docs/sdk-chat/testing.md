# SDK chat testing plan

Status: draft 1, 2026-11-11. Unverified items are marked. Style follows `tests/test_alerts.py` and `tests/test_routes_agents.py`.

## Rules

- Write the test first. Then write the class.
- One test file per class. File name is the class in snake case.
- Test names state the behavior: `test_clear_command_drops_session_id` (in the runner test).
- A test builds its own inputs. No hidden state. No shared fixtures between files.
- Pure classes take plain values. Edge classes take injected fakes.
- Run `.venv/Scripts/python -m pytest` for the full suite.

## Unit tests per Phase 1 class

| Class | Test file | Behaviors (test names) |
|---|---|---|
| `ChatEvent` | `test_chat_event.py` | `test_chat_event_round_trips_through_json` |
| `ClaudeSdkTranslator` | `test_claude_sdk_translator.py` | `test_text_block_becomes_text_event`, `test_tool_use_block_becomes_tool_event`, `test_thinking_block_becomes_chip_event`, `test_result_becomes_result_event_with_cost`, `test_error_result_becomes_error_event` |
| `SlashCommandParser` | `test_slash_command_parser.py` | `test_clear_text_becomes_clear_command`, `test_plain_text_is_a_prompt`, `test_blank_text_is_rejected` |
| `SessionIdStore` | `test_session_id_store.py` | `test_save_then_load_returns_session_id`, `test_missing_name_returns_none`, `test_clear_removes_session_id` |
| `ClaudeSessionRunner` | `test_claude_session_runner.py` | `test_prompt_streams_events_from_fake_client`, `test_interrupt_stops_turn_keeps_session`, `test_clear_forgets_session_id`, `test_runner_reuses_saved_session_id` |
| `routes_chat.py` | `test_routes_chat.py` | `test_post_chat_returns_event_stream`, `test_post_stop_answers_ok`, `test_unknown_orchestrator_answers_404` |
| `web/chat.js` | none | Checked by hand in the browser. Not a pytest target. |

Translator inputs are sample SDK messages captured from `scripts/sdk_spike.py`. Store them as plain dicts in the test file. This keeps tests true to real SDK shapes.

## Fake SDK client

`ClaudeSessionRunner` takes its client through the constructor. The fake stands in for `ClaudeSDKClient`:

- `connect`, `query`, `interrupt`, `disconnect` record each call.
- `receive_response` yields a fixed tuple of canned SDK messages.
- A `fail` flag makes `query` raise. This tests the error event path.
- No network, no subprocess, no cost.

## Route tests

Build a FastAPI app with `routes_chat` wired to the fake runner, as `test_routes_agents.py` does. Post a prompt with `TestClient`. Then read the server-sent event stream and check the `data:` lines. Streaming through `TestClient` is unverified. If it fails, collect events into one JSON response for the test and keep SSE for the browser.

## ChatEvent contract (R8)

One test asserts the JSON contract:

- `dataclasses.asdict(event)` holds only str, int, float, bool, list, and dict with str keys.
- `json.dumps` then `json.loads` returns equal values.
- `kind` is one of `text`, `thinking`, `tool`, `result`, `error`.

These asserts are the R8 boundary contract. A Rust replacement must pass the same asserts.

## Manual live check (costs money)

One real SDK turn bills like a normal session. A cold spike run cost about 0.14 USD. Run all checks in one session, in this order:

1. Skills load: the reply shows an `opencode-agent` skill use.
2. The reply quotes the `CLAUDE.md` GLM rule. Still unverified.
3. `/clear` drops the session id. The next message starts a new session id.
4. Stop ends the turn and keeps the session id.
5. A permission request shows Allow and Deny. The turn resumes after the choice.


## Risks

- The SDK may rename message types between versions. Pin `claude-agent-sdk` 0.2.180. Re-capture samples after an upgrade.
- `ThinkingBlock.thinking` came back empty. The chip event may carry no text.
- SSE through `TestClient` is unverified. The route test may need the JSON fallback.

## Open questions for the author

- May tests store captured real SDK message samples in the repo? Default: yes, as small dicts in the test file.
- Should route tests use SSE or the collected-JSON fallback from day one? Default: try SSE first. Fall back only if `TestClient` blocks it.
