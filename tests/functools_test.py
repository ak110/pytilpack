"""テストコード。"""

import pytest

import pytilpack.functools_


def test_retry_1():
    @pytilpack.functools_.retry(2, initial_delay=0, exponential_base=0)
    def f():
        f.call_count += 1

    f.call_count = 0
    f()
    assert f.call_count == 1


def test_retry_2():
    @pytilpack.functools_.retry(2, initial_delay=0, exponential_base=0)
    def f():
        f.call_count += 1
        raise RuntimeError("test")

    f.call_count = 0
    with pytest.raises(RuntimeError):
        f()
    assert f.call_count == 3
