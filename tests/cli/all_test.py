"""全CLIコマンドのテスト（並行実行版）。"""

import asyncio

import pytest


async def _run_help(command: str, expected_text: str) -> None:
    """ヘルプコマンドを実行して期待されるテキストを確認する。"""
    proc = await asyncio.create_subprocess_exec(
        "pytilpack",
        command,
        "--help",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, f"{command} --help failed: {stderr.decode()}"
    assert expected_text in stdout.decode(), f"Expected '{expected_text}' not found in stdout"


@pytest.mark.asyncio
async def test_all_cli_commands() -> None:
    """全CLIコマンドのヘルプを並行実行してテスト。"""
    await asyncio.gather(
        _run_help("delete-empty-dirs", "空のディレクトリを削除"),
        _run_help("delete-old-files", "古いファイルを削除"),
        _run_help("sync", "ディレクトリを同期"),
        _run_help("fetch", "URL"),
        _run_help("mcp", "Model Context Protocol"),
        _run_help("--help", "usage:"),
    )
