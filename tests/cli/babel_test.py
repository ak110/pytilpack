"""babel CLIのテスト。"""

import pathlib

import pytilpack.cli.main


def test_babel_extract_and_compile(tmp_path: pathlib.Path) -> None:
    """extract → init → compile の一連の流れをテスト。"""
    # テスト用Pythonファイルを作成
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text(
        'from pytilpack.i18n import gettext_func as _\nprint(_("Hello"))\nprint(_("World"))\n',
        encoding="utf-8",
    )
    pot_path = tmp_path / "messages.pot"
    locale_dir = tmp_path / "locales"

    # extract
    pytilpack.cli.main.main(["babel", "extract", str(src_dir), "-o", str(pot_path)])
    assert pot_path.exists()
    pot_content = pot_path.read_text(encoding="utf-8")
    assert "Hello" in pot_content
    assert "World" in pot_content

    # init
    pytilpack.cli.main.main(
        [
            "babel",
            "init",
            "-l",
            "ja",
            "-i",
            str(pot_path),
            "-d",
            str(locale_dir),
        ]
    )
    po_path = locale_dir / "ja" / "LC_MESSAGES" / "messages.po"
    assert po_path.exists()

    # compile
    pytilpack.cli.main.main(["babel", "compile", "-d", str(locale_dir)])
    mo_path = locale_dir / "ja" / "LC_MESSAGES" / "messages.mo"
    assert mo_path.exists()


def test_babel_update(tmp_path: pathlib.Path) -> None:
    """updateサブコマンドのテスト。"""
    # 初期POTを作成
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text(
        'from pytilpack.i18n import gettext_func as _\nprint(_("Hello"))\n',
        encoding="utf-8",
    )
    pot_path = tmp_path / "messages.pot"
    locale_dir = tmp_path / "locales"

    # extract → init
    pytilpack.cli.main.main(["babel", "extract", str(src_dir), "-o", str(pot_path)])
    pytilpack.cli.main.main(["babel", "init", "-l", "ja", "-i", str(pot_path), "-d", str(locale_dir)])

    # ソースを更新してextract
    (src_dir / "app.py").write_text(
        'from pytilpack.i18n import gettext_func as _\nprint(_("Hello"))\nprint(_("New message"))\n',
        encoding="utf-8",
    )
    pytilpack.cli.main.main(["babel", "extract", str(src_dir), "-o", str(pot_path)])

    # update
    pytilpack.cli.main.main(["babel", "update", "-i", str(pot_path), "-d", str(locale_dir)])
    po_path = locale_dir / "ja" / "LC_MESSAGES" / "messages.po"
    po_content = po_path.read_text(encoding="utf-8")
    assert "New message" in po_content
