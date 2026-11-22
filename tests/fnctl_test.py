import asyncio
import pathlib
import sys
import threading
import types

import pytest

import pytilpack.fnctl

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="pytilpack.fnctlはUnix専用のfcntlに依存するため")


def test_lock(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_file = tmp_path / "dir" / "test.lock"
    retried = threading.Event()
    released = threading.Event()
    entered = threading.Event()

    def retry(_delay: float) -> None:
        assert not retried.is_set()
        retried.set()
        assert released.wait(5)

    monkeypatch.setattr(pytilpack.fnctl, "time", types.SimpleNamespace(sleep=retry))

    def contender() -> None:
        with pytilpack.fnctl.lock(lock_file):
            entered.set()
        retried.set()

    thread = threading.Thread(target=contender, daemon=True)
    try:
        with pytilpack.fnctl.lock(lock_file):
            thread.start()
            assert retried.wait(5)
            assert not entered.is_set()
    finally:
        released.set()
        thread.join(5)
    assert not thread.is_alive()
    assert entered.is_set()


@pytest.mark.asyncio
async def test_alock(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_file = tmp_path / "dir" / "test.lock"
    retried = asyncio.Event()
    released = asyncio.Event()

    async def retry(_delay: float) -> None:
        assert not retried.is_set()
        retried.set()
        await released.wait()

    monkeypatch.setattr(pytilpack.fnctl, "asyncio", types.SimpleNamespace(sleep=retry))

    async def contender() -> None:
        async with pytilpack.fnctl.alock(lock_file):
            retried.set()

    async with asyncio.timeout(5), asyncio.TaskGroup() as group:
        async with pytilpack.fnctl.alock(lock_file):
            task = group.create_task(contender())
            await retried.wait()
            assert not task.done()
        released.set()
        await task
