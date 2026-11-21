"""専用スレッド上のイベントループで非同期処理を実行するプール。"""

__lazy_modules__ = ["asyncio", "concurrent.futures", "dataclasses", "logging", "threading", "typing"]

import asyncio
import concurrent.futures
import dataclasses
import logging
import threading
import typing

logger = logging.getLogger(__name__)

__all__ = ["ThreadPool"]


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
        self._shutdown = False
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
            if self._shutdown:
                raise RuntimeError("ThreadPoolは停止済みです。新しいプールを作成して送信してください。")
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
        with self.lock:
            self._shutdown = True
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
        active_workers = [w for w in getattr(self, "workers", ()) if w.thread is not None]
        if active_workers:
            logger.warning(
                "ThreadPool is being destroyed with %d active worker(s). Sending stop signal."
                " Call shutdown() or ashutdown(), or use the pool in a with/async with block, before releasing it.",
                len(active_workers),
            )
            # デストラクタ内では待機せず、停止シグナルのみ送出する
            for w in active_workers:
                w._request_stop()


@dataclasses.dataclass(frozen=True)
class _Starting:
    thread: threading.Thread
    ready: concurrent.futures.Future[None]


@dataclasses.dataclass(frozen=True)
class _Running:
    thread: threading.Thread
    loop: asyncio.AbstractEventLoop


@dataclasses.dataclass(frozen=True)
class _Stopping(_Running):
    pass


class WorkerThread:
    """専用のasyncioイベントループを実行するワーカースレッド。"""

    def __init__(self, name: str) -> None:
        """ワーカースレッドを初期化する。

        Args:
            name: スレッド名
        """
        self.name = name
        self._lock = threading.Lock()
        self._state: _Starting | _Running | None = None
        self.stopped = threading.Event()

    @property
    def thread(self) -> threading.Thread | None:
        """現在の起動で使うスレッド。"""
        with self._lock:
            return self._state.thread if self._state is not None else None

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        """準備済みのイベントループ。"""
        with self._lock:
            return self._state.loop if isinstance(self._state, _Running) else None

    def start(self) -> None:
        """ワーカースレッドを起動する。停止処理中はRuntimeErrorを送出する。"""
        with self._lock:
            state = self._state
            if isinstance(state, _Stopping):
                raise RuntimeError("worker is stopping")
            if isinstance(state, _Running):
                return
            if state is None:
                ready = concurrent.futures.Future[None]()
                thread = threading.Thread(target=self._run, args=(ready,), name=self.name, daemon=True)
                self._state = _Starting(thread, ready)
                self.stopped.clear()
                try:
                    thread.start()
                except BaseException:
                    self._set_idle()
                    raise
            else:
                ready = state.ready
        ready.result()

    def _run(self, ready: concurrent.futures.Future[None]) -> None:
        try:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                with self._lock:
                    self._state = _Running(threading.current_thread(), loop)
                    ready.set_result(None)
                try:
                    loop.run_forever()
                finally:
                    self._request_stop(signal=False)
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()
        except BaseException as exc:
            if ready.done():
                raise
            with self._lock:
                self._set_idle()
                ready.set_exception(exc)
        finally:
            with self._lock:
                state = self._state
                if state is not None and state.thread is threading.current_thread():
                    self._set_idle()

    def _set_idle(self) -> None:
        self._state = None
        self.stopped.set()

    def _request_stop(self, *, signal: bool = True, thread: threading.Thread | None = None) -> None:
        with self._lock:
            state = self._state
            if not isinstance(state, _Running) or isinstance(state, _Stopping):
                return
            if thread is not None and state.thread is not thread:
                return
            if signal:
                state.loop.call_soon_threadsafe(state.loop.stop)
            self._state = _Stopping(state.thread, state.loop)

    def submit[T](self, coro: typing.Coroutine[typing.Any, typing.Any, T]) -> concurrent.futures.Future[T]:
        """コルーチンをイベントループに送信する。

        Args:
            coro: 実行するコルーチン

        Returns:
            結果を取得するためのFuture
        """
        with self._lock:
            state = self._state
            if not isinstance(state, _Running) or isinstance(state, _Stopping):
                raise RuntimeError("worker not started")
            return asyncio.run_coroutine_threadsafe(coro, state.loop)

    def stop(self) -> None:
        """ワーカースレッドを停止する。"""
        with self._lock:
            state = self._state
        if state is None:
            return
        if isinstance(state, _Starting):
            concurrent.futures.wait((state.ready,))
        self._request_stop(thread=state.thread)
        state.thread.join()
