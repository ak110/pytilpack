__lazy_modules__ = ["babel.dates", "babel.numbers", "datetime", "decimal", "pytilpack.i18n"]

import datetime  # noqa: ICN001  # 公開関数format_datetimeの引数名dtと衝突するため別名にしない
import decimal

import babel.dates
import babel.numbers

import pytilpack.i18n


def format_date(  # pylint: disable=redefined-builtin
    date: datetime.date | None = None,
    format: str = "medium",
    locale: str | None = None,
) -> str:
    return babel.dates.format_date(date, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_datetime(  # pylint: disable=redefined-builtin
    dt: datetime.datetime | None = None,
    format: str = "medium",
    locale: str | None = None,
    tzinfo: datetime.tzinfo | None = None,
) -> str:
    return babel.dates.format_datetime(dt, format=format, tzinfo=tzinfo, locale=locale or pytilpack.i18n.get_locale())


def format_time(  # pylint: disable=redefined-builtin
    time: datetime.time | None = None,
    format: str = "medium",
    locale: str | None = None,
) -> str:
    return babel.dates.format_time(time, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_number(
    number: int | float | decimal.Decimal,
    locale: str | None = None,
) -> str:
    return babel.numbers.format_decimal(number, locale=locale or pytilpack.i18n.get_locale())


def format_decimal(  # pylint: disable=redefined-builtin
    number: int | float | decimal.Decimal,
    format: str | None = None,
    locale: str | None = None,
) -> str:
    return babel.numbers.format_decimal(number, format=format, locale=locale or pytilpack.i18n.get_locale())


def format_currency(  # pylint: disable=redefined-builtin
    number: int | float | decimal.Decimal,
    currency: str,
    locale: str | None = None,
    format: str | None = None,
) -> str:
    return babel.numbers.format_currency(
        number,
        currency,
        format=format,
        locale=locale or pytilpack.i18n.get_locale(),
    )


def format_percent(  # pylint: disable=redefined-builtin
    number: int | float | decimal.Decimal,
    format: str | None = None,
    locale: str | None = None,
) -> str:
    return babel.numbers.format_percent(number, format=format, locale=locale or pytilpack.i18n.get_locale())
