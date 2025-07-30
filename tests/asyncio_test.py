"""テストコード。"""

import asyncio
import pathlib
import queue
import threading
import time
import typing

import pytest

import pytilpack.asyncio


@pytest.mark.asyncio
async def test_file_operations(tmp_path: pathlib.Path) -> None:
    """ファイル操作のテスト。"""
    # テストファイルのパス
    text_file = tmp_path / "test.txt"
    bytes_file = tmp_path / "test.bin"

    # テストデータ
    test_text = "Hello, World!\n日本語テスト"
    test_bytes = b"Hello, World!\x00\x01\x02"

    # write_text のテスト
    await pytilpack.asyncio.write_text(text_file, test_text)
    assert text_file.exists()

    # read_text のテスト
    result_text = await pytilpack.asyncio.read_text(text_file)
    assert result_text == test_text

    # write_bytes のテスト
    await pytilpack.asyncio.write_bytes(bytes_file, test_bytes)
    assert bytes_file.exists()

    # read_bytes のテスト
    result_bytes = await pytilpack.asyncio.read_bytes(bytes_file)
    assert result_bytes == test_bytes


@pytest.mark.asyncio
async def test_json_operations(tmp_path: pathlib.Path) -> None:
    """JSON操作のテスト。"""
    json_file = tmp_path / "test.json"

    # テストデータ
    test_data = {"name": "テスト", "value": 42, "list": [1, 2, 3], "nested": {"key": "value"}}

    # write_json のテスト
    await pytilpack.asyncio.write_json(json_file, test_data)
    assert json_file.exists()

    # read_json のテスト
    result = await pytilpack.asyncio.read_json(json_file)
    assert result == test_data

    # 存在しないファイルの読み込み（空のdictを返す）
    nonexistent_file = tmp_path / "nonexistent.json"
    result = await pytilpack.asyncio.read_json(nonexistent_file)
    assert result == {}


@pytest.mark.asyncio
async def test_json_operations_with_options(tmp_path: pathlib.Path) -> None:
    """JSONオプションのテスト。"""
    json_file = tmp_path / "test_options.json"

    test_data = {"z": 1, "a": 2, "japanese": "日本語"}

    # sort_keys=Trueでの書き込み
    await pytilpack.asyncio.write_json(json_file, test_data, sort_keys=True, indent=2)

    # ファイル内容を確認
    content = await pytilpack.asyncio.read_text(json_file)
    lines = content.strip().split("\n")
    assert '"a": 2' in lines[1]  # aが最初に来る
    assert '"japanese": "日本語"' in lines[2]
    assert '"z": 1' in lines[3]  # zが最後に来る

    # 読み込み確認
    result = await pytilpack.asyncio.read_json(json_file)
    assert result == test_data


@pytest.mark.asyncio
async def test_file_operations_with_encoding(tmp_path: pathlib.Path) -> None:
    """エンコーディングとエラーハンドリングのテスト。"""
    test_file = tmp_path / "test_encoding.txt"
    test_text = "Hello, 日本語"

    # UTF-8での書き込み・読み込み
    await pytilpack.asyncio.write_text(test_file, test_text, encoding="utf-8")
    result = await pytilpack.asyncio.read_text(test_file, encoding="utf-8")
    assert result == test_text

    # Shift_JISでの書き込み・読み込み
    await pytilpack.asyncio.write_text(test_file, test_text, encoding="shift_jis")
    result = await pytilpack.asyncio.read_text(test_file, encoding="shift_jis")
    assert result == test_text

    # errorsパラメータのテスト（ignore）
    await pytilpack.asyncio.write_text(test_file, "Hello\udc80World", encoding="utf-8", errors="ignore")
    result = await pytilpack.asyncio.read_text(test_file, encoding="utf-8")
    assert result == "HelloWorld"


@pytest.mark.asyncio
async def test_run_sync():
    """pytilpack.asyncio.run_syncのテスト。"""

    @pytilpack.asyncio.run_sync
    def sync_func(a: int, k: int) -> str:
        return str(a + k)

    assert await sync_func(1, k=2) == "3"


@pytest.mark.asyncio
async def test_acquire_with_timeout():
    lock = asyncio.Lock()
    async with pytilpack.asyncio.acquire_with_timeout(lock, 0.001) as acquired:
        assert acquired

    async with lock, pytilpack.asyncio.acquire_with_timeout(lock, 0.001) as acquired:
        assert not acquired


@pytest.mark.asyncio
async def async_func():
    await asyncio.sleep(0.0)
    return "Done"


@pytest.mark.asyncio(loop_scope="function")
async def test_run():
    await asyncio.to_thread(_sync_test_run)


def _sync_test_run():
    for _ in range(3):
        assert pytilpack.asyncio.run(async_func()) == "Done"


@pytest.mark.asyncio
async def test_run_async():
    for _ in range(3):
        assert pytilpack.asyncio.run(async_func()) == "Done"


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

    # JobRunnerを実行（1秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(1.0)
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

    # JobRunnerを実行（0.5秒後にシャットダウン）
    async def shutdown_after() -> None:
        await asyncio.sleep(0.5)
        runner.shutdown()

    start_time = time.perf_counter()
    await asyncio.gather(runner.run(), shutdown_after())
    thread.join()
    elapsed_time = time.perf_counter() - start_time
    assert 0.5 <= elapsed_time < 1.0

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
