"""fetchコマンドのテストコード。"""

import socket
import subprocess
import typing

import pytest
import pytest_asyncio
import quart

import pytilpack.quart


def get_free_port() -> int:
    """使用可能なポート番号を取得する。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest_asyncio.fixture(name="mock_server")
async def _mock_server() -> typing.AsyncGenerator[tuple[str, int], None]:
    """テスト用のモックサーバー。"""
    app = quart.Quart(__name__)
    port = get_free_port()

    @app.route("/")
    async def index():
        return (
            "<html><head><title>Example Domain</title></head>"
            "<body><h1>Example Domain</h1><p>This is a test page.</p></body></html>"
        )

    @app.route("/verbose")
    async def verbose():
        return "<html><head><title>Verbose Test</title></head><body><h1>Verbose Test</h1></body></html>"

    async with pytilpack.quart.run(app, port=port):
        yield "localhost", port


@pytest.mark.asyncio
async def test_fetch_success(mock_server: tuple[str, int]) -> None:
    """正常なURLの取得テスト。"""
    host, port = mock_server
    result = subprocess.run(
        ["pytilpack", "fetch", f"http://{host}:{port}/"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Example Domain" in result.stdout


@pytest.mark.asyncio
async def test_fetch_with_verbose(mock_server: tuple[str, int]) -> None:
    """verboseオプション付きのテスト。"""
    host, port = mock_server
    result = subprocess.run(
        [
            "pytilpack",
            "fetch",
            f"http://{host}:{port}/verbose",
            "--verbose",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Verbose Test" in result.stdout
    assert "[INFO ]" in result.stderr


def test_fetch_non_existent_url() -> None:
    """存在しないURLのテスト。"""
    port = get_free_port()
    result = subprocess.run(
        ["pytilpack", "fetch", f"http://localhost:{port}/"],
        capture_output=True,
        text=True,
        check=False,
    )

    # 接続エラーでプロセスが異常終了する
    assert result.returncode != 0
