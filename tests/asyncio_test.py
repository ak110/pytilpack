"""テストコード。"""

import asyncio
import queue
import threading
import time

import pytest

import pytilpack.asyncio_


async def async_func():
    await asyncio.sleep(0.0)
    return "Done"


def test_run():
    for _ in range(3):
        assert pytilpack.asyncio_.run(async_func()) == "Done"

    assert tuple(
        pytilpack.asyncio_.run(asyncio.gather(async_func(), async_func(), async_func()))
    ) == ("Done", "Done", "Done")


class CountingJob(pytilpack.asyncio_.Job):
    """実行回数をカウントするジョブ。"""

    def __init__(self) -> None:
        self.count = 0

    async def run(self) -> None:
        await asyncio.sleep(0.1)
        self.count += 1


class ErrorJob(pytilpack.asyncio_.Job):
    """エラーを発生させるジョブ。"""

    async def run(self) -> None:
        raise ValueError("Test error")


class TestJobRunner(pytilpack.asyncio_.JobRunner):
    """テスト用のJobRunner。"""

    def __init__(self, poll_interval: float = 0.1, **kwargs) -> None:
        # テスト高速化のためpoll_intervalは短くする
        super().__init__(poll_interval=poll_interval, **kwargs)
        self.queue = queue.Queue[pytilpack.asyncio_.Job]()

    async def poll(self) -> pytilpack.asyncio_.Job | None:
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None


def add_jobs_thread(
    queue_: queue.Queue[pytilpack.asyncio_.Job], jobs: list[pytilpack.asyncio_.Job]
) -> None:
    """別スレッドでジョブを追加する。"""
    for job in jobs:
        time.sleep(0.1)
        queue_.put(job)


@pytest.mark.asyncio
async def test_job_runner() -> None:
    """基本機能のテスト。"""
    runner = TestJobRunner()

    # 別スレッドでジョブを追加
    jobs = [CountingJob() for _ in range(3)]
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()

    # JobRunnerを実行（1秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(1.0)
        runner.shutdown()

    await asyncio.gather(runner.run(), shutdown_after())

    thread.join()
    # 各ジョブの実行回数を確認
    for job in jobs:
        assert job.count == 1


@pytest.mark.asyncio
async def test_job_runner_error() -> None:
    """エラーハンドリングのテスト。"""
    runner = TestJobRunner()

    # 正常なジョブとエラーを発生させるジョブを混ぜて追加
    jobs = [CountingJob(), ErrorJob(), CountingJob()]
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()

    # JobRunnerを実行（1秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(1.0)
        runner.shutdown()

    await asyncio.gather(runner.run(), shutdown_after())

    thread.join()
    # エラーが発生しても他のジョブは実行されることを確認
    assert isinstance(jobs[0], CountingJob) and jobs[0].count == 1
    assert isinstance(jobs[2], CountingJob) and jobs[2].count == 1


@pytest.mark.asyncio
async def test_job_runner_shutdown() -> None:
    """シャットダウン機能のテスト。"""
    runner = TestJobRunner()

    async def shutdown_after_and_add_job() -> CountingJob:
        runner.shutdown()
        # シャットダウン後に少し待ってからジョブを追加
        time.sleep(0.5)
        job = CountingJob()
        runner.queue.put(job)
        return job

    # シャットダウン後に追加されたジョブは実行されないことを確認
    _, job = await asyncio.gather(runner.run(), shutdown_after_and_add_job())
    assert job.count == 0  # ジョブは実行されていない
