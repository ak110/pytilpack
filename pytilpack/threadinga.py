"""スレッド関連のasync版。

`parallel()`は、各コルーチンを個別のOSスレッドで`asyncio.run()`することで並列実行する。
同一イベントループ上での`asyncio.gather()`と異なり、スレッドごとに独立したイベントループを持つ設計のため、
同期DBドライバーや非再入可能なリソース（SQLiteのコネクションなど）を複数コルーチンから安全に並列利用できる。

具体的な実装は`asyncio.to_thread()`で`_thread()`関数（スレッド上で`asyncio.run(coroutine)`を呼ぶ）を起動し、
`threading.Semaphore`で同時実行スレッド数を制御する二重構造になっている。
"""

import asyncio
import multiprocessing
import threading
import typing


async def parallel[T](
    funcs: list[typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]]],
    max_workers: int | None = None,
    timeout: float | None = None,
) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        funcs: 実行する関数のリスト。
        max_workers: 同時実行するスレッド数。Noneの場合はCPUのコア数。
        timeout: タイムアウト時間。

    Returns:
        各関数の戻り値のリスト。

    """
    semaphore = threading.Semaphore(max_workers if max_workers is not None else multiprocessing.cpu_count())

    def _thread(
        func: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
    ) -> T:
        with semaphore:
            return asyncio.run(func())

    tasks = [asyncio.to_thread(_thread, func) for func in funcs]
    if timeout is None:
        results = await asyncio.gather(*tasks)
    else:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
    return list(results)


async def parallel_for[T](func: typing.Callable[[int], typing.Awaitable[T]], n: int) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        func: 実行する関数。
        n: ループ回数。

    Returns:
        各関数の戻り値のリスト。

    """
    return await parallel([lambda i=i: func(i) for i in range(n)])  # type: ignore[misc]


async def parallel_foreach[T, U](func: typing.Callable[[U], typing.Awaitable[T]], items: typing.Iterable[U]) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        func: 実行する関数。
        items: 引数のリスト。

    Returns:
        各関数の戻り値のリスト。

    """
    return await parallel([lambda item=item: func(item) for item in items])  # type: ignore[misc]
