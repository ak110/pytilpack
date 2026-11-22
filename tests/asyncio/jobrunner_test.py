import asyncio
import queue
import threading
import time
import typing

import pytest

import pytilpack.asyncio


class CountingJob(pytilpack.asyncio.Job):
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
    @typing.override
    async def run(self) -> None:
        raise ValueError("Test error")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"


class JobRunner(pytilpack.asyncio.JobRunner):
    def __init__(self, max_job_concurrency: int = 8, poll_interval: float = 0.1, **kwargs) -> None:
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
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.finish = asyncio.Event()

    @typing.override
    async def run(self) -> None:
        self.started.set()
        await self.finish.wait()


class PollingJobRunner(pytilpack.asyncio.JobRunner):
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


@pytest.mark.parametrize("outcome", ["finished", "errored", "canceled"])
@pytest.mark.asyncio
async def test_job_state_owned_by_runner(outcome: pytilpack.asyncio.JobStatus, caplog: pytest.LogCaptureFixture) -> None:

    observed: list[tuple[str, pytilpack.asyncio.JobStatus]] = []

    class NotifyingJob(EventJob):
        @typing.override
        async def run(self) -> None:
            observed.append(("run", self.status))
            await super().run()
            if outcome == "errored":
                raise ValueError("job failed")

        def _record_notification(self, name: str) -> None:
            observed.append((name, self.status))
            raise ValueError("notification failed")

        @typing.override
        async def on_finished(self) -> None:
            self._record_notification("finished")

        @typing.override
        async def on_errored(self) -> None:
            self._record_notification("errored")

        @typing.override
        async def on_canceled(self) -> None:
            self._record_notification("canceled")

        @typing.override
        async def on_finally(self) -> None:
            observed.append(("finally", self.status))

    job = NotifyingJob()
    pending = EventJob()
    runner = PollingJobRunner(job)
    assert job.status == "waiting" and runner.running
    task = asyncio.create_task(runner.run())
    try:
        async with asyncio.timeout(2):
            await job.started.wait()
            await runner.poll_started.wait()
            if outcome == "canceled":
                runner.shutdown()
            else:
                job.finish.set()
            await runner.graceful_shutdown()
            runner.result.set_result(pending)
            await task
        assert observed == [("run", "running"), (outcome, outcome), ("finally", outcome)]
        assert job.status == outcome
        assert pending.status == "waiting" and not pending.started.is_set()
        assert not runner.running and not runner.tasks
        assert "notification failed" in caplog.text
    finally:
        job.finish.set()
        task.cancel()
        await asyncio.gather(task, *runner.tasks, return_exceptions=True)


async def _shutdown(runner: PollingJobRunner) -> None:
    runner.shutdown()


async def _graceful_shutdown(runner: PollingJobRunner) -> None:
    await runner.graceful_shutdown()


@pytest.mark.asyncio
async def test_cancel_while_polling_releases_capacity() -> None:
    runner = PollingJobRunner()
    task = asyncio.create_task(runner.run())
    try:
        await runner.poll_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with asyncio.timeout(1):
            await runner.semaphore.acquire()
            await runner.semaphore.acquire()
        assert runner.semaphore.locked()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def add_jobs_thread(
    queue_: queue.Queue[pytilpack.asyncio.Job],
    jobs: list[pytilpack.asyncio.Job],
    sleep_time: float | None = 0.1,
) -> None:
    for job in jobs:
        if sleep_time is not None:
            time.sleep(sleep_time)
        queue_.put(job)


@pytest.mark.asyncio
async def test_job_runner() -> None:
    runner = JobRunner()

    jobs = [CountingJob() for _ in range(3)]
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    async def shutdown_after() -> None:
        await asyncio.sleep(0.75)
        runner.shutdown()

    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()

    thread.join()
    assert all(job.status == "finished" and job.count == 1 for job in jobs)


@pytest.mark.asyncio
async def test_job_runner_cancel() -> None:
    runner = JobRunner()

    jobs = (
        CountingJob(),
        CountingJob(sleep_time=3.0),
    )
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    async def shutdown_after() -> None:
        await asyncio.sleep(1.0)
        runner.shutdown()

    start_time = time.perf_counter()
    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()
    elapsed_time = time.perf_counter() - start_time
    assert 0.75 <= elapsed_time < 1.25

    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[1].status == "canceled" and jobs[1].count == 0


@pytest.mark.asyncio
async def test_job_runner_errors() -> None:
    runner = JobRunner()

    jobs = (
        CountingJob(),
        ErrorJob(),
        CountingJob(),
        CountingJob(sleep_time=3.0),
    )
    thread = threading.Thread(target=add_jobs_thread, args=(runner.queue, jobs))
    thread.start()
    time.sleep(0.0)

    async def shutdown_after_and_add_job() -> CountingJob:
        await asyncio.sleep(0.75)
        runner.shutdown()
        await asyncio.sleep(0.25)
        post_job = CountingJob()
        runner.queue.put(post_job)
        return post_job

    _, post_job = await asyncio.gather(runner.run(), shutdown_after_and_add_job())
    thread.join()

    assert jobs[0].status == "finished" and jobs[0].count == 1
    assert jobs[1].status == "errored"
    assert jobs[2].status == "finished" and jobs[2].count == 1
    assert jobs[3].status == "canceled" and jobs[3].count == 0
    assert post_job.status == "waiting" and post_job.count == 0


@pytest.mark.asyncio
async def test_job_runner_graceful_shutdown() -> None:
    runner = JobRunner(max_job_concurrency=2)

    jobs = (
        CountingJob(sleep_time=0.5),
        CountingJob(sleep_time=0.5),
        CountingJob(sleep_time=0.5),
    )
    for job in jobs:
        runner.queue.put(job)

    async def graceful_shutdown_after() -> None:
        await asyncio.sleep(0.3)
        await runner.graceful_shutdown()

    start_time = time.perf_counter()
    await asyncio.gather(runner.run(), graceful_shutdown_after())
    elapsed_time = time.perf_counter() - start_time
    assert 0.5 <= elapsed_time < 0.9

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


@pytest.mark.asyncio
async def test_shutdown_cancels_job_again() -> None:
    first_cancel = asyncio.Event()

    class RetryingJob(EventJob):
        @typing.override
        async def run(self) -> None:
            try:
                await super().run()
            except asyncio.CancelledError:
                first_cancel.set()
                await self.finish.wait()

    job = RetryingJob()
    runner = PollingJobRunner(job)
    task = asyncio.create_task(runner.run())
    try:
        async with asyncio.timeout(2):
            await job.started.wait()
            await runner.poll_started.wait()
            runner.shutdown()
            await first_cancel.wait()
            assert job.status == "running"
            runner.shutdown()
            await runner.graceful_shutdown()
            runner.result.set_result(None)
            await task
        assert str(job.status) == "canceled"
        assert not runner.running and not runner.tasks
    finally:
        job.finish.set()
        task.cancel()
        await asyncio.gather(task, *runner.tasks, return_exceptions=True)
