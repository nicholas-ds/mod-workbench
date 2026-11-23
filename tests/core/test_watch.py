import asyncio
from pathlib import Path

from workbench.core.watch import FileChangeWatcher


async def test_yields_path_when_file_created(tmp_path: Path) -> None:
    watcher = FileChangeWatcher()
    iterator = watcher.changes([tmp_path]).__aiter__()

    async def create_file() -> None:
        await asyncio.sleep(0.5)
        (tmp_path / "new.md").write_text("content", encoding="utf-8")

    creator = asyncio.create_task(create_file())
    try:
        changed = await asyncio.wait_for(anext(iterator), timeout=5.0)
    finally:
        await creator
    await iterator.aclose()

    assert isinstance(changed, frozenset)
    assert tmp_path / "new.md" in changed
