"""main.pyのテスト。"""

import pytilpack.cli.main


def test_main_no_command(capsys) -> None:
    """引数なしでmain()を呼んだ場合のテスト。"""
    try:
        pytilpack.cli.main.main([])
    except SystemExit as e:
        assert e.code == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out
