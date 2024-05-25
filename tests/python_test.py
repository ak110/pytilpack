"""テストコード。"""

import pytest

import pytilpack.python_


def test_coalesce():
    assert pytilpack.python_.coalesce([]) is None
    assert pytilpack.python_.coalesce([None]) is None
    assert pytilpack.python_.coalesce([], 123) == 123
    assert pytilpack.python_.coalesce([None], 123) == 123
    assert pytilpack.python_.coalesce([None, 1, 2], 123) == 1


def test_remove_none():
    assert pytilpack.python_.remove_none([]) == []
    assert pytilpack.python_.remove_none([None]) == []
    assert pytilpack.python_.remove_none([1, None, 2]) == [1, 2]


def test_is_null_or_empty():
    assert pytilpack.python_.is_null_or_empty(None)
    assert pytilpack.python_.is_null_or_empty("")
    assert pytilpack.python_.is_null_or_empty([])
    assert not pytilpack.python_.is_null_or_empty(" ")
    assert not pytilpack.python_.is_null_or_empty([0])
    assert not pytilpack.python_.is_null_or_empty(0)


def test_default_if_null_or_empty():
    assert pytilpack.python_.default_if_null_or_empty(None, 123) == 123
    assert pytilpack.python_.default_if_null_or_empty("", "123") == "123"
    assert pytilpack.python_.default_if_null_or_empty([], [123]) == [123]
    assert pytilpack.python_.default_if_null_or_empty(" ", "123") == " "
    assert pytilpack.python_.default_if_null_or_empty([0], [123]) == [0]
    assert pytilpack.python_.default_if_null_or_empty(0, 123) == 0


def test_retry_1():
    @pytilpack.python_.retry(2, initial_delay=0, exponential_base=0)
    def f():
        f.call_count += 1

    f.call_count = 0
    f()
    assert f.call_count == 1


def test_retry_2():
    @pytilpack.python_.retry(2, initial_delay=0, exponential_base=0)
    def f():
        f.call_count += 1
        raise RuntimeError("test")

    f.call_count = 0
    with pytest.raises(RuntimeError):
        f()
    assert f.call_count == 3
