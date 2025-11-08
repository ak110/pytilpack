"""非同期I/O関連。"""

import asyncio
import concurrent.futures
import logging
import threading
import typing

logger = logging.getLogger(__name__)


class ThreadPool:
    """N個のスレッド上で非同期処理を実行するスレッドプール。"""

    def __init__(self, max_workers: int) -> None:
        """スレッドプールを初期化する。

        Args:
            max_workers: ワーカースレッド数(1以上)
        """
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self.workers = [WorkerThread(name=f"aloop-{i}") for i in range(max_workers)]
        self.next = 0
        self.lock = threading.Lock()
        for w in self.workers:
            w.start()

    def __enter__(self) -> "ThreadPool":
        """コンテキストマネージャーの開始処理。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャーの終了処理。"""
        self.shutdown()

    def submit[T](self, coro: typing.Coroutine[typing.Any, typing.Any, T]) -> concurrent.futures.Future[T]:
        """コルーチンを実行するワーカーに送信する。

        Args:
            coro: 実行するコルーチン

        Returns:
            結果を取得するためのFuture
        """
        with self.lock:
            idx = self.next
            self.next = (self.next + 1) % len(self.workers)
        return self.workers[idx].submit(coro)

    def map[T](self, coros: typing.Iterable[typing.Coroutine[typing.Any, typing.Any, T]]) -> list[concurrent.futures.Future[T]]:
        """複数のコルーチンをワーカーに送信する。

        Args:
            coros: 実行するコルーチンのイテラブル

        Returns:
            各コルーチンの結果を取得するためのFutureのリスト
        """
        return [self.submit(c) for c in coros]

    def shutdown(self) -> None:
        """全てのワーカースレッドを停止する。"""
        for w in self.workers:
            w.stop()

    async def ashutdown(self) -> None:
        """全てのワーカースレッドを非同期的に停止する。"""
        await asyncio.to_thread(self.shutdown)

    async def __aenter__(self) -> "ThreadPool":
        """非同期コンテキストマネージャーの開始処理。"""
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """非同期コンテキストマネージャーの終了処理。"""
        await self.ashutdown()

    def __del__(self) -> None:
        """デストラクタ。停止していないワーカーがいる場合は警告して停止シグナルを送る。"""
        active_workers = [w for w in self.workers if w.thread is not None]
        if active_workers:
            logger.warning(
                "ThreadPool is being destroyed with %d active worker(s). Sending stop signal.",
                len(active_workers),
            )
            # デストラクタ内では待機せず、停止シグナルだけ送る
            for w in active_workers:
                if w.loop is not None:
                    w.loop.call_soon_threadsafe(w.loop.stop)  # 一時的に無効化


class WorkerThread:
    """専用のasyncioイベントループを実行するワーカースレッド。"""

    def __init__(self, name: str) -> None:
        """ワーカースレッドを初期化する。

        Args:
            name: スレッド名
        """
        self.name = name
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stopped = threading.Event()

    def start(self) -> None:
        """ワーカースレッドを起動する。"""
        started = threading.Event()

        def thread() -> None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            started.set()
            try:
                self.loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(self.loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                finally:
                    self.loop.close()
                    self.stopped.set()

        self.thread = threading.Thread(target=thread, name=self.name, daemon=True)
        self.thread.start()
        started.wait()

    def submit[T](self, coro: typing.Coroutine[typing.Any, typing.Any, T]) -> concurrent.futures.Future[T]:
        """コルーチンをイベントループに送信する。

        Args:
            coro: 実行するコルーチン

        Returns:
            結果を取得するためのFuture
        """
        if self.loop is None:
            raise RuntimeError("worker not started")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        """ワーカースレッドを停止する。"""
        if self.loop is None:
            return
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.stopped.wait()
        self.loop = None
        self.thread = None
