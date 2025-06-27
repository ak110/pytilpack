"""テストコード。"""

import logging
import time

import pytest

import pytilpack.functools


def test_retry_1():
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f():
        nonlocal call_count
        call_count += 1

    f()
    assert call_count == 1


def test_retry_2():
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        f()
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_1_async():
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f():
        nonlocal call_count
        call_count += 1

    await f()
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_2_async():
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await f()
    assert call_count == 3


def test_warn_if_slow_not_trigger(caplog):
    """閾値以下の時間では警告が出ないことを確認。"""
    with caplog.at_level(logging.WARNING):

        @pytilpack.functools.warn_if_slow()
        def fast_function(x: int, y: str = "default"):
            return f"{x}-{y}"

        result = fast_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 0


def test_warn_if_slow_trigger(caplog):
    """閾値を超える時間で警告が出ることを確認。"""
    with caplog.at_level(logging.WARNING):

        @pytilpack.functools.warn_if_slow()
        def slow_function(x: int, y: str = "default"):
            time.sleep(0.01)
            return f"{x}-{y}"

        result = slow_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 1
        assert "Function test_warn_if_slow_trigger.<locals>.slow_function took" in caplog.records[0].message
        assert "threshold 0.001 s" in caplog.records[0].message


@pytest.mark.asyncio
async def test_warn_if_slow_async_not_trigger(caplog):
    """非同期関数で閾値以下の時間では警告が出ないことを確認。"""
    with caplog.at_level(logging.WARNING):

        @pytilpack.functools.warn_if_slow()
        async def fast_async_function(x: int, y: str = "default"):
            return f"{x}-{y}"

        result = await fast_async_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 0


@pytest.mark.asyncio
async def test_warn_if_slow_async_trigger(caplog):
    """非同期関数で閾値を超える時間で警告が出ることを確認。"""
    with caplog.at_level(logging.WARNING):

        @pytilpack.functools.warn_if_slow()
        def slow_async_function(x: int, y: str = "default"):
            time.sleep(0.01)
            return f"{x}-{y}"

        result = slow_async_function(42, y="test")
        assert result == "42-test"
        assert len(caplog.records) == 1
        assert "Function test_warn_if_slow_async_trigger.<locals>.slow_async_function took" in caplog.records[0].message
