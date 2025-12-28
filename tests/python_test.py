"""テストコード。"""

import pytest

import pytilpack.python


def test_coalesce():
    assert pytilpack.python.coalesce([]) is None
    assert pytilpack.python.coalesce([None]) is None
    assert pytilpack.python.coalesce([], 123) == 123
    assert pytilpack.python.coalesce([None], 123) == 123
    assert pytilpack.python.coalesce([None, 1, 2], 123) == 1


def test_remove_none():
    assert pytilpack.python.remove_none([]) == []
    assert pytilpack.python.remove_none([None]) == []
    assert pytilpack.python.remove_none([1, None, 2]) == [1, 2]


def test_empty():
    from pytilpack.python import empty

    assert empty(None)
    assert empty("")
    assert empty([])
    assert not empty(" ")
    assert not empty([0])
    assert not empty(0)


def test_default():
    from pytilpack.python import default

    assert default(None, 123) == 123
    assert default("", "123") == "123"
    assert default([], [123]) == [123]
    assert default(" ", "123") == " "
    assert default([0], [123]) == [0]
    assert default(0, 123) == 0


def test_doc_summary():
    from pytilpack.python import doc_summary

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

    assert pytilpack.python.class_field_comments(A) == {
        "b": "bbb",
        "c": "ccc",
        "d": "ddd",
    }


def test_get():
    from pytilpack.python import get

    data = {"a": [{"b": 1}], "none": None}

    # 正常系
    assert get(data, "a") == [{"b": 1}]
    assert get(data, ["a", 0]) == {"b": 1}
    assert get(data, ["a", 0, "b"]) == 1

    # デフォルト値
    assert get(data, ["a", 0, "c"], 2) == 2
    assert get(data, ["a", 1], 2) == 2
    assert get(data, ["c", 0], 2) == 2

    # 値がNone
    assert get(data, "none", 2) == 2
    assert get(data, "none", 2, default_if_none=False) is None

    # スカラーに対してまだキーがあるならエラー
    with pytest.raises(ValueError):
        get(data, ["a", 0, "b", "c"])
    assert get(data, ["a", 0, "b", "c"], 2, errors="ignore") == 2

    # 配列のインデックスはint型でなければならない
    with pytest.raises(ValueError):
        get(data, ["a", "0"])
    assert get(data, ["a", "0"], 2, errors="ignore") == 2


def test_get_float():
    from pytilpack.python import get_float

    data = {"a": 1.1, "b": "string", "c": None}

    assert get_float(data, "a") == 1.1
    assert get_float(data, "c", 2.2) == 2.2  # 値がNoneの場合
    assert get_float(data, "d", 2.2) == 2.2  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_float(data, "b")
    assert get_float(data, "b", errors="ignore") == 0.0


def test_get_bool():
    from pytilpack.python import get_bool

    data = {"a": True, "b": "string", "c": None}

    assert get_bool(data, "a") is True
    assert get_bool(data, "c", False) is False  # 値がNoneの場合
    assert get_bool(data, "d", False) is False  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_bool(data, "b")
    assert get_bool(data, "b", errors="ignore") is False


def test_get_int():
    from pytilpack.python import get_int

    data = {"a": 1, "b": "string", "c": None}

    assert get_int(data, "a") == 1
    assert get_int(data, "c", 2) == 2  # 値がNoneの場合
    assert get_int(data, "d", 2) == 2  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_int(data, "b")
    assert get_int(data, "b", errors="ignore") == 0


def test_get_str():
    from pytilpack.python import get_str

    data = {"a": "string", "b": 1, "c": None}

    assert get_str(data, "a") == "string"
    assert get_str(data, "c", "default") == "default"  # 値がNoneの場合
    assert get_str(data, "d", "default") == "default"  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_str(data, "b")
    assert get_str(data, "b", errors="ignore") == ""


def test_get_list():
    from pytilpack.python import get_list

    data = {"a": [1, 2, 3], "b": "string", "c": None}

    assert get_list(data, "a") == [1, 2, 3]
    assert get_list(data, "c", [4, 5, 6]) == [4, 5, 6]  # 値がNoneの場合
    assert get_list(data, "d", [4, 5, 6]) == [4, 5, 6]  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_list(data, "b")
    assert get_list(data, "b", errors="ignore") == []


def test_get_dict():
    from pytilpack.python import get_dict

    data = {"a": {"key": "value"}, "b": "string", "c": None}

    assert get_dict(data, "a") == {"key": "value"}
    assert get_dict(data, "c", {"d": "v"}) == {"d": "v"}  # 値がNoneの場合
    assert get_dict(data, "d", {"d": "v"}) == {"d": "v"}  # キーが存在しない場合

    with pytest.raises(ValueError):
        get_dict(data, "b")
    assert get_dict(data, "b", errors="ignore") == {}


