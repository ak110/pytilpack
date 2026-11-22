import asyncio
import queue
import typing

import pytest
import pytest_asyncio

import pytilpack.asyncio


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


class ObservedJob(EventJob):
    def __init__(self, *, fail: bool = False) -> None:
        super().__init__()
        self.fail = fail
        self.done = asyncio.Event()
        self.count = 0

    @typing.override
    async def run(self) -> None:
        self.count += 1
        await super().run()
        if self.fail:
            raise ValueError("Test error")

    @typing.override
    async def on_finally(self) -> None:
        self.done.set()


@pytest_asyncio.fixture(name="running_jobs")
async def _running_jobs():
    tasks: list[tuple[JobRunner, asyncio.Task[None]]] = []

    def start(concurrency: int = 8) -> JobRunner:
        runner = JobRunner(max_job_concurrency=concurrency, poll_interval=0)
        task = asyncio.create_task(runner.run())
        tasks.append((runner, task))
        return runner

    yield start

    for runner, task in tasks:
        active = tuple(runner.tasks)
        runner.shutdown()
        task.cancel()
        async with asyncio.timeout(5):
            await asyncio.gather(task, *active, return_exceptions=True)


@pytest.mark.asyncio
async def test_job_runner(running_jobs) -> None:
    runner = running_jobs()
    jobs = [ObservedJob() for _ in range(3)]

    def submit() -> None:
        for job in jobs:
            runner.queue.put(job)

    async with asyncio.timeout(5):
        await asyncio.to_thread(submit)
        for job in jobs:
            job.finish.set()
        await asyncio.gather(*(job.done.wait() for job in jobs))
    assert [(job.status, job.count) for job in jobs] == [("finished", 1)] * 3


@pytest.mark.asyncio
async def test_job_runner_cancel(running_jobs) -> None:
    runner = running_jobs()
    finished, active = ObservedJob(), ObservedJob()
    runner.queue.put(finished)
    runner.queue.put(active)
    finished.finish.set()

    async with asyncio.timeout(5):
        await finished.done.wait()
        await active.started.wait()
        runner.shutdown()
        await active.done.wait()
    assert (finished.status, finished.count) == ("finished", 1)
    assert (active.status, active.count) == ("canceled", 1)


@pytest.mark.asyncio
async def test_job_runner_errors(running_jobs) -> None:
    runner = running_jobs(1)
    failed, following, active, pending = ObservedJob(fail=True), ObservedJob(), ObservedJob(), ObservedJob()
    runner.queue.put(failed)
    runner.queue.put(following)
    runner.queue.put(active)
    failed.finish.set()
    following.finish.set()

    async with asyncio.timeout(5):
        await following.done.wait()
        await active.started.wait()
        runner.shutdown()
        runner.queue.put(pending)
        await active.done.wait()
    assert (failed.status, failed.count) == ("errored", 1)
    assert (following.status, following.count) == ("finished", 1)
    assert (active.status, active.count) == ("canceled", 1)
    assert (pending.status, pending.count) == ("waiting", 0)
    assert runner.queue.get_nowait() is pending


@pytest.mark.asyncio
async def test_job_runner_graceful_shutdown(running_jobs) -> None:
    runner = running_jobs(2)
    first, second, pending = ObservedJob(), ObservedJob(), ObservedJob()
    for job in (first, second, pending):
        runner.queue.put(job)

    async with asyncio.timeout(5):
        await first.started.wait()
        await second.started.wait()
        assert not pending.started.is_set()

        shutdown = asyncio.create_task(runner.graceful_shutdown())
        try:
            while runner.running:
                await asyncio.sleep(0)
            assert not shutdown.done()
            first.finish.set()
            second.finish.set()
            await shutdown
        finally:
            shutdown.cancel()
            await asyncio.gather(shutdown, return_exceptions=True)

    assert [(job.status, job.count) for job in (first, second, pending)] == [
        ("finished", 1),
        ("finished", 1),
        ("waiting", 0),
    ]
    assert runner.queue.get_nowait() is pending


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
