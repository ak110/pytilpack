"""datetime_のテストコード。"""

import datetime as dt
import zoneinfo

import pytest

import pytilpack.datetime


@pytest.mark.parametrize(
    "iso_str,tz,remove_tz,expected",
    [
        # 基本的なISO形式
        (
            "2023-12-25T10:30:00",
            None,
            False,
            dt.datetime(2023, 12, 25, 10, 30, 0),
        ),
        (
            "2023-12-25T10:30:00.123456",
            None,
            False,
            dt.datetime(2023, 12, 25, 10, 30, 0, 123456),
        ),
        # 秒無し
        (
            "2023-12-25T10:30",
            None,
            False,
            dt.datetime(2023, 12, 25, 10, 30, 0),
        ),
        # UTC表記（Z）
        (
            "2023-12-25T10:30:00Z",
            None,
            False,
            dt.datetime(2023, 12, 25, 10, 30, 0, tzinfo=dt.UTC),
        ),
        # タイムゾーン付き
        (
            "2023-12-25T10:30:00+09:00",
            None,
            False,
            dt.datetime(
                2023,
                12,
                25,
                10,
                30,
                0,
                tzinfo=dt.timezone(dt.timedelta(hours=9)),
            ),
        ),
        # タイムゾーン変換（文字列指定）
        (
            "2023-12-25T10:30:00+00:00",
            "Asia/Tokyo",
            False,
            dt.datetime(2023, 12, 25, 19, 30, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Tokyo")),
        ),
        # タイムゾーン変換（ZoneInfo指定）
        (
            "2023-12-25T10:30:00+00:00",
            zoneinfo.ZoneInfo("America/New_York"),
            False,
            dt.datetime(2023, 12, 25, 5, 30, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")),
        ),
        # タイムゾーン情報を削除
        (
            "2023-12-25T10:30:00+09:00",
            None,
            True,
            dt.datetime(2023, 12, 25, 10, 30, 0),
        ),
        (
            "2023-12-25T10:30:00Z",
            "Asia/Tokyo",
            True,
            dt.datetime(2023, 12, 25, 19, 30, 0),
        ),
    ],
)
def test_fromiso(
    iso_str: str,
    tz: zoneinfo.ZoneInfo | str | None,
    remove_tz: bool,
    expected: dt.datetime,
) -> None:
    """fromisoのテスト。"""
    actual = pytilpack.datetime.fromiso(iso_str, tz, remove_tz)
    assert actual == expected
    if remove_tz:
        assert actual.tzinfo is None
    elif tz is not None:
        if isinstance(tz, str):
            assert actual.tzinfo == zoneinfo.ZoneInfo(tz)
        else:
            assert actual.tzinfo == tz


@pytest.mark.parametrize(
    "year,month,expected_is_valid,expected_prev,expected_this,expected_next",
    [
        # 正常なケース
        (2023, 1, True, dt.date(2022, 12, 1), dt.date(2023, 1, 1), dt.date(2023, 2, 1)),
        (2023, 6, True, dt.date(2023, 5, 1), dt.date(2023, 6, 1), dt.date(2023, 7, 1)),
        (2023, 12, True, dt.date(2023, 11, 1), dt.date(2023, 12, 1), dt.date(2024, 1, 1)),
        # 年またぎ
        (2023, 1, True, dt.date(2022, 12, 1), dt.date(2023, 1, 1), dt.date(2023, 2, 1)),
        (2022, 12, True, dt.date(2022, 11, 1), dt.date(2022, 12, 1), dt.date(2023, 1, 1)),
        # 異常なケース
        (2023, 0, False, None, None, None),
        (2023, 13, False, None, None, None),
        (2023, -1, False, None, None, None),
    ],
)
def test_year_month(
    year: int,
    month: int,
    expected_is_valid: bool,
    expected_prev: dt.date | None,
    expected_this: dt.date | None,
    expected_next: dt.date | None,
) -> None:
    """YearMonthのテスト。"""
    ym = pytilpack.datetime.YearMonth(year, month)

    assert ym.is_valid == expected_is_valid

    if expected_is_valid:
        assert ym.prev_month == expected_prev
        assert ym.this_month == expected_this
        assert ym.next_month == expected_next
    else:
        # 無効な日付の場合は例外が発生する
        with pytest.raises(ValueError):
            _ = ym.prev_month
        with pytest.raises(ValueError):
            _ = ym.this_month
        with pytest.raises(ValueError):
            _ = ym.next_month


@pytest.mark.parametrize(
    "year,month,day,expected_is_valid,expected_prev,expected_this,expected_next",
    [
        # 正常なケース
        (2023, 1, 1, True, dt.date(2022, 12, 31), dt.date(2023, 1, 1), dt.date(2023, 1, 2)),
        (2023, 6, 15, True, dt.date(2023, 6, 14), dt.date(2023, 6, 15), dt.date(2023, 6, 16)),
        (2023, 12, 31, True, dt.date(2023, 12, 30), dt.date(2023, 12, 31), dt.date(2024, 1, 1)),
        # うるう年
        (2024, 2, 29, True, dt.date(2024, 2, 28), dt.date(2024, 2, 29), dt.date(2024, 3, 1)),
        (2023, 2, 29, False, None, None, None),  # 平年の2月29日は無効
        # 月末チェック
        (2023, 2, 28, True, dt.date(2023, 2, 27), dt.date(2023, 2, 28), dt.date(2023, 3, 1)),
        (2023, 4, 31, False, None, None, None),  # 4月31日は無効
        # 異常なケース
        (2023, 1, 0, False, None, None, None),
        (2023, 1, 32, False, None, None, None),
        (2023, 0, 1, False, None, None, None),
        (2023, 13, 1, False, None, None, None),
    ],
)
def test_year_month_day(
    year: int,
    month: int,
    day: int,
    expected_is_valid: bool,
    expected_prev: dt.date | None,
    expected_this: dt.date | None,
    expected_next: dt.date | None,
) -> None:
    """YearMonthDayのテスト。"""
    ymd = pytilpack.datetime.YearMonthDay(year, month, day)

    assert ymd.is_valid == expected_is_valid

    if expected_is_valid:
        assert ymd.prev_day == expected_prev
        assert ymd.this_day == expected_this
        assert ymd.next_day == expected_next
    else:
        # 無効な日付の場合は例外が発生する
        with pytest.raises(ValueError):
            _ = ymd.prev_day
        with pytest.raises(ValueError):
            _ = ymd.this_day
        with pytest.raises(ValueError):
            _ = ymd.next_day
