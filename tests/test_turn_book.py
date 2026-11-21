"""Tests for the shared turn state book."""

import asyncio

from workbench.chat_event import ChatEvent, KIND_TEXT
from workbench.turn_book import TurnBook
from workbench.turn_event_log import TurnEventLog


async def test_begin_marks_running_and_end_clears_state() -> None:
    book = TurnBook()
    log = TurnEventLog()
    pump = asyncio.create_task(asyncio.sleep(0))
    book.begin("coder", log, pump)
    assert book.is_running("coder")
    assert book.log_of("coder") is log
    assert book.pump_of("coder") is pump
    book.end("coder")
    assert not book.is_running("coder")
    assert book.log_of("coder") is None
    assert book.pump_of("coder") is None
    await pump


def test_unknown_name_reads_empty() -> None:
    book = TurnBook()
    assert not book.is_running("coder")
    assert book.log_of("coder") is None
    assert book.pump_of("coder") is None
    assert book.take_holds("coder") == frozenset()
    assert book.dequeue("coder") is None


async def test_offer_appends_to_running_log_and_ignores_unknown_name() -> None:
    book = TurnBook()
    log = TurnEventLog()
    pump = asyncio.create_task(asyncio.sleep(0))
    book.begin("coder", log, pump)
    event = ChatEvent(kind=KIND_TEXT, text="hi")
    book.offer("coder", event)
    assert log.events() == (event,)
    book.offer("ghost", event)
    assert log.events() == (event,)
    book.end("coder")
    await pump


def test_take_holds_pops_remaining_holds_once() -> None:
    book = TurnBook()
    book.hold("coder", "r1")
    book.hold("coder", "r2")
    book.release("coder", "r1")
    assert book.take_holds("coder") == frozenset({"r2"})
    assert book.take_holds("coder") == frozenset()


def test_queue_is_fifo_and_drops_when_emptied() -> None:
    book = TurnBook()
    book.enqueue("coder", "first")
    book.enqueue("coder", "second")
    assert book.dequeue("coder") == "first"
    assert book.dequeue("coder") == "second"
    assert book.dequeue("coder") is None


def test_drop_queue_discards_pending_text() -> None:
    book = TurnBook()
    book.enqueue("coder", "only")
    book.drop_queue("coder")
    assert book.dequeue("coder") is None
