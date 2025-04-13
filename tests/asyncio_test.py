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

    def __init__(self, sleep_time: float = 0.1) -> None:
        super().__init__()
        self.count = 0
        self.sleep_time = sleep_time

    async def run(self) -> None:
        await asyncio.sleep(self.sleep_time)
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
        await asyncio.sleep(0.5)
        runner.shutdown()

    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()

    thread.join()
    # 各ジョブの実行回数を確認
    assert all(job.status == "finished" and job.count == 1 for job in jobs)


@pytest.mark.asyncio
async def test_job_runner_errors() -> None:
    """異常系のテスト。"""
    runner = TestJobRunner()

    # 時間がかからないジョブとエラーになるジョブと時間のかかるジョブ
    jobs = (
        CountingJob(),  # 期待: count == 1
        ErrorJob(),  # エラー発生するがrunnerは継続
        CountingJob(),  # 期待: count == 1
        CountingJob(sleep_time=3.0),  # shutdownにより処理されず count == 0
    )
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()

    # JobRunnerを実行（0.5秒後にシャットダウン）
    async def shutdown_after_and_add_job() -> CountingJob:
        # 早めにshutdownを実施
        await asyncio.sleep(0.5)
        runner.shutdown()
        # シャットダウン後に少し待ってからジョブを追加
        await asyncio.sleep(0.5)
        post_job = CountingJob()
        runner.queue.put(post_job)
        return post_job

    _, post_job = await asyncio.gather(runner.run(), shutdown_after_and_add_job())
    thread.join()

    # 時間がかからないジョブは実行されていることを確認
    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[2].status == "finished" and jobs[2].count == 1
    # エラーになるジョブはエラーが発生していることを確認
    assert jobs[1].status == "errored"
    # 時間がかかるジョブは途中でshutdownされて実行されていないことを確認
    assert jobs[3].status == "canceled" and jobs[3].count == 0
    # シャットダウン後に追加されたジョブは実行されないことを確認
    assert post_job.count == 0
