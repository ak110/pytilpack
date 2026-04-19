"""FastAPI用i18n統合。"""

import pathlib

import starlette.datastructures
import starlette.types

import pytilpack.http
import pytilpack.i18n

__all__ = ["I18nMiddleware", "init_app"]


class I18nMiddleware:
    """Accept-Languageからロケールを自動設定するASGIミドルウェア。"""

    def __init__(self, app: starlette.types.ASGIApp, state: pytilpack.i18n.I18nState) -> None:
        self.app = app
        self.state = state

    async def __call__(
        self,
        scope: starlette.types.Scope,
        receive: starlette.types.Receive,
        send: starlette.types.Send,
    ) -> None:
        """ASGIインターフェース。"""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        # Accept-Languageからロケールを決定
        headers = starlette.datastructures.Headers(scope=scope)
        accept_lang = headers.get("accept-language", "")
        locale = pytilpack.http.select_accept_language(
            accept_lang,
            self.state.supported_locales,
            default=self.state.default_locale,
        )
        # activate → try/finally → deactivate でリクエストスコープに閉じ込める
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
    """FastAPI/Starletteアプリにi18nを統合する。

    Args:
        app: FastAPI/Starletteアプリ
        locale_dir: localeディレクトリのパス
        domain: gettextドメイン名
        supported_locales: サポートするロケール一覧
        default_locale: デフォルトロケール
        fallback: フォールバック有無

    Returns:
        I18nMiddlewareインスタンス（app.add_middlewareを使う場合はこの関数ではなく
        直接I18nMiddlewareを使用する）

    """
    state = pytilpack.i18n.I18nState(
        locale_dir=locale_dir,
        domain=domain,
        locales=supported_locales,
        default_locale=default_locale,
        fallback=fallback,
    )
    return I18nMiddleware(app, state)
