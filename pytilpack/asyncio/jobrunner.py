"""同時実行数を制限して非同期ジョブを処理するランナー。"""

__lazy_modules__ = ["abc", "asyncio", "logging", "typing"]

import abc
import asyncio
import logging
import typing

logger = logging.getLogger(__name__)

__all__ = ["JobStatus", "Job", "JobRunner"]


JobStatus = typing.Literal["waiting", "running", "finished", "canceled", "errored"]


class Job(metaclass=abc.ABCMeta):
    """非同期ジョブ。"""

    def __init__(self) -> None:
        self.status: JobStatus = "waiting"

    @abc.abstractmethod
    async def run(self) -> None:
        """ジョブの処理。内部でブロッキング処理がある場合は適宜 asyncio.to_thread 等を利用する。"""

    async def on_finished(self) -> None:
        """ジョブが完了した場合に呼ばれる処理。必要に応じてサブクラスで追加の処理を行う。"""
        del self  # noqa

    async def on_canceled(self) -> None:
        """ジョブが完了する前にキャンセルされた場合に呼ばれる処理。必要に応じてサブクラスで追加の処理を行う。"""
        del self  # noqa

    async def on_errored(self) -> None:
        """ジョブがエラー終了した場合に呼ばれる処理。必要に応じてサブクラスで追加の処理を行う。"""
        del self  # noqa

    async def on_finally(self) -> None:
        """ジョブの終了時に必ず呼ばれる処理。必要に応じてサブクラスで追加の処理を行う。"""
        del self  # noqa


class JobRunner(metaclass=abc.ABCMeta):
    """非同期ジョブを最大 max_job_concurrency 並列で実行するクラス。

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
            transferred = False
            try:
                if not self.running:
                    break
                job = await self._poll()
                # poll()の待機中にも停止できるため、タスク登録の直前に再確認する。
                if not self.running:
                    break
                if job is not None:
                    task = asyncio.create_task(self._run_job(job))
                    task.add_done_callback(self.tasks.discard)
                    self.tasks.add(task)
                    transferred = True
            finally:
                if not transferred:
                    self.semaphore.release()
            if job is None:
                await asyncio.sleep(self.poll_interval)

    async def _poll(self) -> Job | None:
        try:
            return await self.poll()
        except Exception:
            logger.warning(
                "ジョブ取得エラー。次回のポーリングで取得し直して処理を続ける。繰り返す場合はpoll()の実装と取得元の状態を確かめる",
                exc_info=True,
            )
            return None

    async def _run_job(self, job: Job) -> None:
        try:
            job.status = "running"
            try:
                await job.run()
            except asyncio.CancelledError:
                await self._notify_job(job, "canceled")
                raise
            except Exception:
                logger.warning(
                    "ジョブ実行エラー。on_errored()を呼び出して処理を続ける。原因は付記した例外を参照",
                    exc_info=True,
                )
                await self._notify_job(job, "errored")
            else:
                await self._notify_job(job, "finished")
        finally:
            try:
                await asyncio.shield(job.on_finally())
            except Exception:
                logger.warning(
                    "ジョブ終了処理エラー。同時実行数の枠を解放して処理を続ける。on_finally()の実装を見直す", exc_info=True
                )
            finally:
                self.semaphore.release()

    async def _notify_job(self, job: Job, status: typing.Literal["finished", "canceled", "errored"]) -> None:
        """本体の結果を確定してから、上書き可能な通知を実行する。"""
        job.status = status
        callback = {"finished": job.on_finished, "canceled": job.on_canceled, "errored": job.on_errored}[status]
        try:
            await asyncio.shield(callback())
        except Exception:
            logger.warning(
                "ジョブの%s通知エラー。本体の結果を保持して終了処理を続ける。通知メソッドの実装を見直す",
                status,
                exc_info=True,
            )

    def shutdown(self) -> None:
        """停止処理。"""
        self.running = False
        # 現在実行中のタスクにキャンセルを通知
        for task in list(self.tasks):
            task.cancel()

    async def graceful_shutdown(self) -> None:
        """新規ジョブ取得を停止し、実行中のジョブ完了を待ってから戻る。"""
        self.running = False
        await asyncio.sleep(0)
        if len(self.tasks) > 0:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)

    @abc.abstractmethod
    async def poll(self) -> Job | None:
        """次のジョブを返す。ジョブがなければ None を返す。"""
