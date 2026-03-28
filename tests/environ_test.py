"""テストコード。"""

import decimal
import pathlib

import pytest

import pytilpack.environ


def test_get_str(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_strのテスト。"""
    monkeypatch.setenv("TEST_STR", "hello")
    assert pytilpack.environ.get_str("TEST_STR") == "hello"
    assert pytilpack.environ.get_str("TEST_STR", "default") == "hello"
    # デフォルト値
    monkeypatch.delenv("TEST_STR")
    assert pytilpack.environ.get_str("TEST_STR", "default") == "default"
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_STR"):
        pytilpack.environ.get_str("TEST_STR")


def test_get_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_intのテスト。"""
    monkeypatch.setenv("TEST_INT", "42")
    assert pytilpack.environ.get_int("TEST_INT") == 42
    assert pytilpack.environ.get_int("TEST_INT", 0) == 42
    # デフォルト値
    monkeypatch.delenv("TEST_INT")
    assert pytilpack.environ.get_int("TEST_INT", 99) == 99
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_INT"):
        pytilpack.environ.get_int("TEST_INT")
    # 不正な値
    monkeypatch.setenv("TEST_INT", "abc")
    with pytest.raises(ValueError):
        pytilpack.environ.get_int("TEST_INT")


def test_get_float(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_floatのテスト。"""
    monkeypatch.setenv("TEST_FLOAT", "3.14")
    assert pytilpack.environ.get_float("TEST_FLOAT") == pytest.approx(3.14)
    # デフォルト値
    monkeypatch.delenv("TEST_FLOAT")
    assert pytilpack.environ.get_float("TEST_FLOAT", 1.0) == 1.0


def test_get_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_boolのテスト。"""
    for true_val in ("true", "True", "TRUE", "1"):
        monkeypatch.setenv("TEST_BOOL", true_val)
        assert pytilpack.environ.get_bool("TEST_BOOL") is True
    for false_val in ("false", "False", "FALSE", "0"):
        monkeypatch.setenv("TEST_BOOL", false_val)
        assert pytilpack.environ.get_bool("TEST_BOOL") is False
    # デフォルト値
    monkeypatch.delenv("TEST_BOOL")
    assert pytilpack.environ.get_bool("TEST_BOOL", True) is True
    # 不正な値
    monkeypatch.setenv("TEST_BOOL", "invalid")
    with pytest.raises(ValueError):
        pytilpack.environ.get_bool("TEST_BOOL")


def test_get_decimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_decimalのテスト。"""
    monkeypatch.setenv("TEST_DECIMAL", "3.14159")
    assert pytilpack.environ.get_decimal("TEST_DECIMAL") == decimal.Decimal("3.14159")
    # デフォルト値
    monkeypatch.delenv("TEST_DECIMAL")
    assert pytilpack.environ.get_decimal("TEST_DECIMAL", decimal.Decimal("0")) == decimal.Decimal("0")
    # 不正な値
    monkeypatch.setenv("TEST_DECIMAL", "not-a-number")
    with pytest.raises(ValueError):
        pytilpack.environ.get_decimal("TEST_DECIMAL")


def test_get_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pathのテスト。"""
    monkeypatch.setenv("TEST_PATH", "/tmp/test")
    result = pytilpack.environ.get_path("TEST_PATH")
    assert isinstance(result, pathlib.Path)
    assert result == pathlib.Path("/tmp/test").resolve()
    # デフォルト値
    monkeypatch.delenv("TEST_PATH")
    default = pathlib.Path("/default")
    assert pytilpack.environ.get_path("TEST_PATH", default) == default


def test_get_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_listのテスト。"""
    # カンマ区切り
    monkeypatch.setenv("TEST_LIST", "a,b,c")
    assert pytilpack.environ.get_list("TEST_LIST") == ["a", "b", "c"]
    # 空白の除去
    monkeypatch.setenv("TEST_LIST", " a , b , c ")
    assert pytilpack.environ.get_list("TEST_LIST") == ["a", "b", "c"]
    # 空文字列の除外
    monkeypatch.setenv("TEST_LIST", "a,,b,,c")
    assert pytilpack.environ.get_list("TEST_LIST") == ["a", "b", "c"]
    # カスタムセパレータ
    monkeypatch.setenv("TEST_LIST", "a:b:c")
    assert pytilpack.environ.get_list("TEST_LIST", separator=":") == ["a", "b", "c"]
    # デフォルト値
    monkeypatch.delenv("TEST_LIST")
    assert pytilpack.environ.get_list("TEST_LIST", default=["x"]) == ["x"]
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_LIST"):
        pytilpack.environ.get_list("TEST_LIST")


def test_get_or_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_or_noneのテスト。"""
    monkeypatch.setenv("TEST_KEY", "value")
    assert pytilpack.environ.get_or_none("TEST_KEY") == "value"
    monkeypatch.delenv("TEST_KEY")
    assert pytilpack.environ.get_or_none("TEST_KEY") is None


def test_load_dotenv(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """load_dotenvのテスト。"""
    env_file = tmp_path / ".env"
    env_file.write_text("DOTENV_TEST_VAR=dotenv_value\n")
    # 読み込み前は未設定
    monkeypatch.delenv("DOTENV_TEST_VAR", raising=False)
    assert pytilpack.environ.get_or_none("DOTENV_TEST_VAR") is None
    # 読み込み後は設定される
    pytilpack.environ.load_dotenv(env_file)
    assert pytilpack.environ.get_or_none("DOTENV_TEST_VAR") == "dotenv_value"
    # クリーンアップ
    monkeypatch.delenv("DOTENV_TEST_VAR", raising=False)
