"""pre-commit hookの入口テスト。"""

import pathlib
import subprocess

CONFIG_PATH = pathlib.Path(__file__).parents[1] / ".pre-commit-config.yaml"


def test_end_of_file_fixer_entrypoint(tmp_path: pathlib.Path) -> None:
    """除外対象を保持し、対象ファイルの末尾改行を修正する。"""
    excluded = tmp_path / "tests" / "data" / "example.txt"
    included = tmp_path / "tests" / "datafile"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("keep", encoding="utf-8")
    included.write_text("fix", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "add", "--", "tests/data/example.txt", "tests/datafile"], cwd=tmp_path, check=True)
    command = [
        "uvx",
        "prek",
        "--config",
        str(CONFIG_PATH),
        "run",
        "end-of-file-fixer",
        "--files",
        "tests/data/example.txt",
        "tests/datafile",
    ]

    first = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert first.returncode == 1, first.stdout + first.stderr
    assert excluded.read_text(encoding="utf-8") == "keep"
    assert included.read_text(encoding="utf-8") == "fix\n"

    second = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert second.returncode == 0, second.stdout + second.stderr
