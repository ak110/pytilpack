__lazy_modules__ = ["pathlib", "typing", "zipfile"]

import pathlib
import typing
import zipfile


def decode_zipinfo_filename(
    info: zipfile.ZipInfo,
    *,
    fallback_encodings: typing.Sequence[str] = ("cp932", "cp437"),
) -> str:
    # info.filenameはWindowsで\\を/へ置換済みのため、2バイト目に0x5Cを含むCP932の文字を復元できない。
    # orig_filenameを起点に復号する。
    if info.flag_bits & 0x800:
        decoded = info.orig_filename
    else:
        raw = info.orig_filename.encode("cp437")
        decoded = info.orig_filename
        for encoding in fallback_encodings:
            try:
                decoded = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
    nul = decoded.find("\x00")
    if nul >= 0:
        return decoded[:nul]
    return decoded


def is_safe_relative_path(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    for part in name.split("/"):
        if part in ("", ".."):
            return False
        if ":" in part:
            return False
    win = pathlib.PureWindowsPath(name)
    return not (win.drive or win.root)
