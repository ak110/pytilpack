"""非同期I/O関連。"""

import abc
import asyncio
import concurrent.futures
import logging
import threading
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


class WorkerThread:
    """独自のイベントループを持つスレッド。複数の非同期タスクを同時に実行できる。"""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()
        self.running_tasks: int = 0
        self.lock = threading.Lock()

    def _start_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro: typing.Coroutine) -> None:
        """ワーカーのイベントループ上でコルーチンを実行する。"""
        with self.lock:
            self.running_tasks += 1
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(self._handle_result)

    def _handle_result(self, future: concurrent.futures.Future) -> None:
        try:
            future.result()
        except Exception:
            logger.warning("ジョブ実行中のエラー", exc_info=True)
        finally:
            with self.lock:
                self.running_tasks -= 1


class JobRunner(metaclass=abc.ABCMeta):
    """
    非同期ジョブを複数のワーカースレッドで分散して実行するクラス。

    Args:
        poll_interval: ジョブ取得のポーリング間隔（秒）
        num_workers: ワーカー数（各ワーカーは独自のイベントループを持つ）

    """

    def __init__(self, poll_interval: float = 1.0, num_workers: int = 4) -> None:
        self.poll_interval = poll_interval
        self.running = True
        self.workers = [WorkerThread() for _ in range(num_workers)]

    async def run(self) -> None:
        """poll()でジョブを取得し、適切なワーカーに dispatch します。"""
        while self.running:
            try:
                job = await asyncio.wait_for(self.poll(), timeout=self.poll_interval)
                if job:
                    worker = self._select_worker()
                    worker.submit(job.run())
            except asyncio.TimeoutError:
                continue
            except Exception:
                logger.warning("JobRunnerエラー", exc_info=True)

    def _select_worker(self) -> WorkerThread:
        """各ワーカーの実行中ジョブ数が最も少ないワーカーを選択する。"""
        return min(self.workers, key=lambda w: w.running_tasks)

    def shutdown(self) -> None:
        """停止処理。各ワーカーのイベントループも停止します。"""
        self.running = False
        for worker in self.workers:
            worker.loop.call_soon_threadsafe(worker.loop.stop)

    @abc.abstractmethod
    async def poll(self) -> Job | None:
        """次のジョブを返す。ジョブがなければ None を返す。"""
