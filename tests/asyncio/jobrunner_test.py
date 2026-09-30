"""テストコード。"""

import asyncio
import queue
import threading
import time
import typing

import pytest

import pytilpack.asyncio


class CountingJob(pytilpack.asyncio.Job):
    """実行回数をカウントするジョブ。"""

    def __init__(self, sleep_time: float = 0.1) -> None:
        super().__init__()
        self.count = 0
        self.sleep_time = sleep_time

    @typing.override
    async def run(self) -> None:
        await asyncio.sleep(self.sleep_time)
        self.count += 1

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"


class ErrorJob(pytilpack.asyncio.Job):
    """エラーを発生させるジョブ。"""

    @typing.override
    async def run(self) -> None:
        raise ValueError("Test error")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"


class JobRunner(pytilpack.asyncio.JobRunner):
    """テスト用のJobRunner。"""

    def __init__(self, max_job_concurrency: int = 8, poll_interval: float = 0.1, **kwargs) -> None:
        # テスト高速化のためpoll_intervalのデフォルトは短くする
        super().__init__(
            max_job_concurrency=max_job_concurrency,
            poll_interval=poll_interval,
            **kwargs,
        )
        self.queue = queue.Queue[pytilpack.asyncio.Job]()

    @typing.override
    async def poll(self) -> pytilpack.asyncio.Job | None:
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"


class EventJob(pytilpack.asyncio.Job):
    """開始と終了をイベントで制御するジョブ。"""

    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.finish = asyncio.Event()

    @typing.override
    async def run(self) -> None:
        self.started.set()
        await self.finish.wait()


class PollingJobRunner(pytilpack.asyncio.JobRunner):
    """取得待機の開始と返却を制御するランナー。"""

    def __init__(self, first_job: EventJob | None = None) -> None:
        super().__init__(max_job_concurrency=2, poll_interval=0)
        self.first_job = first_job
        self.poll_started = asyncio.Event()
        self.result: asyncio.Future[pytilpack.asyncio.Job | None] = asyncio.get_running_loop().create_future()

    @typing.override
    async def poll(self) -> pytilpack.asyncio.Job | None:
        if self.first_job is not None:
            job = self.first_job
            self.first_job = None
            return job
        self.poll_started.set()
        return await self.result


async def _shutdown(runner: PollingJobRunner) -> None:
    runner.shutdown()


async def _graceful_shutdown(runner: PollingJobRunner) -> None:
    await runner.graceful_shutdown()


def add_jobs_thread(
    queue_: queue.Queue[pytilpack.asyncio.Job],
    jobs: list[pytilpack.asyncio.Job],
    sleep_time: float | None = 0.1,
) -> None:
    """別スレッドでジョブを追加する。"""
    for job in jobs:
        if sleep_time is not None:
            time.sleep(sleep_time)
        queue_.put(job)


@pytest.mark.asyncio
async def test_job_runner() -> None:
    """基本機能のテスト。"""
    runner = JobRunner()

    # 別スレッドでジョブを追加
    jobs = [CountingJob() for _ in range(3)]
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    # JobRunnerを実行（0.75秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(0.75)
        runner.shutdown()

    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()

    thread.join()
    # 各ジョブの実行回数を確認
    assert all(job.status == "finished" and job.count == 1 for job in jobs)


@pytest.mark.asyncio
async def test_job_runner_cancel() -> None:
    """キャンセルのテスト。"""
    runner = JobRunner()

    # 時間がかからないジョブとエラーになるジョブと時間のかかるジョブ
    jobs = (
        CountingJob(),  # 期待: count == 1
        CountingJob(sleep_time=3.0),  # shutdownにより処理されず count == 0
    )
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    # JobRunnerを実行（1.0秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(1.0)
        runner.shutdown()

    start_time = time.perf_counter()
    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()
    elapsed_time = time.perf_counter() - start_time
    assert 0.75 <= elapsed_time < 1.25

    # 各ジョブの実行結果を確認
    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[1].status == "canceled" and jobs[1].count == 0


@pytest.mark.asyncio
async def test_job_runner_errors() -> None:
    """異常系のテスト。"""
    runner = JobRunner()

    # 時間がかからないジョブとエラーになるジョブと時間のかかるジョブ
    jobs = (
        CountingJob(),  # 期待: count == 1
        ErrorJob(),  # エラー発生するがrunnerは継続
        CountingJob(),  # 期待: count == 1
        CountingJob(sleep_time=3.0),  # shutdownにより処理されず count == 0
    )
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    # JobRunnerを実行（0.75秒後にシャットダウン）
    async def shutdown_after_and_add_job() -> CountingJob:
        # 早めにshutdownを実施
        await asyncio.sleep(0.75)
        runner.shutdown()
        # シャットダウン後に少し待ってからジョブを追加
        await asyncio.sleep(0.25)
        post_job = CountingJob()
        runner.queue.put(post_job)
        return post_job

    _, post_job = await asyncio.gather(runner.run(), shutdown_after_and_add_job())
    thread.join()

    # 各ジョブの実行結果を確認
    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[1].status == "errored"
    assert jobs[2].status == "finished" and jobs[2].count == 1
    assert jobs[3].status == "canceled" and jobs[3].count == 0
    assert post_job.status == "waiting" and post_job.count == 0


