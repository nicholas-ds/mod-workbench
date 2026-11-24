"""Reader-crash tests: the turn error names the reader's real exception (WI-6)."""

from workbench.chat.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat.chat_event import KIND_ERROR, KIND_TEXT, ChatEvent
from workbench.chat.session_id_store import SessionIdStore

from runner_fakes import make_assistant, make_runner

BUFFER_ERROR = "JSON message exceeded maximum buffer size"


async def test_reader_crash_names_the_real_error() -> None:
    runner, factory = make_runner(SessionIdStore(None), (make_assistant("hi"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    client = factory.clients[0]
    client.stream_error = RuntimeError(BUFFER_ERROR)
    await client.disconnect()
    error = await stream.__anext__()
    assert error == ChatEvent(
        KIND_ERROR,
        "The Claude session ended before the turn finished: " + BUFFER_ERROR,
    )
