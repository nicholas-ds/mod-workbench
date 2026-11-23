"""Tests for worker_scanner: port parsing, mapping to repos, active vs stalled, caching."""

from __future__ import annotations

from workbench.agents.worker_scanner import (
    BusySession,
    BusyWorkerCounter,
    OpencodePortFinder,
    OpencodeSessionClient,
    WorkerCounts,
)

TASKLIST_TEXT = (
    '\r\n'
    '"opencode.exe","23504","Console","1","45,012 K"\r\n'
    '"opencode.exe","77","Console","1","12 K"\r\n'
    '"explorer.exe","4100","Console","1","90,000 K"\r\n'
)

NETSTAT_TEXT = (
    '\r\n'
    'Active Connections\r\n'
    '\r\n'
    '  Proto  Local Address          Foreign Address        State           PID\r\n'
    '  TCP    127.0.0.1:4096         0.0.0.0:0              LISTENING       23504\r\n'
    '  TCP    127.0.0.1:5050         0.0.0.0:0              LISTENING       4100\r\n'
    '  TCP    [::]:4096              [::]:0                 LISTENING       23504\r\n'
    '  TCP    127.0.0.1:4096         1.2.3.4:5555           ESTABLISHED     23504\r\n'
    '  UDP    127.0.0.1:1900         *:*                                    4100\r\n'
)

NOW_MS = 1_000_000_000_000
ACTIVE_MS = 180 * 1000


class FakeClock:
    """A monotonic clock that only advances when told to."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _session(directory: str, age_ms: int = 0) -> BusySession:
    return BusySession(directory=directory, updated_ms=NOW_MS - age_ms)


def test_port_finder_keeps_listening_ports_of_worker_pids() -> None:
    finder = OpencodePortFinder()
    assert finder._worker_pids(TASKLIST_TEXT) == {23504, 77}
    assert finder._listening_ports(NETSTAT_TEXT) == [(4096, 23504), (5050, 4100),
                                                     (4096, 23504)]


def test_client_returns_empty_when_server_is_down() -> None:
    sessions = OpencodeSessionClient().busy_sessions(1)
    assert sessions == []


def test_client_skips_session_with_missing_or_bad_update_time() -> None:
    client = FakeHttpClient(pages={
        "http://127.0.0.1:4096/session/status": {"s1": {"type": "busy"},
                                                 "s2": {"type": "busy"},
                                                 "s3": {"type": "busy"}},
        "http://127.0.0.1:4096/session": [
            {"id": "s1", "directory": "E:\\repos\\mods\\CityBuilder",
             "time": {"updated": NOW_MS}},
            {"id": "s2", "directory": "E:\\repos\\mods\\CityBuilder", "time": {}},
            {"id": "s3", "directory": "E:\\repos\\mods\\CityBuilder",
             "time": {"updated": "soon"}},
        ],
    })
    sessions = client.busy_sessions(4096)
    assert sessions == [BusySession(directory="E:\\repos\\mods\\CityBuilder",
                                    updated_ms=NOW_MS)]


def test_counter_counts_recent_busy_session_as_active() -> None:
    counter = BusyWorkerCounter(FakePortFinder(), FakeSessionClient([
        _session("E:\\repos\\mods\\CityBuilder\\src"),
        _session("E:\\repos\\mods\\CityBuilder\\src", age_ms=ACTIVE_MS),
    ]), now_ms=lambda: NOW_MS)
    counts = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    assert counts == {"E:\\repos\\mods\\CityBuilder": WorkerCounts(active=2, stalled=0)}


def test_counter_counts_old_busy_session_as_stalled() -> None:
    counter = BusyWorkerCounter(FakePortFinder(), FakeSessionClient([
        _session("E:\\repos\\mods\\CityBuilder", age_ms=ACTIVE_MS + 1),
        _session("E:\\repos\\mods\\CityBuilder", age_ms=57 * 60 * 1000),
    ]), now_ms=lambda: NOW_MS)
    counts = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    assert counts == {"E:\\repos\\mods\\CityBuilder": WorkerCounts(active=0, stalled=2)}


def test_counter_splits_active_and_stalled_per_repo() -> None:
    counter = BusyWorkerCounter(FakePortFinder(), FakeSessionClient([
        _session("E:\\repos\\mods\\CityBuilder"),
        _session("E:\\repos\\mods\\CityBuilder\\deep", age_ms=ACTIVE_MS + 1),
    ]), now_ms=lambda: NOW_MS)
    counts = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    assert counts == {"E:\\repos\\mods\\CityBuilder": WorkerCounts(active=1, stalled=1)}


def test_counter_counts_unrelated_directory_for_no_repo() -> None:
    counter = BusyWorkerCounter(FakePortFinder(), FakeSessionClient([
        _session("E:\\somewhere\\else"),
        _session("E:\\repos\\mods\\CityBuilder\\src"),
    ]), now_ms=lambda: NOW_MS)
    counts = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    assert counts == {"E:\\repos\\mods\\CityBuilder": WorkerCounts(active=1, stalled=0)}


def test_counter_match_is_case_insensitive_with_mixed_slashes() -> None:
    counter = BusyWorkerCounter(FakePortFinder(), FakeSessionClient([
        _session("e:/repos/mods/starfieldmodresearch/sub"),
    ]), now_ms=lambda: NOW_MS)
    counts = counter.count_by_repo(["E:\\repos\\Mods\\StarfieldModResearch"])
    assert counts == {"E:\\repos\\Mods\\StarfieldModResearch": WorkerCounts(active=1, stalled=0)}


def test_counter_caches_until_ttl_expires() -> None:
    clock = FakeClock()
    session_client = FakeSessionClient([])
    counter = BusyWorkerCounter(FakePortFinder(), session_client, ttl_seconds=5.0,
                                clock=clock, now_ms=lambda: NOW_MS)
    counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    session_client.sessions = [_session("E:\\repos\\mods\\CityBuilder\\new")]
    stale = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    clock.advance(5.0)
    fresh = counter.count_by_repo(["E:\\repos\\mods\\CityBuilder"])
    assert stale == {"E:\\repos\\mods\\CityBuilder": WorkerCounts()}
    assert fresh == {"E:\\repos\\mods\\CityBuilder": WorkerCounts(active=1, stalled=0)}


class FakePortFinder:
    """Always reports one fixed port."""

    def find(self) -> list[int]:
        return [4096]


class FakeSessionClient:
    """Returns a fixed list of busy sessions."""

    def __init__(self, sessions: list[BusySession]) -> None:
        self.sessions = sessions

    def busy_sessions(self, port: int) -> list[BusySession]:
        return self.sessions


class FakeHttpClient(OpencodeSessionClient):
    """Serves canned JSON pages instead of HTTP."""

    def __init__(self, pages: dict[str, object]) -> None:
        self.pages = pages

    def _get_json(self, url: str) -> object:
        return self.pages[url]
