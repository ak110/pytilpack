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
