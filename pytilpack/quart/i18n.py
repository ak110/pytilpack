__lazy_modules__ = ["pathlib", "pytilpack.http", "pytilpack.i18n", "quart"]

import pathlib

import quart

import pytilpack.http
import pytilpack.i18n

__all__ = ["init_app"]


def init_app(
    app: quart.Quart,
    locale_dir: str | pathlib.Path,
    domain: str = "messages",
    supported_locales: list[str] | None = None,
    default_locale: str = "en",
    fallback: bool = True,
) -> None:
    state = pytilpack.i18n.I18nState(
        locale_dir=locale_dir,
        domain=domain,
        locales=supported_locales,
        default_locale=default_locale,
        fallback=fallback,
    )
    app.extensions["pytilpack_i18n"] = state

    app.jinja_env.globals["_"] = pytilpack.i18n.gettext_func
    app.jinja_env.globals["ngettext"] = pytilpack.i18n.ngettext

    @app.before_request
    async def _set_locale_from_request() -> None:
        i18n_state: pytilpack.i18n.I18nState = app.extensions["pytilpack_i18n"]
        accept_lang = quart.request.headers.get("Accept-Language", "")
        locale = pytilpack.http.select_accept_language(
            accept_lang,
            i18n_state.supported_locales,
            default=i18n_state.default_locale,
        )
        quart.g.pytilpack_i18n_tokens = pytilpack.i18n.activate(i18n_state, locale)

    @app.teardown_request
    async def _teardown_locale(exc: BaseException | None) -> None:
        del exc  # noqa
        if hasattr(quart.g, "pytilpack_i18n_tokens"):
            pytilpack.i18n.deactivate(quart.g.pytilpack_i18n_tokens)
