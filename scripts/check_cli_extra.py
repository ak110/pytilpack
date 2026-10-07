"""配布環境のCLIヘルプをレジストリから検証する。"""

import subprocess
import sys

from pytilpack.cli.main import _SUBCOMMANDS


def main() -> int:
    """導入したextraに応じて成功と未導入案内を確認する。"""
    extra = sys.argv[1]
    root = subprocess.run(
        [sys.executable, "-I", "-m", "pytilpack.cli.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    failed = root.returncode != 0 or "usage:" not in root.stdout
    if failed:
        print(f"CLIの全体ヘルプが不整合です。\n{root.stdout}{root.stderr}", file=sys.stderr)
    for name, _, required_extra in _SUBCOMMANDS:
        if extra and required_extra is not None and extra not in (required_extra, "all"):
            continue
        result = subprocess.run(
            [sys.executable, "-I", "-m", "pytilpack.cli.main", name, "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        installed = required_extra is None or extra in (required_extra, "all")
        valid = result.returncode == (0 if installed else 2)
        valid = valid and ("usage:" in result.stdout if installed else f"extras [{required_extra}]" in result.stderr)
        if not valid:
            failed = True
            print(f"extra {extra or 'ベース'} の{name}ヘルプが不整合です。\n{result.stdout}{result.stderr}", file=sys.stderr)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
