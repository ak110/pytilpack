"""main.pyのテスト。"""

import subprocess

import pytilpack.cli.main


def test_main_no_command(capsys) -> None:
    """引数なしでmain()を呼んだ場合のテスト。"""
    try:
        pytilpack.cli.main.main([])
    except SystemExit as e:
        assert e.code == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_main_help_command() -> None:
    """ヘルプコマンドのテスト。"""
    result = subprocess.run(["pytilpack", "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "delete-empty-dirs" in result.stdout
    assert "delete-old-files" in result.stdout
    assert "sync" in result.stdout
    assert "fetch" in result.stdout
