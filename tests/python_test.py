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


def test_empty():
    from pytilpack.python_ import empty

    assert empty(None)
    assert empty("")
    assert empty([])
    assert not empty(" ")
    assert not empty([0])
    assert not empty(0)


def test_default():
    from pytilpack.python_ import default

    assert default(None, 123) == 123
    assert default("", "123") == "123"
    assert default([], [123]) == [123]
    assert default(" ", "123") == " "
    assert default([0], [123]) == [0]
    assert default(0, 123) == 0


def test_doc_summary():
    from pytilpack.python_ import doc_summary

    assert doc_summary(None) == ""
    assert doc_summary(0) == "int([x]) -> integer"
    assert doc_summary(doc_summary) == "docstringの先頭1行分を取得する。"


def test_class_field_comments():
    class A:
        """テスト用クラス。"""

        a = 1  # aaa(無視されてほしいコメント)
        # bbb
        b = 2  # bbb(無視されてほしいコメント)
        # ccc
        c: str
        # ddd
        # (無視されてほしいコメント)
        d: str = "d"

    assert pytilpack.python_.class_field_comments(A) == {
        "b": "bbb",
        "c": "ccc",
        "d": "ddd",
    }


def test_get():
    from pytilpack.python_ import get

    data_dict = {"a": [{"b": 1}]}

    assert get(data_dict, "a") == [{"b": 1}]
    assert get(data_dict, ["a", 0]) == {"b": 1}
    assert get(data_dict, ["a", 0, "b"]) == 1
    assert get(data_dict, ["a", 0, "c"], 2) == 2
    assert get(data_dict, ["a", 1], 2) == 2
    assert get(data_dict, ["c", 0], 2) == 2


def test_get_float():
    from pytilpack.python_ import get_float

    data_dict = {"a": 1.1, "b": "string", "c": None}
    data_list = [1.1, "string", None]

    assert get_float(data_dict, "a") == 1.1
    assert get_float(data_dict, "c", 2.2) == 2.2
    assert get_float(data_list, 0) == 1.1
    assert get_float(data_list, 2, 2.2) == 2.2

    with pytest.raises(ValueError):
        get_float(data_dict, "b")

    with pytest.raises(ValueError):
        get_float(data_list, 1)


def test_get_bool():
    from pytilpack.python_ import get_bool

    data_dict = {"a": True, "b": "string", "c": None}
    data_list = [True, "string", None]

    assert get_bool(data_dict, "a") is True
    assert get_bool(data_dict, "c", False) is False
    assert get_bool(data_list, 0) is True
    assert get_bool(data_list, 2, False) is False

    with pytest.raises(ValueError):
        get_bool(data_dict, "b")

    with pytest.raises(ValueError):
        get_bool(data_list, 1)


def test_get_int():
    from pytilpack.python_ import get_int

    data_dict = {"a": 1, "b": "string", "c": None}
    data_list = [1, "string", None]

    assert get_int(data_dict, "a") == 1
    assert get_int(data_dict, "c", 2) == 2
    assert get_int(data_list, 0) == 1
    assert get_int(data_list, 2, 2) == 2

    with pytest.raises(ValueError):
        get_int(data_dict, "b")

    with pytest.raises(ValueError):
        get_int(data_list, 1)


def test_get_str():
    from pytilpack.python_ import get_str

    data_dict = {"a": "string", "b": 1, "c": None}
    data_list = ["string", 1, None]

    assert get_str(data_dict, "a") == "string"
    assert get_str(data_dict, "c", "default") == "default"
    assert get_str(data_list, 0) == "string"
    assert get_str(data_list, 2, "default") == "default"

    with pytest.raises(ValueError):
        get_str(data_dict, "b")

    with pytest.raises(ValueError):
        get_str(data_list, 1)


def test_get_list():
    from pytilpack.python_ import get_list

    data_dict = {"a": [1, 2, 3], "b": "string", "c": None}
    data_list = [[1, 2, 3], "string", None]

    assert get_list(data_dict, "a") == [1, 2, 3]
    assert get_list(data_dict, "c", [4, 5, 6]) == [4, 5, 6]
    assert get_list(data_list, 0) == [1, 2, 3]
    assert get_list(data_list, 2, [4, 5, 6]) == [4, 5, 6]

    with pytest.raises(ValueError):
        get_list(data_dict, "b")

    with pytest.raises(ValueError):
        get_list(data_list, 1)


def test_get_dict():
    from pytilpack.python_ import get_dict

    data_dict = {"a": {"key": "value"}, "b": "string", "c": None}
    data_list = [{"key": "value"}, "string", None]

    assert get_dict(data_dict, "a") == {"key": "value"}
    assert get_dict(data_dict, "c", {"default": "value"}) == {"default": "value"}
    assert get_dict(data_list, 0) == {"key": "value"}
    assert get_dict(data_list, 2, {"default": "value"}) == {"default": "value"}

    with pytest.raises(ValueError):
        get_dict(data_dict, "b")

    with pytest.raises(ValueError):
        get_dict(data_list, 1)
