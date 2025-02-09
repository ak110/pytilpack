"""スレッド関連。"""

import concurrent.futures
import typing

T = typing.TypeVar("T")
U = typing.TypeVar("U")


def parallel(
    funcs: typing.Iterable[typing.Callable[[], T]],
    max_workers: int | None = None,
    thread_name_prefix: str = "",
    timeout: float | None = None,
    chunksize: int = 1,
) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        funcs: 実行する関数のリスト。
        max_workers: 同時実行するスレッド数。Noneの場合はCPUのコア数。
        thread_name_prefix: スレッド名のプレフィックス。
        initializer: スレッドの初期化関数。
        initargs: 初期化関数の引数。
        timeout: タイムアウト時間。
        chunksize: 一度に実行する関数の数。

    Returns:
        各関数の戻り値のリスト。

    """
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix=thread_name_prefix
    ) as executor:
        return list(
            executor.map(lambda f: f(), funcs, timeout=timeout, chunksize=chunksize)
        )


def parallel_for(func: typing.Callable[[int], T], n: int) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        func: 実行する関数。
        n: ループ回数。

    Returns:
        各関数の戻り値のリスト。

    """
    return parallel([lambda i=i: func(i) for i in range(n)])  # type: ignore[misc]


def parallel_foreach(
    func: typing.Callable[[U], T], items: typing.Iterable[U]
) -> list[T]:
    """複数の関数を並列実行する。

    Args:
        func: 実行する関数。
        items: 引数のリスト。

    Returns:
        各関数の戻り値のリスト。

    """
    return parallel([lambda item=item: func(item) for item in items])  # type: ignore[misc]
