"""テストコード。"""

import logging
import time

import pytest

import pytilpack.functools


@pytest.mark.asyncio
async def test_retry() -> None:
    """retryデコレーターの同期・非同期テスト。"""
    # 同期: 成功ケース
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f_sync():
        nonlocal call_count
        call_count += 1

    f_sync()
    assert call_count == 1

    # 同期: エラーケース（リトライ後も失敗）
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f_sync_err():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        f_sync_err()
    assert call_count == 3

    # 非同期: 成功ケース
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f_async():
        nonlocal call_count
        call_count += 1

    await f_async()
    assert call_count == 1

    # 非同期: エラーケース
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f_async_err():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await f_async_err()
    assert call_count == 3


@pytest.mark.asyncio
async def test_warn_if_slow(caplog: pytest.LogCaptureFixture) -> None:
    """warn_if_slowデコレーターの同期・非同期テスト。"""
    with caplog.at_level(logging.WARNING):
        # 同期: 閾値以下（警告なし）
        @pytilpack.functools.warn_if_slow()
        def fast_function(x: int, y: str = "default"):
            return f"{x}-{y}"

        result = fast_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 0

        # 同期: 閾値超過（警告あり）
        @pytilpack.functools.warn_if_slow()
        def slow_function(x: int, y: str = "default"):
            time.sleep(0.01)
            return f"{x}-{y}"

        result = slow_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 1
        assert "slow_function took" in caplog.records[0].message
        assert "threshold 0.001 s" in caplog.records[0].message

        caplog.clear()

        # 非同期: 閾値以下（警告なし）
        @pytilpack.functools.warn_if_slow()
        async def fast_async_function(x: int, y: str = "default"):
            return f"{x}-{y}"

        result = await fast_async_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 0

        # 非同期: 閾値超過（警告あり）
        @pytilpack.functools.warn_if_slow()
        async def slow_async_function(x: int, y: str = "default"):
            time.sleep(0.01)
            return f"{x}-{y}"

        result = await slow_async_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 1
        assert "slow_async_function took" in caplog.records[0].message


@pytest.mark.asyncio
async def test_retry_override() -> None:
    """Retryオーバーライドのテスト（同期・非同期）。"""
    # 同期版
    call_count = 0

    @pytilpack.functools.retry(max_retries=5, initial_delay=0, exponential_base=0)
    def f(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    # デフォルト設定: max_retries=5 なので6回呼ばれる
    with pytest.raises(RuntimeError):
        f()
    assert call_count == 6

    # オーバーライド: max_retries=2 なので3回呼ばれる
    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(max_retries=2))
    assert call_count == 3

    # 部分的なオーバーライド
    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(max_retries=1))
    assert call_count == 2

    # 非同期版
    call_count = 0

    @pytilpack.functools.retry(max_retries=5, initial_delay=0, exponential_base=0)
    async def f_async(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await f_async()
    assert call_count == 6

    call_count = 0
    with pytest.raises(RuntimeError):
        await f_async(retry=pytilpack.functools.Retry(max_retries=2))
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_should_retry() -> None:
    """should_retry引数のテスト（同期・非同期）。"""

    def should_retry_func(exc: Exception) -> bool:
        return isinstance(exc, ValueError)

    # 同期版
    call_count = 0

    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0, should_retry=should_retry_func)
    def f(error_type: type[Exception]):
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    # ValueErrorはリトライされる
    call_count = 0
    with pytest.raises(ValueError):
        f(ValueError)
    assert call_count == 4

    # RuntimeErrorはリトライされない
    call_count = 0
    with pytest.raises(RuntimeError):
        f(RuntimeError)
    assert call_count == 1

    # 非同期版
    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0, should_retry=should_retry_func)
    async def f_async(error_type: type[Exception]):
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    call_count = 0
    with pytest.raises(ValueError):
        await f_async(ValueError)
    assert call_count == 4

    call_count = 0
    with pytest.raises(RuntimeError):
        await f_async(RuntimeError)
    assert call_count == 1


def test_retry_override_should_retry() -> None:
    """Retryオーバーライドでshould_retryを指定するテスト。"""
    call_count = 0

    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0)
    def f(retry=None, error_type: type[Exception] = RuntimeError):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    # デフォルト設定: すべての例外をリトライ
    with pytest.raises(RuntimeError):
        f()
    assert call_count == 4

    # オーバーライドでshould_retryを指定: ValueErrorのみリトライ
    def custom_should_retry(exc: Exception) -> bool:
        return isinstance(exc, ValueError)

    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(should_retry=custom_should_retry), error_type=RuntimeError)
    assert call_count == 1

    call_count = 0
    with pytest.raises(ValueError):
        f(retry=pytilpack.functools.Retry(should_retry=custom_should_retry), error_type=ValueError)
    assert call_count == 4
