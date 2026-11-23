"""Tests for the pending permission request store."""

import asyncio

from workbench.chat.pending_permission_store import PendingPermissionStore

WAIT_SECONDS = 0.05


async def test_answer_allow_wakes_the_waiter() -> None:
    store = PendingPermissionStore()
    request_id = store.hold()
    waiter = asyncio.create_task(store.await_decision(request_id, WAIT_SECONDS))
    await asyncio.sleep(0)
    assert store.answer(request_id, allowed=True) is True
    assert await waiter == "allowed"
    assert store.open_ids() == ()


async def test_answer_deny_wakes_the_waiter() -> None:
    store = PendingPermissionStore()
    request_id = store.hold()
    waiter = asyncio.create_task(store.await_decision(request_id, WAIT_SECONDS))
    await asyncio.sleep(0)
    assert store.answer(request_id, allowed=False) is True
    assert await waiter == "denied"
    assert store.open_ids() == ()


async def test_timeout_returns_timed_out_and_forgets_the_request() -> None:
    store = PendingPermissionStore()
    request_id = store.hold()
    decision = await store.await_decision(request_id, WAIT_SECONDS)
    assert decision == "timed out"
    assert store.open_ids() == ()
    assert store.answer(request_id, allowed=True) is False


async def test_unknown_id_answer_is_false() -> None:
    store = PendingPermissionStore()
    assert store.answer("missing", allowed=True) is False


async def test_second_answer_is_false() -> None:
    store = PendingPermissionStore()
    request_id = store.hold()
    assert store.answer(request_id, allowed=True) is True
    assert store.answer(request_id, allowed=True) is False


async def test_fail_all_denies_every_open_request() -> None:
    store = PendingPermissionStore()
    first = store.hold()
    second = store.hold()
    waiters = [
        asyncio.create_task(store.await_decision(first, WAIT_SECONDS)),
        asyncio.create_task(store.await_decision(second, WAIT_SECONDS)),
    ]
    await asyncio.sleep(0)
    store.fail_all()
    assert await asyncio.gather(*waiters) == ["denied", "denied"]
    assert store.open_ids() == ()


async def test_open_ids_lists_unresolved_requests() -> None:
    store = PendingPermissionStore()
    first = store.hold()
    second = store.hold()
    assert store.open_ids() == (first, second)
    assert store.answer(first, allowed=True) is True
    assert store.open_ids() == (second,)
