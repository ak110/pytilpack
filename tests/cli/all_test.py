import asyncio
import sys

import pytest

from pytilpack.cli.main import _SUBCOMMANDS


async def _run_help(command: str, expected_text: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytilpack.cli.main",
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
    await asyncio.gather(*(_run_help(name, "usage:") for name, _, _ in _SUBCOMMANDS), _run_help("--help", "usage:"))
