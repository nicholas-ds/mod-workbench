import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import context_recorder
from context_recorder import ContextRecorder


def make_root(tmp_path: Path, body: str) -> Path:
    status = tmp_path / "repo" / "status"
    status.mkdir(parents=True)
    (status / "a.toml").write_text(body, encoding="utf-8")
    (status / "b.toml").write_text('wmux_surface = "other"\n', encoding="utf-8")
    return tmp_path


def test_writes_percent_before_the_first_table(tmp_path: Path) -> None:
    root = make_root(tmp_path, 'wmux_surface = "s1"\n[extra]\nx = 1\n')
    assert ContextRecorder().record(root, "s1", 31.5) == 1
    text = (root / "repo/status/a.toml").read_text(encoding="utf-8")
    assert text.index("context_percent = 31.5") < text.index("[extra]")


def test_replaces_an_existing_value(tmp_path: Path) -> None:
    root = make_root(tmp_path, 'wmux_surface = "s1"\ncontext_percent = 10\n')
    ContextRecorder().record(root, "s1", 40)
    text = (root / "repo/status/a.toml").read_text(encoding="utf-8")
    assert text.count("context_percent") == 1 and "context_percent = 40" in text


def test_no_matching_surface_changes_nothing(tmp_path: Path) -> None:
    root = make_root(tmp_path, 'wmux_surface = "s1"\n')
    assert ContextRecorder().record(root, "missing", 5) == 0


def test_reads_percent_from_stdin_json() -> None:
    payload = {"context_window": {"used_percentage": 12.5}}
    assert context_recorder.read_percent(payload) == 12.5
    assert context_recorder.read_percent({"used_percentage": 7}) == 7
    assert context_recorder.read_percent({}) is None


def test_main_always_returns_zero(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert context_recorder.main() == 0


def test_clear_forgets_the_stale_context_percent(tmp_path: Path) -> None:
    from activity_hook import ActivityRecorder

    root = make_root(tmp_path, 'wmux_surface = "s1"\ncontext_percent = 92\nactivity = "working"\n')
    ActivityRecorder().forget_context(root, "s1")
    text = (root / "repo/status/a.toml").read_text(encoding="utf-8")
    assert "context_percent" not in text and 'activity = "working"' in text
    assert (root / "repo/status/b.toml").read_text(encoding="utf-8") == 'wmux_surface = "other"\n'
