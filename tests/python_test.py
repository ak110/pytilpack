"""テストコード。"""

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
