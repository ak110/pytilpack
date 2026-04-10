"""テストコード。"""

import decimal
import pathlib

import pytest

import pytilpack.environ


def test_get_str() -> None:
    """get_strのテスト。"""
    env = {"TEST_STR": "hello"}
    assert pytilpack.environ.get_str("TEST_STR", environ=env) == "hello"
    assert pytilpack.environ.get_str("TEST_STR", "default", environ=env) == "hello"
    # デフォルト値
    assert pytilpack.environ.get_str("TEST_STR", "default", environ={}) == "default"
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_STR"):
        pytilpack.environ.get_str("TEST_STR", environ={})


def test_get_int() -> None:
    """get_intのテスト。"""
    env = {"TEST_INT": "42"}
    assert pytilpack.environ.get_int("TEST_INT", environ=env) == 42
    assert pytilpack.environ.get_int("TEST_INT", 0, environ=env) == 42
    # デフォルト値
    assert pytilpack.environ.get_int("TEST_INT", 99, environ={}) == 99
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_INT"):
        pytilpack.environ.get_int("TEST_INT", environ={})
    # 不正な値
    with pytest.raises(ValueError):
        pytilpack.environ.get_int("TEST_INT", environ={"TEST_INT": "abc"})


def test_get_float() -> None:
    """get_floatのテスト。"""
    env = {"TEST_FLOAT": "3.14"}
    assert pytilpack.environ.get_float("TEST_FLOAT", environ=env) == pytest.approx(3.14)
    # デフォルト値
    assert pytilpack.environ.get_float("TEST_FLOAT", 1.0, environ={}) == 1.0


def test_get_bool() -> None:
    """get_boolのテスト。"""
    for true_val in ("true", "True", "TRUE", "1"):
        assert pytilpack.environ.get_bool("K", environ={"K": true_val}) is True
    for false_val in ("false", "False", "FALSE", "0"):
        assert pytilpack.environ.get_bool("K", environ={"K": false_val}) is False
    # デフォルト値
    assert pytilpack.environ.get_bool("K", True, environ={}) is True
    # 不正な値
    with pytest.raises(ValueError):
        pytilpack.environ.get_bool("K", environ={"K": "invalid"})


def test_get_decimal() -> None:
    """get_decimalのテスト。"""
    env = {"TEST_DECIMAL": "3.14159"}
    assert pytilpack.environ.get_decimal("TEST_DECIMAL", environ=env) == decimal.Decimal("3.14159")
    # デフォルト値
    assert pytilpack.environ.get_decimal("TEST_DECIMAL", decimal.Decimal("0"), environ={}) == decimal.Decimal("0")
    # 不正な値
    with pytest.raises(ValueError):
        pytilpack.environ.get_decimal("TEST_DECIMAL", environ={"TEST_DECIMAL": "not-a-number"})


def test_get_path() -> None:
    """get_pathのテスト。"""
    env = {"TEST_PATH": "/tmp/test"}
    result = pytilpack.environ.get_path("TEST_PATH", environ=env)
    assert isinstance(result, pathlib.Path)
    assert result == pathlib.Path("/tmp/test").resolve()
    # デフォルト値
    default = pathlib.Path("/default")
    assert pytilpack.environ.get_path("TEST_PATH", default, environ={}) == default


def test_get_list() -> None:
    """get_listのテスト。"""
    # カンマ区切り
    env = {"TEST_LIST": "a,b,c"}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    # 空白の除去
    env = {"TEST_LIST": " a , b , c "}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    # 空文字列の除外
    env = {"TEST_LIST": "a,,b,,c"}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    # カスタムセパレータ
    env = {"TEST_LIST": "a:b:c"}
    assert pytilpack.environ.get_list("TEST_LIST", separator=":", environ=env) == [
        "a",
        "b",
        "c",
    ]
    # デフォルト値
    assert pytilpack.environ.get_list("TEST_LIST", default=["x"], environ={}) == ["x"]
    # 未設定でデフォルトなし
    with pytest.raises(ValueError, match="TEST_LIST"):
        pytilpack.environ.get_list("TEST_LIST", environ={})


def test_get_or_none() -> None:
    """get_or_noneのテスト。"""
    assert pytilpack.environ.get_or_none("TEST_KEY", environ={"TEST_KEY": "value"}) == "value"
    assert pytilpack.environ.get_or_none("TEST_KEY", environ={}) is None


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
