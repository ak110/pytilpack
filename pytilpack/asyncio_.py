"""非同期I/O関連。"""

import abc
import asyncio
import logging
import typing

logger = logging.getLogger(__name__)

T = typing.TypeVar("T")


def run(coro: typing.Awaitable[T]) -> T:
    """非同期関数を実行する。"""
    # https://github.com/microsoftgraph/msgraph-sdk-python/issues/366#issuecomment-1830756182
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.debug("EventLoop Error", exc_info=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


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

    def __init__(
        self, max_job_concurrency: int = 8, poll_interval: float = 1.0
    ) -> None:
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

    @abc.abstractmethod
    async def poll(self) -> Job | None:
        """次のジョブを返す。ジョブがなければ None を返す。"""
