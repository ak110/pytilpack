"""datetime関連。"""

import datetime
import zoneinfo


def fromiso(
    iso_str: str, tz: zoneinfo.ZoneInfo | str | None = None, remove_tz: bool = False
) -> datetime.datetime:
    """ISO形式の文字列をdatetimeオブジェクトに変換する。

    Args:
        iso_str (str): ISO形式の文字列。
        tz (zoneinfo.ZoneInfo | str | None): タイムゾーン。
        remove_tz (bool): タイムゾーン情報を削除するかどうか。

    """
    result = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if tz is not None:
        if isinstance(tz, str):
            tz = zoneinfo.ZoneInfo(tz)
        result = result.astimezone(tz)
    if remove_tz:
        result = result.replace(tzinfo=None)
    return result
