import importlib
import logging
import subprocess
import sys

import pytest

import pytilpack.cli.main


def test_main_no_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main([])
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "サブコマンドが指定されていません" in captured.err
    assert "例: pytilpack delete-empty-dirs <ディレクトリ>" in captured.err
    assert "pytilpack <サブコマンド> --help" in captured.err


@pytest.fixture(name="fake_missing_sqlalchemy")
def _fake_missing_sqlalchemy(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.wait_for_db_connection":
            raise ModuleNotFoundError("No module named 'sqlalchemy'", name="sqlalchemy")
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


def _help_details(output: str, command: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        parts = line.split(maxsplit=1)
        if parts and parts[0] == command:
            indent = len(line) - len(line.lstrip())
            details = parts[1:]
            for continuation in lines[index + 1 :]:
                if not continuation.strip() or len(continuation) - len(continuation.lstrip()) <= indent:
                    break
                details.append(continuation.strip())
            return " ".join(details)
    raise AssertionError(f"ヘルプに {command} の説明がない")


@pytest.mark.usefixtures("fake_missing_sqlalchemy")
def test_main_help_lists_missing_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    details = _help_details(captured.out, "wait-for-db-connection")
    assert "未インストール" in details
    assert "sqlalchemy" in details


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
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(argv)
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "extras [sqlalchemy]" in captured.err
    assert "pytilpack[sqlalchemy]" in captured.err
    assert "wait-for-db-connection" in captured.err


def test_main_real_import_error_reraised(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.wait_for_db_connection":
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
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ModuleNotFoundError(
                "No module named 'mcp.server.mcpserver'",
                name="mcp.server.mcpserver",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.usefixtures("fake_missing_mcp_dependency")
def test_main_help_survives_missing_core_dep(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "sync" in captured.out
    details = _help_details(captured.out, "mcp")
    assert "利用不可" in details
    assert "extras" not in details and "pytilpack[" not in details


@pytest.fixture(name="fake_incompatible_mcp_dependency")
def _fake_incompatible_mcp_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ImportError(
                "internal detail: FastMCP_REVIEW_SENTINEL from '/internal/mcp/_compat.py'",
                name="mcp.server.mcpserver",
            )
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.parametrize("argv", [["mcp"], ["mcp", "--help"]])
@pytest.mark.usefixtures("fake_incompatible_mcp_dependency")
def test_main_incompatible_core_dep_exits(capsys, argv: list[str]) -> None:
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
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
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
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.mcp":
            raise ImportError("判別材料のない import 失敗")
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)

    with pytest.raises(ImportError):
        pytilpack.cli.main.main(["--help"])


@pytest.fixture(name="fake_wrapped_missing_greenlet")
def _fake_wrapped_missing_greenlet(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake(name: str, package: str | None = None):
        if name == "pytilpack.cli.wait_for_db_connection":
            try:
                raise ModuleNotFoundError("No module named 'greenlet'", name="greenlet")
            except ModuleNotFoundError as e:
                raise ImportError(
                    "The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed."
                ) from e
        return real_import_module(name, package)

    monkeypatch.setattr(pytilpack.cli.main.importlib, "import_module", fake)
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)


@pytest.mark.usefixtures("fake_wrapped_missing_greenlet")
def test_main_help_survives_wrapped_missing_dep(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["--help"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "sync" in captured.out
    details = _help_details(captured.out, "wait-for-db-connection")
    assert "未インストール" in details
    assert "sqlalchemy" in details


@pytest.mark.usefixtures("fake_wrapped_missing_greenlet")
def test_main_wrapped_missing_dep_exits(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        pytilpack.cli.main.main(["wait-for-db-connection", "sqlite:///x"])
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "extras [sqlalchemy]" in captured.err
    assert "pytilpack[sqlalchemy]" in captured.err


@pytest.mark.parametrize(
    ("missing", "command", "extras"),
    [("sqlalchemy", "wait-for-db-connection", "sqlalchemy"), ("babel", "babel", "babel")],
)
def test_main_help_lists_really_missing_command(missing: str, command: str, extras: str) -> None:
    code = f"import sys\nsys.modules[{missing!r}] = None\nimport pytilpack.cli.main\npytilpack.cli.main.main(['--help'])\n"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert command in result.stdout
    assert f"(未インストール: extras [{extras}] が必要)" in result.stdout