@pytest.mark.asyncio
async def test_job_runner_graceful_shutdown() -> None:
    """graceful_shutdownのテスト。"""
    # 同時実行数2のJobRunnerを作成
    runner = JobRunner(max_job_concurrency=2)

    # 3つのジョブを用意
    jobs = (
        CountingJob(sleep_time=0.5),  # 期待: count == 1
        CountingJob(sleep_time=0.5),  # 期待: count == 1
        CountingJob(sleep_time=0.5),  # 実行待ちになる
    )
    for job in jobs:
        runner.queue.put(job)

    # JobRunnerを実行（0.3秒後にgraceful_shutdown）
    async def graceful_shutdown_after() -> None:
        await asyncio.sleep(0.3)
        await runner.graceful_shutdown()

    # 処理実行
    start_time = time.perf_counter()
    await asyncio.gather(runner.run(), graceful_shutdown_after())
    elapsed_time = time.perf_counter() - start_time
    assert 0.5 <= elapsed_time < 0.9

    # 各ジョブの実行結果を確認
    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[1].status == "finished" and jobs[1].count == 1
    assert jobs[2].status == "waiting" and jobs[2].count == 0


@pytest.mark.parametrize("stop", [_shutdown, _graceful_shutdown], ids=["immediate", "graceful"])
@pytest.mark.parametrize("return_job", [False, True], ids=["none", "job"])
@pytest.mark.asyncio
async def test_stop_while_polling(stop: typing.Callable[[PollingJobRunner], typing.Awaitable[None]], return_job: bool) -> None:
    runner = PollingJobRunner()
    job = EventJob()
    task = asyncio.create_task(runner.run())
    try:
        await runner.poll_started.wait()
        await stop(runner)
        runner.result.set_result(job if return_job else None)
        await task
        assert not runner.tasks
        assert not job.started.is_set()
        assert job.status == "waiting"
        # 全枠を再取得できれば、停止分岐での返却漏れと二重返却を検出できる。
        async with asyncio.timeout(1):
            await runner.semaphore.acquire()
            await runner.semaphore.acquire()
        assert runner.semaphore.locked()
    finally:
        job.finish.set()
        runner.shutdown()
        await asyncio.gather(task, *runner.tasks, return_exceptions=True)


@pytest.mark.parametrize("stop", [_shutdown, _graceful_shutdown], ids=["immediate", "graceful"])
@pytest.mark.asyncio
async def test_stop_after_poll_error(stop: typing.Callable[[PollingJobRunner], typing.Awaitable[None]]) -> None:
    runner = PollingJobRunner()
    task = asyncio.create_task(runner.run())
    await runner.poll_started.wait()
    await stop(runner)
    runner.result.set_exception(ValueError("poll failed"))
    await task
    assert not runner.tasks
    async with asyncio.timeout(1):
        await runner.semaphore.acquire()
        await runner.semaphore.acquire()
    assert runner.semaphore.locked()


@pytest.mark.asyncio
async def test_graceful_shutdown_while_polling_with_running_job() -> None:
    active = EventJob()
    pending = EventJob()
    runner = PollingJobRunner(active)
    task = asyncio.create_task(runner.run())
    await active.started.wait()
    await runner.poll_started.wait()
    stop = asyncio.create_task(runner.graceful_shutdown())
    # coroutine開始を確定し、既存ジョブの完了までは停止処理が戻らないことを確認する。
    await asyncio.sleep(0)
    assert not stop.done()
    runner.result.set_result(pending)
    await task
    active.finish.set()
    pending.finish.set()
    await stop
    assert active.status == "finished"
    assert not pending.started.is_set()
    assert pending.status == "waiting"


@pytest.mark.asyncio
async def test_shutdown_while_polling_with_running_job() -> None:
    active = EventJob()
    pending = EventJob()
    runner = PollingJobRunner(active)
    task = asyncio.create_task(runner.run())
    await active.started.wait()
    await runner.poll_started.wait()
    runner.shutdown()
    runner.result.set_result(pending)
    await task
    pending.finish.set()
    await asyncio.gather(*runner.tasks, return_exceptions=True)
    assert active.status == "canceled"
    assert not pending.started.is_set()
    assert pending.status == "waiting"
