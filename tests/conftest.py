import pytest


@pytest.fixture(autouse=True)
def isolate_from_app_chat_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """The app chat sets this variable. It makes the activity hook exit early, so tests must not inherit it."""
    monkeypatch.delenv("WORKBENCH_CHAT_SESSION", raising=False)
