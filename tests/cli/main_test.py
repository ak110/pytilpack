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
    """`pytilpack.cli.xxx` 自体の import 失敗は抑制されず再送出される。"""
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


@pytest.fixture(name="fake_missing_mcp_dependency")
def _fake_missing_mcp_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """`pytilpack.cli.mcp` の import で実障害の外部パッケージ欠落を再現する。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ModuleNotFoundError(
                "No module named 'mcp.server.mcpserver'",
                name="mcp.server.mcpserver",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    # basicConfig の副作用を隔離する。
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.usefixtures("fake_missing_mcp_dependency")
def test_main_help_survives_missing_core_dep(capsys) -> None:
    """外部パッケージ欠落が CLI 全体を停止させない。"""
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    # 無関係なサブコマンドは通常どおり列挙される。
    assert "sync" in captured.out
    assert "利用不可" in captured.out


@pytest.fixture(name="fake_incompatible_mcp_dependency")
def _fake_incompatible_mcp_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """`pytilpack.cli.mcp` の import で外部パッケージの属性消失を再現する。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ImportError(
                "internal detail: FastMCP_REVIEW_SENTINEL from '/internal/mcp/_compat.py'",
                name="mcp.server.mcpserver",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    # basicConfig の副作用を隔離する。
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.parametrize("argv", [["mcp"], ["mcp", "--help"]])
@pytest.mark.usefixtures("fake_incompatible_mcp_dependency")
def test_main_incompatible_core_dep_exits(capsys, argv: list[str]) -> None:
    """属性が消失したコア依存サブコマンドは失敗理由を提示して終了する。"""
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(argv)
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "pytilpack mcp" in captured.err
    assert "mcp.server.mcpserver" in captured.err
    assert "ImportError" in captured.err
    assert "pip install -U pytilpack" in captured.err
    assert "FastMCP_REVIEW_SENTINEL" not in captured.err
    assert "/internal/mcp/_compat.py" not in captured.err


def test_main_incompatible_optional_dep_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    """extras対象の互換性問題は未導入案内と区別する。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.babel":
            raise ImportError(
                "internal detail: OPTIONAL_DEP_REVIEW_SENTINEL",
                name="babel.messages.catalog",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)

    with pytest.raises(SystemExit) as help_exc_info:
        pytilpack.cli.main.main(["--help"])
    assert help_exc_info.value.code == 0

    help_output = capsys.readouterr().out
    assert "利用不可" in help_output
    assert "extras [babel]" not in help_output

    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["babel"])
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "pytilpack babel" in captured.err
    assert "babel.messages.catalog" in captured.err
    assert "ImportError" in captured.err
    assert "pip install -U 'pytilpack[babel]'" in captured.err
    assert "extras [babel]" not in captured.err
    assert "OPTIONAL_DEP_REVIEW_SENTINEL" not in captured.err


def test_main_internal_import_error_reraised(monkeypatch: pytest.MonkeyPatch) -> None:
    """自パッケージ配下のモジュールの import 失敗は抑制されず再送出される。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            # サブコマンドが依存する自パッケージ内モジュールの欠落を模擬する。
            raise ModuleNotFoundError(
                "No module named 'pytilpack.htmlrag'",
                name="pytilpack.htmlrag",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.name == "pytilpack.htmlrag"


def test_main_import_error_without_name_reraised(monkeypatch: pytest.MonkeyPatch) -> None:
    """`name` を持たない `ImportError` は判別できないため再送出される。"""
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ImportError("判別材料のない import 失敗")
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)

    with pytest.raises(ImportError):
        pytilpack.cli.main.main(["--help"])
