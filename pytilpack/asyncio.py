"""非同期I/O関連。"""

import abc
import asyncio
import concurrent.futures
import contextlib
import datetime
import functools
import logging
import pathlib
import typing

import pytilpack.json
import pytilpack.pathlib

logger = logging.getLogger(__name__)


async def read_json(path: pathlib.Path | str) -> dict[str, typing.Any]:
    """JSONファイルから非同期で読み取る。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pytilpack.json.load, path)


async def write_json(
    path: pathlib.Path | str,
    data: dict,
    ensure_ascii: bool = False,
    indent: int | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
) -> None:
    """JSONファイルに非同期で書き込む。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        pytilpack.json.save,
        path,
        data,
        ensure_ascii,
        indent,
        separators,
        sort_keys,
    )


async def read_text(path: pathlib.Path | str, encoding: str = "utf-8", errors: str = "strict") -> str:
    """ファイルからテキストを非同期で読み取る。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_text, encoding, errors)


async def write_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で書き込む。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, path.write_text, data, encoding, errors)


async def append_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で追記する。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.append_text, path, data, encoding, errors)


async def read_bytes(path: pathlib.Path | str) -> bytes:
    """ファイルからバイトを非同期で読み取る。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_bytes)


async def write_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で書き込む。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, path.write_bytes, data)


async def append_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で追記する。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.append_bytes, path, data)


async def delete_file(path: pathlib.Path | str) -> None:
    """ファイルを非同期で削除する。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_file, path)


async def get_size(path: pathlib.Path | str) -> int:
    """ファイル・ディレクトリのサイズを非同期で取得する。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pytilpack.pathlib.get_size, path)


async def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    """指定したパス以下の空ディレクトリを削除する。

    Args:
        path: 対象のパス
        keep_root: Trueの場合、指定したディレクトリ自体は削除しない
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_empty_dirs, path, keep_root)


async def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
    """コピー元からコピー先へ同期する。
    Args:
        src: コピー元のパス
        dst: コピー先のパス
        delete: Trueの場合、コピー元に存在しないファイル・ディレクトリをコピー先から削除する
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.sync, src, dst, delete)


async def delete_old_files(
    path: str | pathlib.Path,
    before: datetime.datetime,
    delete_empty_dirs: bool = True,  # pylint: disable=redefined-outer-name
    keep_root_empty_dir: bool = True,
) -> None:
    """指定した日時より古いファイルを削除し、空になったディレクトリも削除する。

    Args:
        path: 対象のパス
        before: この日時より前に更新されたファイルを削除
        delete_empty_dirs: Trueの場合、空になったディレクトリを削除
        keep_root_empty_dir: Trueの場合、指定したディレクトリ自体は削除しない
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_old_files, path, before, delete_empty_dirs, keep_root_empty_dir)


def ensure_async[**P, R](
    func: typing.Callable[P, typing.Awaitable[R] | R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """関数が非同期関数でない場合、非同期関数に変換するデコレーター。"""
    if asyncio.iscoroutinefunction(func):
        return typing.cast(typing.Callable[P, typing.Awaitable[R]], func)
    else:
        return run_sync(typing.cast(typing.Callable[P, R], func))


def run_sync[**P, R](
    func: typing.Callable[P, R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """同期関数を非同期に実行するデコレーター。

    quart.utils.run_syncのquart関係ない版。
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


@contextlib.asynccontextmanager
async def acquire_with_timeout(lock: asyncio.Lock | asyncio.Semaphore, timeout: float) -> typing.AsyncGenerator[bool, None]:
    """ロックを取得し、タイムアウト時間内に取得できなかった場合はFalseを返す。

    Args:
        lock: 取得するロック。
        timeout: タイムアウト時間（秒）。

    Returns:
        ロックが取得できた場合はTrue、取得できなかった場合はFalse。

    """
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
        acquired = True
    except TimeoutError:
        acquired = False

    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


