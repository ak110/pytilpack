"""現在のタスク識別と公開名の検証。"""

import asyncio

import pytest

import pytilpack.asyncio


@pytest.mark.asyncio
async def test_current_task_identity() -> None:
    task = asyncio.current_task()
    assert task is not None
    assert pytilpack.asyncio.get_task_id() == id(task)
    assert pytilpack.asyncio.get_task_id_hex() == f"{id(task):x}"


@pytest.mark.asyncio
async def test_no_current_task_in_callback() -> None:
    loop = asyncio.get_running_loop()
    result: asyncio.Future[tuple[int | None, str]] = loop.create_future()

    def callback() -> None:
        result.set_result((pytilpack.asyncio.get_task_id(), pytilpack.asyncio.get_task_id_hex()))

    loop.call_soon(callback)
    assert await result == (None, "None")


def test_public_names() -> None:
    assert pytilpack.asyncio.ThreadPool is not None
    for name in ("abc", "asyncio", "shutil", "functools", "pytilpack", "logger", "WorkerThread"):
        assert not hasattr(pytilpack.asyncio, name), name
