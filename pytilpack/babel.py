"""Babel関連。"""

import datetime
import decimal

import babel.dates
import babel.numbers

import pytilpack.i18n


def format_date(
    date: datetime.date | None = None,
    format: str = "medium",
    locale: str | None = None,
) -> str:
    """日付をロケールに応じてフォーマットする。

    Args:
        date: フォーマットする日付。Noneの場合は本日。
        format: フォーマット種別 ("short", "medium", "long", "full" またはパターン文字列)
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。

    """
    return babel.dates.format_date(date, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_datetime(
    dt: datetime.datetime | None = None,
    format: str = "medium",
    locale: str | None = None,
    tzinfo: datetime.tzinfo | None = None,
) -> str:
    """日時をロケールに応じてフォーマットする。

    Args:
        dt: フォーマットする日時。Noneの場合は現在日時。
        format: フォーマット種別 ("short", "medium", "long", "full" またはパターン文字列)
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。
        tzinfo: タイムゾーン情報。

    """
    return babel.dates.format_datetime(dt, format=format, tzinfo=tzinfo, locale=locale or pytilpack.i18n.get_locale())


def format_time(
    time: datetime.time | None = None,
    format: str = "medium",
    locale: str | None = None,
) -> str:
    """時刻をロケールに応じてフォーマットする。

    Args:
        time: フォーマットする時刻。Noneの場合は現在時刻。
        format: フォーマット種別 ("short", "medium", "long", "full" またはパターン文字列)
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。

    """
    return babel.dates.format_time(time, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_number(
    number: int | float | decimal.Decimal,
    locale: str | None = None,
) -> str:
    """数値をロケールに応じてフォーマットする。

    Args:
        number: フォーマットする数値。
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。

    """
    return babel.numbers.format_decimal(number, locale=locale or pytilpack.i18n.get_locale())


def format_decimal(
    number: int | float | decimal.Decimal,
    format: str | None = None,
    locale: str | None = None,
) -> str:
    """小数をロケールに応じてフォーマットする。

    Args:
        number: フォーマットする数値。
        format: カスタムフォーマットパターン。
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。

    """
    return babel.numbers.format_decimal(number, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_currency(
    number: int | float | decimal.Decimal,
    currency: str,
    locale: str | None = None,
    format: str | None = None,
) -> str:
    """通貨をロケールに応じてフォーマットする。

    Args:
        number: フォーマットする数値。
        currency: 通貨コード（例: "USD", "JPY"）。
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。
        format: カスタムフォーマットパターン。

    """
    return babel.numbers.format_currency(
        number,
        currency,
        format=format,
        locale=locale or pytilpack.i18n.get_locale(),
    )


def format_percent(
    number: int | float | decimal.Decimal,
    format: str | None = None,
    locale: str | None = None,
) -> str:
    """パーセントをロケールに応じてフォーマットする。

    Args:
        number: フォーマットする数値（0.5 = 50%）。
        format: カスタムフォーマットパターン。
        locale: ロケール。Noneの場合はi18n.get_locale()を使用。

    """
    return babel.numbers.format_percent(number, format=format, locale=locale or pytilpack.i18n.get_locale())