@pytest.mark.parametrize(
    "value,target_type,expected",
    [
        # bool相互変換
        (True, bool, True),
        (False, bool, False),
        (0, bool, False),
        (1, bool, True),
        (2, bool, None),
        ("true", bool, True),
        ("True", bool, True),
        ("false", bool, False),
        ("False", bool, False),
        ("0", bool, False),
        ("1", bool, True),
        ("2", bool, None),
        # int相互変換
        (True, int, 1),
        (False, int, 0),
        (42, int, 42),
        (3.14, int, 3),
        ("42", int, 42),
        ("-123", int, -123),
        # float相互変換
        (True, float, 1.0),
        (False, float, 0.0),
        (3.14, float, 3.14),
        (42, float, 42.0),
        ("3.14", float, 3.14),
        ("-123.45", float, -123.45),
        # str相互変換
        (True, str, "True"),
        (False, str, "False"),
        (42, str, "42"),
        (3.14, str, "3.14"),
        ("hello", str, "hello"),
        # None処理
        (None, bool, None),
        (None, int, None),
        (None, float, None),
        (None, str, None),
    ],
)
def test_convert_success(value, target_type, expected):
    """convertの成功パターンのテスト。"""
    result = pytilpack.python.convert(value, target_type, None)
    assert result == expected


@pytest.mark.parametrize(
    "value,target_type,errors",
    [
        # bool変換エラー
        (2, bool, "strict"),
        (3.14, bool, "strict"),
        ("2", bool, "strict"),
        ([1, 2, 3], bool, "strict"),
        ({"key": "value"}, bool, "strict"),
        # int変換エラー
        ("invalid", int, "strict"),
        ("3.14abc", int, "strict"),
        ([1, 2, 3], int, "strict"),
        ({"key": "value"}, int, "strict"),
        # float変換エラー
        ("invalid", float, "strict"),
        ("3.14abc", float, "strict"),
        ([1, 2, 3], float, "strict"),
        ({"key": "value"}, float, "strict"),
    ],
)
def test_convert_error(value, target_type, errors):
    """convertのエラーパターンのテスト。"""
    with pytest.raises(ValueError):
        pytilpack.python.convert(value, target_type, None, errors=errors)


def test_singleton_mixin():
    """SingletonMixinのテスト。"""
    import threading
    import time

    # テスト用クラス
    class MyConfig(pytilpack.python.SingletonMixin):
        """テスト用のコンフィグクラス。"""

        def __init__(self):
            self.value = "initial"
            self.counter = 0

    class AnotherConfig(pytilpack.python.SingletonMixin):
        """テスト用の別のコンフィグクラス。"""

        def __init__(self):
            self.value = "another"

    # get_singleton()で取得できる
    config1 = MyConfig.get_singleton()
    assert config1.value == "initial"

    # 複数回get_singleton()しても同じインスタンス
    config2 = MyConfig.get_singleton()
    assert config1 is config2

    # インスタンスを変更すると他も変わる
    config1.value = "modified"
    assert config2.value == "modified"

    # 異なるクラスは異なるインスタンス
    another1 = AnotherConfig.get_singleton()
    another2 = AnotherConfig.get_singleton()
    assert another1 is another2
    assert id(another1) != id(config1)  # 異なるクラスのインスタンス

    # reset()後は新しいインスタンス
    MyConfig.reset()
    config3 = MyConfig.get_singleton()
    assert config3 is not config1
    assert config3.value == "initial"

    # 直接インスタンス化は禁止
    with pytest.raises(TypeError, match="は直接インスタンス化できません"):
        MyConfig()

    # スレッドセーフ性の確認（簡易）
    MyConfig.reset()
    instances = []

    def get_instance():
        time.sleep(0.001)  # 競合を起こしやすくする
        instance = MyConfig.get_singleton()
        instances.append(instance)

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # すべて同じインスタンス
    assert len(instances) == 10
    assert all(inst is instances[0] for inst in instances)


@pytest.mark.parametrize(
    "dst,src,expected",
    [
        # 両方がdictの場合の再帰的マージ
        ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        ({"a": 1}, {"a": 2}, {"a": 2}),
        ({"a": {"b": 1}}, {"a": {"c": 2}}, {"a": {"b": 1, "c": 2}}),
        ({"a": {"b": 1}}, {"a": {"b": 2, "c": 3}}, {"a": {"b": 2, "c": 3}}),
        ({"a": 1, "b": 2}, {"a": 10}, {"a": 10, "b": 2}),
        # 両方がリストの場合の結合
        ([1, 2], [3, 4], [1, 2, 3, 4]),
        ([], [1], [1]),
        ([1], [], [1]),
        # それ以外の場合(srcで上書き)
        (1, 2, 2),
        ("a", "b", "b"),
        (1, "a", "a"),
        ([1], {"a": 1}, {"a": 1}),
        ({"a": 1}, [1], [1]),
        (None, 1, 1),
        (1, None, None),
        # 複雑なケース
        (
            {"a": [1, 2], "b": {"c": 1}},
            {"a": [3], "b": {"d": 2}},
            {"a": [1, 2, 3], "b": {"c": 1, "d": 2}},
        ),
    ],
)
def test_merge(dst, src, expected):
    """mergeのテスト。"""
    actual = pytilpack.python.merge(dst, src)
    assert actual == expected
