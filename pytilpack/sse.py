"""Server-Sent Events メッセージを生成するユーティリティ"""

import asyncio
import contextlib
import dataclasses
import functools
import logging
import typing

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SSE:
    r"""Server-Sent Events メッセージ。

    改行を含むデータは自動的に複数のdata:行に分割されます。

    仕様: <https://triple-underscore.github.io/HTML-server-sent-events-ja.html>

    Quartでの使用例::

        ```python
        import quart
        import pytilpack.sse

        app = quart.Quart(__name__)

        @app.route("/events")
        async def events():
            async def generate():
                # 複数行のデータも自動的に処理
                yield str(pytilpack.sse.SSE(
                    data="line 1\\nline 2\\nline 3",
                    event="update"
                ))
                await asyncio.sleep(1)

            return quart.Response(
                pytilpack.sse.add_keepalive(generate()),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        ```
    """

    data: str
    event: str | None = None
    id: str | None = None
    retry: int | None = None

    def __str__(self) -> str:
        """SSE形式の文字列への変換。

        Returns:
            SSE形式の文字列。各フィールドはコロンで区切られ、最後に空行が付加されます。
            data フィールドに改行が含まれる場合、複数の data: 行に分割されます。
        """
        return self.to_str()

    def to_str(self) -> str:
        """SSE形式の文字列への変換。

        Returns:
            SSE形式の文字列。各フィールドはコロンで区切られ、最後に空行が付加されます。
            data フィールドに改行が含まれる場合、複数の data: 行に分割されます。
        """
        lines = []

        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # dataフィールドの各行をdata:プレフィックス付きで追加
        for line in self.data.splitlines():
            lines.append(f"data: {line}")

        # 最後に空行を追加して終端
        return "\n".join(lines) + "\n\n"


def generator(interval: float = 15):
    """SSEジェネレーターのデコレーター。

    15秒以上メッセージが送信されない場合、コメント行を送信してコネクションを維持します。

    Args:
        interval: キープアライブを送信する間隔（秒）。デフォルトは15秒

    Returns:
        キープアライブが追加されたSSEメッセージストリームを生成するデコレーター
    """

    def decorator[**P, T: str | SSE](
        func: typing.Callable[P, typing.AsyncGenerator[T, None]],
    ) -> typing.Callable[P, typing.AsyncGenerator[str, None]]:
        """デコレーター本体。

        Args:
            func: SSEメッセージを生成する非同期ジェネレーター関数。

        Returns:
            キープアライブが追加されたSSEメッセージストリームを生成する非同期ジェネレーター関数。
        """

        # Awaitable -> Coroutine 用ユーティリティ
        async def _anext(it: typing.AsyncIterator[T]) -> T:
            return await anext(it)

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> typing.AsyncGenerator[str, None]:
            loop = asyncio.get_running_loop()
            last_msg_time = loop.time()
            generator_ = func(*args, **kwargs)
            try:
                next_task: asyncio.Task[T] | None = None
                try:
                    iterator = aiter(generator_)
                    next_task = loop.create_task(_anext(iterator))

                    while True:
                        # 次メッセージ取得タスク完了 or タイムアウト待ち
                        delay = interval - (loop.time() - last_msg_time)
                        try:
                            msg = await asyncio.wait_for(
                                asyncio.shield(next_task),
                                timeout=max(0.0, delay),
                            )
                            # メッセージ到着
                            if isinstance(msg, SSE):
                                yield str(msg)
                            else:
                                # strの場合は念のため末尾の改行を保証
                                yield msg.rstrip("\n") + "\n\n"
                            last_msg_time = loop.time()
                            next_task = loop.create_task(_anext(iterator))
                        except TimeoutError:
                            # タイムアウト → キープアライブ送信
                            yield ": ping\n\n"
                            last_msg_time = loop.time()
                        except StopAsyncIteration:
                            # ループ正常終了
                            break
                except asyncio.CancelledError:
                    logger.info("SSE切断")
                    raise
                finally:
                    if next_task is not None:
                        next_task.cancel()
                        with contextlib.suppress(StopAsyncIteration):
                            await asyncio.shield(next_task)
            finally:
                # ジェネレーターをクリーンアップ
                await asyncio.shield(generator_.aclose())

        return wrapper

    return decorator
