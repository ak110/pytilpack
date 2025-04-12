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


class Job(metaclass=abc.ABCMeta):
    """非同期ジョブ。内部でブロッキング処理がある場合は適宜 asyncio.to_thread などを利用すること。"""

    @abc.abstractmethod
    async def run(self) -> None:
        pass


class JobRunner(metaclass=abc.ABCMeta):
    """
    非同期ジョブを最大 max_parallel_jobs 並列で実行するクラス。

    Args:
        poll_interval: ジョブ取得のポーリング間隔（秒）
        max_parallel_jobs: 同時実行ジョブの最大数
    """

    def __init__(self, poll_interval: float = 1.0, max_parallel_jobs: int = 8) -> None:
        self.poll_interval = poll_interval
        self.max_parallel_jobs = max_parallel_jobs
        self.running = True
        self.semaphore = asyncio.Semaphore(max_parallel_jobs)

    async def run(self) -> None:
        """poll()でジョブを取得し、並列実行上限内でジョブを実行する。"""
        while self.running:
            # セマフォを取得して実行可能なジョブがあるか確認
            await self.semaphore.acquire()
            job: Job | None = None
            try:
                job = await self.poll()
            except Exception:
                logger.warning("ジョブ取得エラー", exc_info=True)
            if job is None:
                # ジョブがなければセマフォを解放して一定時間待機
                self.semaphore.release()
                await asyncio.sleep(self.poll_interval)
                continue
            # ジョブがあれば実行
            asyncio.create_task(self._run_job(job))

    async def _run_job(self, job: Job) -> None:
        try:
            await job.run()
        except Exception:
            logger.warning("ジョブ実行エラー", exc_info=True)
        finally:
            self.semaphore.release()

    def shutdown(self) -> None:
        """停止処理。"""
        self.running = False

    @abc.abstractmethod
    async def poll(self) -> Job | None:
        """次のジョブを返す。ジョブがなければ None を返す。"""
