import asyncio
import pathlib
import sys
import threading
import time

import pytest

import pytilpack.fnctl

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="pytilpack.fnctlはUnix専用のfcntlに依存するため")


def _assert_lock_order(results: list[str]) -> None:
    assert len(results) == 4
    assert results[0].startswith("start_")
    assert results[1].startswith("end_")
    assert results[2].startswith("start_")
    assert results[3].startswith("end_")

    worker_1_start = results[0] == "start_1"
    if worker_1_start:
        assert results[1] == "end_1"
        assert results[2] == "start_2"
        assert results[3] == "end_2"
    else:
        assert results[0] == "start_2"
        assert results[1] == "end_2"
        assert results[2] == "start_1"
        assert results[3] == "end_1"


def test_lock(tmp_path: pathlib.Path) -> None:
    lock_file = tmp_path / "dir" / "test.lock"
    results = []

    def worker(worker_id: int) -> None:
        with pytilpack.fnctl.lock(lock_file):
            results.append(f"start_{worker_id}")
            time.sleep(0.1)
            results.append(f"end_{worker_id}")

    thread1 = threading.Thread(target=worker, args=(1,))
    thread2 = threading.Thread(target=worker, args=(2,))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    _assert_lock_order(results)


@pytest.mark.asyncio
async def test_alock(tmp_path: pathlib.Path) -> None:
    lock_file = tmp_path / "dir" / "test_async.lock"
    results = []

    async def async_worker(worker_id: int) -> None:
        async with pytilpack.fnctl.alock(lock_file):
            results.append(f"start_{worker_id}")
            await asyncio.sleep(0.1)
            results.append(f"end_{worker_id}")

    await asyncio.gather(
        async_worker(1),
        async_worker(2),
    )

    _assert_lock_order(results)
