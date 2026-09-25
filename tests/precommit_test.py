"""pre-commit hookの入口テスト。"""

import pathlib
import subprocess

CONFIG_PATH = pathlib.Path(__file__).parents[1] / ".pre-commit-config.yaml"


def test_end_of_file_fixer_entrypoint(tmp_path: pathlib.Path) -> None:
    """除外対象を保持し、対象ファイルの末尾改行を修正する。"""
    cases = [
        (
            ("tests/data/example.txt", ".agents/skills", "sample/.agents/skills"),
            ("tests/datafile", ".agents/skills-extra", ".agents/other"),
        ),
        ((), (".agents/skills/file",)),
    ]
    for index, (excluded, included) in enumerate(cases):
        worktree = tmp_path / f"case-{index}"
        worktree.mkdir()
        for name in (*excluded, *included):
            path = worktree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("content", encoding="utf-8")
        subprocess.run(["git", "init", "--quiet", str(worktree)], check=True, capture_output=True)
        subprocess.run(["git", "add", "--", *excluded, *included], cwd=worktree, check=True)
        command = [
            "uvx",
            "prek",
            "--config",
            str(CONFIG_PATH),
            "run",
            "end-of-file-fixer",
            "--files",
            *excluded,
            *included,
        ]
        first = subprocess.run(command, cwd=worktree, capture_output=True, text=True, check=False)
        assert first.returncode == 1, first.stdout + first.stderr
        for name in excluded:
            assert (worktree / name).read_text(encoding="utf-8") == "content"
        for name in included:
            assert (worktree / name).read_text(encoding="utf-8") == "content\n"
        second = subprocess.run(command, cwd=worktree, capture_output=True, text=True, check=False)
        assert second.returncode == 0, second.stdout + second.stderr
