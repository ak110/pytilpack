__lazy_modules__ = ["dataclasses", "datetime", "zoneinfo"]

import dataclasses
import datetime  # noqa: ICN001  # 公開関数toutcの引数名dtと衝突するため別名にしない
import zoneinfo


def fromiso(iso_str: str, tz: zoneinfo.ZoneInfo | str | None = None, remove_tz: bool = False) -> datetime.datetime:
    result = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if tz is not None:
        if isinstance(tz, str):
            tz = zoneinfo.ZoneInfo(tz)
        result = result.astimezone(tz)
    if remove_tz:
        result = result.replace(tzinfo=None)
    return result


def toutc(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
    return dt.astimezone(zoneinfo.ZoneInfo("UTC"))


@dataclasses.dataclass(frozen=True)
class YearMonth:
    year: int
    month: int

    @property
    def is_valid(self) -> bool:
        try:
            _ = self.this_month
            return True
        except ValueError:
            return False

    def _invalid_message(self) -> str:
        return (
            f"Invalid date: year={self.year}, month={self.month}."
            f" Specify month in 1-12 and year in {datetime.MINYEAR}-{datetime.MAXYEAR}."
        )

    @property
    def prev_month(self) -> datetime.date:
        if not self.is_valid:
            raise ValueError(self._invalid_message())
        if self.month == 1:
            return datetime.date(self.year - 1, 12, 1)
        else:
            return datetime.date(self.year, self.month - 1, 1)

    @property
    def this_month(self) -> datetime.date:
        return datetime.date(self.year, self.month, 1)

    @property
    def next_month(self) -> datetime.date:
        if not self.is_valid:
            raise ValueError(self._invalid_message())
        if self.month == 12:
            return datetime.date(self.year + 1, 1, 1)
        else:
            return datetime.date(self.year, self.month + 1, 1)


@dataclasses.dataclass(frozen=True)
class YearMonthDay:
    year: int
    month: int
    day: int

    @property
    def is_valid(self) -> bool:
        try:
            _ = self.this_day
            return True
        except ValueError:
            return False

    def _invalid_message(self) -> str:
        return (
            f"Invalid date: year={self.year}, month={self.month}, day={self.day}."
            f" Specify an existing date (month 1-12, day within the month, year {datetime.MINYEAR}-{datetime.MAXYEAR})."
        )

    @property
    def prev_day(self) -> datetime.date:
        if not self.is_valid:
            raise ValueError(self._invalid_message())
        return self.this_day - datetime.timedelta(days=1)

    @property
    def this_day(self) -> datetime.date:
        return datetime.date(self.year, self.month, self.day)

    @property
    def next_day(self) -> datetime.date:
        if not self.is_valid:
            raise ValueError(self._invalid_message())
        return self.this_day + datetime.timedelta(days=1)
