"""mcpコマンドのテストコード。"""

import subprocess


def test_mcp_help() -> None:
    """mcpコマンドのヘルプテスト。"""
    result = subprocess.run(
        ["pytilpack", "mcp", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Model Context Protocol" in result.stdout
    assert "--transport" in result.stdout
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--verbose" in result.stdout
