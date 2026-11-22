__lazy_modules__ = ["pathlib", "pytilpack.http", "pytilpack.i18n", "starlette.datastructures", "starlette.types"]

import pathlib

import starlette.datastructures
import starlette.types

import pytilpack.http
import pytilpack.i18n

__all__ = ["I18nMiddleware", "init_app"]


class I18nMiddleware:
    def __init__(self, app: starlette.types.ASGIApp, state: pytilpack.i18n.I18nState) -> None:
        self.app = app
        self.state = state

    async def __call__(
        self,
        scope: starlette.types.Scope,
        receive: starlette.types.Receive,
        send: starlette.types.Send,
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        headers = starlette.datastructures.Headers(scope=scope)
        accept_lang = headers.get("accept-language", "")
        locale = pytilpack.http.select_accept_language(
            accept_lang,
            self.state.supported_locales,
            default=self.state.default_locale,
        )
        tokens = pytilpack.i18n.activate(self.state, locale)
        try:
            await self.app(scope, receive, send)
        finally:
            pytilpack.i18n.deactivate(tokens)


def init_app(
    app: starlette.types.ASGIApp,
    locale_dir: str | pathlib.Path,
    domain: str = "messages",
    supported_locales: list[str] | None = None,
    default_locale: str = "en",
    fallback: bool = True,
) -> I18nMiddleware:
    state = pytilpack.i18n.I18nState(
        locale_dir=locale_dir,
        domain=domain,
        locales=supported_locales,
        default_locale=default_locale,
        fallback=fallback,
    )
    return I18nMiddleware(app, state)
