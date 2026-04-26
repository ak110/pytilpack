"""pytilpack.zipfileのテスト。"""

import pathlib
import zipfile

import pytilpack.zipfile


class _Cp932ZipInfo(zipfile.ZipInfo):
    """ファイル名をCP932でエンコードし、Unicode flag（bit 11）を立てないZipInfo。

    Python標準の``ZipInfo._encodeFilenameFlags``は非ASCII名をUTF-8に変換して
    bit 11を立てる。これを上書きすることで、過去の日本語ZIP互換のパターン
    （CP932生バイト + bit 11未設定）をテストで再現できる。
    """

    def _encodeFilenameFlags(self) -> tuple[bytes, int]:
        return self.filename.encode("cp932"), self.flag_bits & ~0x800


class _RawBytesZipInfo(zipfile.ZipInfo):
    """ファイル名として任意の生バイト列を書き込むZipInfo。

    CP932 strictで復号できないバイト列や、NUL文字を含むエントリ名を
    テストで合成するために使う。bit 11は立てない。
    """

    def __init__(self, raw_name: bytes) -> None:
        super().__init__(raw_name.decode("cp437"))
        self._raw_name = raw_name

    def _encodeFilenameFlags(self) -> tuple[bytes, int]:
        return self._raw_name, self.flag_bits & ~0x800


def _build_zip(path: pathlib.Path, infos_and_data: list[tuple[zipfile.ZipInfo, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for info, data in infos_and_data:
            zf.writestr(info, data)


def _read_first_orig(path: pathlib.Path) -> zipfile.ZipInfo:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.infolist()[0]


def test_decode_utf8_with_bit11(tmp_path: pathlib.Path) -> None:
    """bit 11が立つUTF-8エントリはorig_filenameをそのまま採用する。"""
    archive = tmp_path / "u.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("日本語.txt", b"x")
    info = _read_first_orig(archive)
    assert info.flag_bits & 0x800
    assert pytilpack.zipfile.decode_zipinfo_filename(info) == "日本語.txt"


def test_decode_cp932_strict_success(tmp_path: pathlib.Path) -> None:
    """bit 11未設定のCP932エントリはCP932で復号する。"""
    archive = tmp_path / "j.zip"
    _build_zip(archive, [(_Cp932ZipInfo("あいう.txt"), b"x")])
    info = _read_first_orig(archive)
    assert info.flag_bits & 0x800 == 0
    assert pytilpack.zipfile.decode_zipinfo_filename(info) == "あいう.txt"


def test_decode_sjis_backslash_byte_kept_as_single_string(tmp_path: pathlib.Path) -> None:
    """SJIS 2バイト目に0x5Cを含む文字（ソ）でもバックスラッシュ分割されない。"""
    archive = tmp_path / "s.zip"
    _build_zip(archive, [(_Cp932ZipInfo("ソート/メモ.txt"), b"x")])
    info = _read_first_orig(archive)
    decoded = pytilpack.zipfile.decode_zipinfo_filename(info)
    assert decoded == "ソート/メモ.txt"
    assert "\\" not in decoded


def test_decode_cp932_failure_falls_back_to_cp437(tmp_path: pathlib.Path) -> None:
    """CP932 strictで復号できないバイト列はCP437へフォールバックする。"""
    # 0x81はCP932の有効なlead byteだが、0x39は有効なtrail byte範囲外のためstrict失敗。
    raw_invalid = b"\x81\x39hi.txt"
    archive = tmp_path / "f.zip"
    _build_zip(archive, [(_RawBytesZipInfo(raw_invalid), b"x")])
    info = _read_first_orig(archive)
    assert pytilpack.zipfile.decode_zipinfo_filename(info) == raw_invalid.decode("cp437")


def test_decode_truncates_at_nul(tmp_path: pathlib.Path) -> None:
    """NUL文字以降は切り詰める（_sanitize_filenameの挙動を再現）。"""
    archive = tmp_path / "n.zip"
    _build_zip(archive, [(_RawBytesZipInfo(b"bad\x00name.txt"), b"x")])
    info = _read_first_orig(archive)
    assert pytilpack.zipfile.decode_zipinfo_filename(info) == "bad"


def test_decode_all_fallbacks_fail_returns_orig_filename(tmp_path: pathlib.Path) -> None:
    """全フォールバック失敗時はCP437既定のorig_filenameを返す。"""
    raw_invalid = b"\x81\x39hi.txt"
    archive = tmp_path / "ff.zip"
    _build_zip(archive, [(_RawBytesZipInfo(raw_invalid), b"x")])
    info = _read_first_orig(archive)
    # cp932・cp437とも失敗するエンコーディングのみを与えた場合（cp437は失敗しないので
    # 現実には必ずどこかで成功するが、空タプルを与えるとフォールバックは全失敗扱い）。
    result = pytilpack.zipfile.decode_zipinfo_filename(info, fallback_encodings=())
    assert result == info.orig_filename


def test_is_safe_relative_path_accepts_normal_path() -> None:
    assert pytilpack.zipfile.is_safe_relative_path("foo/bar.txt")
    assert pytilpack.zipfile.is_safe_relative_path("a/b/c.txt")
    assert pytilpack.zipfile.is_safe_relative_path("日本語.txt")


def test_is_safe_relative_path_rejects_unsafe_paths() -> None:
    assert not pytilpack.zipfile.is_safe_relative_path("")
    assert not pytilpack.zipfile.is_safe_relative_path("a\\b.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("/abs.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("../escape.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("a/../b.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("a//b.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("C:/win.txt")
    assert not pytilpack.zipfile.is_safe_relative_path("C:foo")
    assert not pytilpack.zipfile.is_safe_relative_path(r"\\srv\share\file.txt")
