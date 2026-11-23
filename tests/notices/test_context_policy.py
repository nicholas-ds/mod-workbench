"""Tests for ContextPolicy route selection."""

from workbench.notices.context_policy import ContextPolicy
from workbench.notices.notice_types import Route


def test_none_percent_gives_send() -> None:
    assert ContextPolicy().route(None) is Route.SEND


def test_percent_below_threshold_gives_send() -> None:
    assert ContextPolicy().route(10.0) is Route.SEND


def test_percent_equal_to_threshold_gives_send() -> None:
    assert ContextPolicy().route(25.0) is Route.SEND


def test_percent_above_threshold_gives_fresh() -> None:
    assert ContextPolicy().route(25.1) is Route.FRESH


def test_custom_threshold_moves_the_boundary() -> None:
    policy = ContextPolicy(threshold_percent=50.0)
    assert policy.route(50.0) is Route.SEND
    assert policy.route(50.1) is Route.FRESH
