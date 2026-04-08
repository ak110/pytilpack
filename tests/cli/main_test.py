"""main.pyのテスト。"""

import importlib
import logging

import pytest

import pytilpack.cli.main


def test_main_no_command(capsys) -> None:
    """引数なしでmain()を呼んだ場合のテスト。"""
    try:
        pytilpack.cli.main.main([])
    except SystemExit as e:
        assert e.code == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out


@pytest.fixture(name="fake_missing_sqlalchemy")
def _fake_missing_sqlalchemy(monkeypatch: pytest.MonkeyPatch) -> None:
    """`pytilpack.cli.wait_for_db_connection` の import で sqlalchemy 欠落を再現する。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.wait_for_db_connection":
            raise ModuleNotFoundError("No module named 'sqlalchemy'", name="sqlalchemy")
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    # basicConfig の副作用を隔離する。
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.usefixtures("fake_missing_sqlalchemy")
def test_main_help_lists_missing_command(capsys) -> None:
    """extras 欠落コマンドも --help に (未インストール) として列挙される。"""
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "wait-for-db-connection" in captured.out
    assert "未インストール" in captured.out
    assert "sqlalchemy" in captured.out


@pytest.mark.parametrize(
    "argv",
    [
        ["wait-for-db-connection"],
        ["wait-for-db-connection", "sqlite:///x"],
        ["wait-for-db-connection", "--help"],
        ["wait-for-db-connection", "--timeout", "1"],
    ],
)
@pytest.mark.usefixtures("fake_missing_sqlalchemy")
def test_main_missing_extras_exits(capsys, argv: list[str]) -> None:
    """未インストールコマンドは argv 形に関わらず extras エラーで終了する。"""
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(argv)
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "extras [sqlalchemy]" in captured.err
    assert "pytilpack[sqlalchemy]" in captured.err
    assert "wait-for-db-connection" in captured.err


def test_main_real_import_error_reraised(monkeypatch: pytest.MonkeyPatch) -> None:
    """`pytilpack.cli.xxx` 自体の import 失敗は握りつぶさず再送出される。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.wait_for_db_connection":
            # モジュール自身が見つからない = 本物のバグを模擬する。
            raise ModuleNotFoundError(
                f"No module named {name!r}",
                name=name,
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.name == "pytilpack.cli.wait_for_db_connection"
