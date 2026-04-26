"""ZIP関連のユーティリティ集。"""

import pathlib
import typing
import zipfile


def decode_zipinfo_filename(
    info: zipfile.ZipInfo,
    *,
    fallback_encodings: typing.Sequence[str] = ("cp932", "cp437"),
) -> str:
    r"""``ZipInfo``のファイル名を生バイト列基準で復号する。

    ``info.filename``は``zipfile._sanitize_filename``でプラットフォーム依存の
    加工（Windowsなら``\\``を``/``に置換）を経た文字列であり、CP932の
    2バイト目に``0x5C``を含む文字（ソ・ポ・表など）を含むエントリでは
    ``info.filename.encode("cp437").decode("cp932")``の往復復元に失敗する。
    そのため、生バイト列に近い``info.orig_filename``を起点に復号する。

    bit 11（Unicode flag）が立つ場合は``zipfile``がUTF-8で``orig_filename``を
    構築済みなのでそのまま採用する。立たない場合は``orig_filename``をCP437で
    エンコードして原バイト列を復元し、``fallback_encodings``の先頭からstrictで
    復号を試み、全て失敗した場合はCP437既定の``orig_filename``をそのまま返す。

    復号後はNUL文字以降を切り詰める。``zipfile._sanitize_filename``がもともと
    行うNUL切り詰め処理のうち、``orig_filename``起点では適用されない部分を
    最低限再現するもの。Windowsの``\\``→``/``置換は0x5C問題の原因のため再現しない。

    Zip Slip相当の検証は本関数では行わない。
    呼び出し側で``is_safe_relative_path``などにより別途検証すること。

    Args:
        info: 対象のZIPエントリ情報。
        fallback_encodings: bit 11未設定時に試行する復号エンコーディングの優先順。

    Returns:
        復号済みのエントリ名。

    """
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
    r"""ZIPエントリ名が展開先配下にとどまる安全な相対パスかを判定する。

    Zip Slip攻撃の防止を主目的とし、加えてSJIS復号崩れによる
    バックスラッシュ混入も併せて遮るため、以下を全て満たすことを要求する。

    - 空文字でない
    - バックスラッシュを含まない（CP932 2バイト目の``0x5C``混入の保険）
    - 先頭が``/``でない
    - ``/``区切りの各要素が``""``（連続``//``由来）でも``..``でもなく、``:``を含まない
    - ``PureWindowsPath``で``drive``または``root``を持たない
      （``C:foo``・``\\srv\share``等の拒否）

    NUL文字の混入チェックは``decode_zipinfo_filename``側で
    切り詰めにより吸収するため本関数では扱わない。

    Args:
        name: ZIPエントリ名相当の文字列。末尾``/``付きディレクトリ名は事前に除去すること。

    Returns:
        安全な相対パスであれば``True``、そうでなければ``False``。

    """
    if not name or "\\" in name or name.startswith("/"):
        return False
    for part in name.split("/"):
        if part in ("", ".."):
            return False
        if ":" in part:
            return False
    win = pathlib.PureWindowsPath(name)
    return not (win.drive or win.root)
