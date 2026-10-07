"""空ディレクトリ削除のCLIを実際のファイルへ適用する。"""

from pathlib import Path

from pytilpack.cli.main import main


def test_delete_empty_dirs_cli(tmp_path: Path) -> None:
    """空の枝を削除し、ファイルを含む枝とルートを保持する。"""
    (tmp_path / "empty" / "nested").mkdir(parents=True)
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "file.txt").write_text("保持", encoding="utf-8")
    main(["delete-empty-dirs", str(tmp_path)])
    assert not (tmp_path / "empty").exists()
    assert (occupied / "file.txt").read_text(encoding="utf-8") == "保持"
    assert tmp_path.is_dir()


def test_delete_empty_root_cli(tmp_path: Path) -> None:
    """ルート削除のオプションを公開入口から指定する。"""
    main(["delete-empty-dirs", str(tmp_path), "--no-keep-root"])
    assert not tmp_path.exists()
