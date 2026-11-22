__lazy_modules__ = ["contextvars", "gettext", "logging", "pathlib"]

import contextvars
import gettext
import logging
import pathlib

logger = logging.getLogger(__name__)

_current_state: contextvars.ContextVar["I18nState | None"] = contextvars.ContextVar("_current_state", default=None)
_current_locale: contextvars.ContextVar[str] = contextvars.ContextVar("_current_locale", default="en")


class I18nState:
    def __init__(
        self,
        locale_dir: str | pathlib.Path,
        domain: str = "messages",
        locales: list[str] | None = None,
        default_locale: str = "en",
        fallback: bool = True,
    ) -> None:
        self.locale_dir = pathlib.Path(locale_dir)
        self.domain = domain
        self.default_locale = default_locale
        self.fallback = fallback
        if locales is not None:
            self.supported_locales = list(locales)
        else:
            self.supported_locales = _detect_locales(self.locale_dir)
        self.translations: dict[str, gettext.GNUTranslations | gettext.NullTranslations] = {}
        for locale in self.supported_locales:
            self.translations[locale] = _load_translations(self.locale_dir, self.domain, locale, self.fallback)
        logger.info(f"i18n初期化完了: domain={domain}, locales={self.supported_locales}")

    def get_translations(self, locale: str) -> gettext.GNUTranslations | gettext.NullTranslations:
        if locale in self.translations:
            return self.translations[locale]
        return gettext.NullTranslations()


def get_state() -> I18nState:
    state = _current_state.get()
    if state is None:
        raise RuntimeError("I18nStateが未設定です。activate()またはフレームワーク統合のinit_app()を呼んでください。")
    return state


def is_active() -> bool:
    return _current_state.get() is not None


def get_locale() -> str:
    return _current_locale.get()


def set_locale(locale: str) -> None:
    _current_locale.set(locale)


def activate(
    state: I18nState, locale: str | None = None
) -> tuple[contextvars.Token["I18nState | None"], contextvars.Token[str]]:
    state_token = _current_state.set(state)
    locale_token = _current_locale.set(locale or state.default_locale)
    return state_token, locale_token


def deactivate(
    tokens: tuple[contextvars.Token["I18nState | None"], contextvars.Token[str]],
) -> None:
    state_token, locale_token = tokens
    _current_state.reset(state_token)
    _current_locale.reset(locale_token)


def gettext_func(message: str) -> str:
    return get_state().get_translations(get_locale()).gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    return get_state().get_translations(get_locale()).ngettext(singular, plural, n)


def pgettext(context: str, message: str) -> str:
    return get_state().get_translations(get_locale()).pgettext(context, message)


def npgettext(context: str, singular: str, plural: str, n: int) -> str:
    return get_state().get_translations(get_locale()).npgettext(context, singular, plural, n)


_ = gettext_func


def _detect_locales(locale_dir: pathlib.Path) -> list[str]:
    locales: list[str] = []
    if not locale_dir.is_dir():
        return locales
    for entry in sorted(locale_dir.iterdir()):
        if entry.is_dir() and (entry / "LC_MESSAGES").is_dir():
            locales.append(entry.name)
    return locales


def _load_translations(
    locale_dir: pathlib.Path,
    domain: str,
    locale: str,
    fallback: bool,
) -> gettext.GNUTranslations | gettext.NullTranslations:
    return gettext.translation(
        domain,
        localedir=str(locale_dir),
        languages=[locale],
        fallback=fallback,
    )
