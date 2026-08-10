"""pre-commit設定のテスト。"""

import pathlib
import re

import pytest
import yaml

CONFIG_PATH = pathlib.Path(__file__).parents[1] / ".pre-commit-config.yaml"
CONFIG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
END_OF_FILE_FIXER = next(hook for repo in CONFIG["repos"] for hook in repo["hooks"] if hook["id"] == "end-of-file-fixer")


@pytest.mark.parametrize(
    "path,excluded",
    [
        ("tests/data/example.txt", True),
        (".agents/skills", True),
        ("sample/.agents/skills", True),
        ("tests/datafile", False),
        (".agents/skills-extra", False),
        (".agents/skills/file", False),
        (".agents/other", False),
    ],
)
def test_end_of_file_fixer_exclude(path: str, *, excluded: bool) -> None:
    pattern = re.compile(END_OF_FILE_FIXER["exclude"])

    assert bool(pattern.search(path)) is excluded
