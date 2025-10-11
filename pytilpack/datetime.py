"""datetime関連。"""

import dataclasses
import datetime
import zoneinfo


def fromiso(iso_str: str, tz: zoneinfo.ZoneInfo | str | None = None, remove_tz: bool = False) -> datetime.datetime:
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


def toutc(dt: datetime.datetime) -> datetime.datetime:
    """UTCのdatetimeオブジェクトに変換する。

    Args:
        dt (datetime.datetime): 変換するdatetimeオブジェクト。

    Returns:
        datetime.datetime: UTCのdatetimeオブジェクト。

    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
    return dt.astimezone(zoneinfo.ZoneInfo("UTC"))


@dataclasses.dataclass(frozen=True)
class YearMonth:
    """年月を表すクラス。"""

    year: int
    month: int

    @property
    def is_valid(self) -> bool:
        """正しい日付なのか否かを返す。"""
        try:
            _ = self.this_month
            return True
        except ValueError:
            return False

    @property
    def prev_month(self) -> datetime.date:
        """前月の1日を返す。"""
        if not self.is_valid:
            raise ValueError("Invalid date")
        if self.month == 1:
            return datetime.date(self.year - 1, 12, 1)
        else:
            return datetime.date(self.year, self.month - 1, 1)

    @property
    def this_month(self) -> datetime.date:
        """当該月の1日を返す。"""
        return datetime.date(self.year, self.month, 1)

    @property
    def next_month(self) -> datetime.date:
        """次の月の1日を返す。"""
        if not self.is_valid:
            raise ValueError("Invalid date")
        if self.month == 12:
            return datetime.date(self.year + 1, 1, 1)
        else:
            return datetime.date(self.year, self.month + 1, 1)


@dataclasses.dataclass(frozen=True)
class YearMonthDay:
    """年月日を表すクラス。"""

    year: int
    month: int
    day: int

    @property
    def is_valid(self) -> bool:
        """正しい日付なのか否かを返す。"""
        try:
            _ = self.this_day
            return True
        except ValueError:
            return False

    @property
    def prev_day(self) -> datetime.date:
        """前日を返す。"""
        if not self.is_valid:
            raise ValueError("Invalid date")
        return self.this_day - datetime.timedelta(days=1)

    @property
    def this_day(self) -> datetime.date:
        """当該日を返す。"""
        return datetime.date(self.year, self.month, self.day)

    @property
    def next_day(self) -> datetime.date:
        """翌日を返す。"""
        if not self.is_valid:
            raise ValueError("Invalid date")
        return self.this_day + datetime.timedelta(days=1)
