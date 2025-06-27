"""datetime_のテストコード。"""

import datetime
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
            datetime.datetime(2023, 12, 25, 10, 30, 0),
        ),
        (
            "2023-12-25T10:30:00.123456",
            None,
            False,
            datetime.datetime(2023, 12, 25, 10, 30, 0, 123456),
        ),
        # UTC表記（Z）
        (
            "2023-12-25T10:30:00Z",
            None,
            False,
            datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=datetime.UTC),
        ),
        # タイムゾーン付き
        (
            "2023-12-25T10:30:00+09:00",
            None,
            False,
            datetime.datetime(
                2023,
                12,
                25,
                10,
                30,
                0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=9)),
            ),
        ),
        # タイムゾーン変換（文字列指定）
        (
            "2023-12-25T10:30:00+00:00",
            "Asia/Tokyo",
            False,
            datetime.datetime(
                2023, 12, 25, 19, 30, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Tokyo")
            ),
        ),
        # タイムゾーン変換（ZoneInfo指定）
        (
            "2023-12-25T10:30:00+00:00",
            zoneinfo.ZoneInfo("America/New_York"),
            False,
            datetime.datetime(
                2023, 12, 25, 5, 30, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")
            ),
        ),
        # タイムゾーン情報を削除
        (
            "2023-12-25T10:30:00+09:00",
            None,
            True,
            datetime.datetime(2023, 12, 25, 10, 30, 0),
        ),
        (
            "2023-12-25T10:30:00Z",
            "Asia/Tokyo",
            True,
            datetime.datetime(2023, 12, 25, 19, 30, 0),
        ),
    ],
)
def test_fromiso(
    iso_str: str,
    tz: zoneinfo.ZoneInfo | str | None,
    remove_tz: bool,
    expected: datetime.datetime,
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