def run[T](coro: typing.Coroutine[typing.Any, typing.Any, T]) -> T:
    """非同期関数を実行する。"""
    # https://github.com/microsoftgraph/msgraph-sdk-python/issues/366#issuecomment-1830756182
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 非同期環境でない場合
        return asyncio.run(coro)

    # 何らかの理由でイベントループは存在するが動いてない場合 (謎)
    if not loop.is_running():
        return loop.run_until_complete(coro)

    # 現在のスレッドでイベントループが実行されている場合
    # 別スレッド・別イベントループで実行する
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: asyncio.run(coro))
        return future.result()


JobStatus = typing.Literal["waiting", "running", "finished", "canceled", "errored"]


class Job(metaclass=abc.ABCMeta):
    """非同期ジョブ。"""

    def __init__(self) -> None:
        self.status: JobStatus = "waiting"

    @abc.abstractmethod
    async def run(self) -> None:
        """ジョブの処理。内部でブロッキング処理がある場合は適宜 asyncio.to_thread などを利用してください。"""

    async def on_finished(self) -> None:
        """ジョブが完了した場合に呼ばれる処理。必要に応じてサブクラスで追加の処理をしてください。"""
        self.status = "finished"

    async def on_canceled(self) -> None:
        """ジョブが完了する前にキャンセルされた場合に呼ばれる処理。必要に応じてサブクラスで追加の処理をしてください。"""
        self.status = "canceled"

    async def on_errored(self) -> None:
        """ジョブがエラー終了した場合に呼ばれる処理。必要に応じてサブクラスで追加の処理をしてください。"""
        self.status = "errored"


class JobRunner(metaclass=abc.ABCMeta):
    """
    非同期ジョブを最大 max_job_concurrency 並列で実行するクラス。

    Args:
        max_job_concurrency: ジョブの最大同時実行数
        poll_interval: ジョブ取得のポーリング間隔（秒）
    """

    def __init__(self, max_job_concurrency: int = 8, poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval
        self.max_job_concurrency = max_job_concurrency
        self.running = True
        self.semaphore = asyncio.Semaphore(max_job_concurrency)
        self.tasks: set[asyncio.Task] = set()  # 実行中ジョブのタスクを管理

    async def run(self) -> None:
        """poll()でジョブを取得し、並列実行上限内でジョブを実行する。"""
        while self.running:
            # セマフォを取得して実行可能なジョブがあるか確認
            await self.semaphore.acquire()
            # 再度self.runningをチェック (graceful_shutdown()対策)
            if not self.running:
                self.semaphore.release()
                break
            job = await self._poll()
            if job is None:
                # ジョブがなければセマフォを解放して一定時間待機
                self.semaphore.release()
                await asyncio.sleep(self.poll_interval)
            else:
                # ジョブがあれば実行
                task = asyncio.create_task(self._run_job(job))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)

    async def _poll(self) -> Job | None:
        try:
            return await self.poll()
        except Exception:
            logger.warning("ジョブ取得エラー", exc_info=True)
            return None

    async def _run_job(self, job: Job) -> None:
        try:
            await job.run()
            await asyncio.shield(job.on_finished())
        except asyncio.CancelledError:
            try:
                await asyncio.shield(job.on_canceled())
            except Exception:
                logger.warning("ジョブキャンセル処理エラー", exc_info=True)
            raise  # 例外を再送出してキャンセル状態を伝搬
        except Exception:
            logger.warning("ジョブ実行エラー", exc_info=True)
            try:
                await asyncio.shield(job.on_errored())
            except Exception:
                logger.warning("ジョブエラー処理エラー", exc_info=True)
        finally:
            self.semaphore.release()

    def shutdown(self) -> None:
        """停止処理。"""
        self.running = False
        # 現在実行中のタスクにキャンセルを通知
        for task in list(self.tasks):
            task.cancel()

    async def graceful_shutdown(self) -> None:
        """新規ジョブ取得を停止し、実行中のジョブ完了を待ってから戻る"""
        self.running = False
        await asyncio.sleep(0)
        if len(self.tasks) > 0:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)

    @abc.abstractmethod
    async def poll(self) -> Job | None:
        """次のジョブを返す。ジョブがなければ None を返す。"""
