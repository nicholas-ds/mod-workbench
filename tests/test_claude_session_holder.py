"""Tests for the per-chat Claude session holder."""

import asyncio
from pathlib import Path

from holder_fakes import (
    FakeChatClient,
    FakeClientFactory,
    IDLE,
    NAME,
    PID,
    ResultRecorder,
    begin_turn,
    make_holder,
    running_job,
    unused_permission,
    wait_for,
)

from runner_fakes import make_assistant, make_result

import pytest

from workbench.chat_event import ChatEvent, KIND_RESULT, KIND_TEXT
from workbench.chat_job_book import ChatJobBook


async def test_open_twice_returns_same_client_with_one_reader(tmp_path: Path) -> None:
    holder, factory, _recorder, _jobs, _book = make_holder(tmp_path)
    first = await holder.open(NAME, unused_permission)
    second = await holder.open(NAME, unused_permission)
    assert first is second
    assert holder.client_of(NAME) is first
    assert factory.requested == [(NAME, "")]
    assert len(factory.clients) == 1
    assert len(holder._readers) == 1


async def test_open_saves_the_cli_pid(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    await holder.open(NAME, unused_permission)
    assert holder.pid_of(NAME) == PID


async def test_stream_messages_reach_turn_book_and_result_reaches_on_result(
    tmp_path: Path,
) -> None:
    holder, _factory, recorder, _jobs, book = make_holder(tmp_path)
    log = begin_turn(book, NAME)
    client = await holder.open(NAME, unused_permission)
    client.feed(make_assistant("hi"))
    client.feed(make_result("s1"))
    assert await wait_for(lambda: bool(recorder.results))
    assert log.events() == (ChatEvent(KIND_TEXT, "hi"), ChatEvent(KIND_RESULT))
    assert [name for name, _message in recorder.results] == [NAME]
    assert recorder.results[0][1].session_id == "s1"
    await holder.close(NAME)
    book.end(NAME)


async def test_result_without_running_job_closes_after_idle(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    client = await holder.open(NAME, unused_permission)
    client.feed(make_result("s1"))
    assert await wait_for(lambda: "disconnect" in client.calls)
    assert holder.client_of(NAME) is None
    assert holder.pid_of(NAME) is None


async def test_running_job_keeps_chat_open_until_finished(tmp_path: Path) -> None:
    holder, _factory, recorder, job_store, _book = make_holder(tmp_path)
    job_store.save(NAME, running_job())
    client = await holder.open(NAME, unused_permission)
    client.feed(make_result("s1"))
    assert await wait_for(lambda: bool(recorder.results))
    await asyncio.sleep(IDLE * 5)
    assert "disconnect" not in client.calls
    assert holder.client_of(NAME) is client
    job_store.save(NAME, ChatJobBook().finish(job_store.load(NAME), "j1", "done", 2))
    assert await wait_for(lambda: "disconnect" in client.calls)
    assert holder.client_of(NAME) is None


async def test_send_cancels_the_idle_timer(tmp_path: Path) -> None:
    holder, _factory, recorder, _jobs, _book = make_holder(tmp_path, idle_seconds=0.2)
    client = await holder.open(NAME, unused_permission)
    client.feed(make_result("s1"))
    assert await wait_for(lambda: bool(recorder.results))
    await holder.send(NAME, "again")
    await asyncio.sleep(0.5)
    assert "disconnect" not in client.calls
    assert holder.client_of(NAME) is client
    assert "query:again" in client.calls
    await holder.close(NAME)


async def test_send_without_open_chat_raises(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    with pytest.raises(RuntimeError):
        await holder.send(NAME, "hello")


async def test_close_twice_is_safe(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    client = await holder.open(NAME, unused_permission)
    await holder.close(NAME)
    await holder.close(NAME)
    assert client.calls.count("disconnect") == 1
    assert holder.client_of(NAME) is None
    assert holder.pid_of(NAME) is None


async def test_reader_closes_chat_after_stream_end_without_hanging(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    client = await holder.open(NAME, unused_permission)
    reader = holder._readers[NAME]
    client.feed(make_result("s1"))
    client.end_stream()
    await asyncio.wait_for(asyncio.shield(reader), timeout=2.0)
    assert holder.client_of(NAME) is None
    assert "disconnect" in client.calls


async def test_close_all_closes_every_chat(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    one = await holder.open("one", unused_permission)
    two = await holder.open("two", unused_permission)
    await holder.close_all()
    assert holder.client_of("one") is None
    assert holder.client_of("two") is None
    assert "disconnect" in one.calls
    assert "disconnect" in two.calls
    assert holder.pid_of("one") is None
    assert holder.pid_of("two") is None



async def test_idle_close_completes_a_disconnect_that_awaits(tmp_path: Path) -> None:
    holder, _factory, _recorder, _jobs, _book = make_holder(tmp_path)
    client = await holder.open(NAME, unused_permission)

    async def slow_disconnect() -> None:
        await asyncio.sleep(0.02)
        client.calls.append("disconnect")

    client.disconnect = slow_disconnect
    client.feed(make_result("s1"))
    assert await wait_for(lambda: "disconnect" in client.calls)
    assert holder.pid_of(NAME) is None
