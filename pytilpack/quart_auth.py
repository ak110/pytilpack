__lazy_modules__ = ["functools", "inspect", "logging", "pytilpack.python", "quart", "quart_auth", "typing"]

import functools
import inspect
import logging
import typing

import quart
import quart_auth

import pytilpack.python

logger = logging.getLogger(__name__)


class UserMixin:
    @property
    def is_authenticated(self) -> bool:
        return True


class AnonymousUser(UserMixin):
    @property
    @typing.override
    def is_authenticated(self) -> bool:
        return False


class QuartAuth[UserType: UserMixin](quart_auth.QuartAuth):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_loader_func: typing.Callable[[str], UserType | None] | None = None
        self.auser_loader_func: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]] | None = None

    @typing.override
    def init_app(self, app: quart.Quart) -> None:
        super().init_app(app)

        app.before_request(self._before_request)

    async def _before_request(self) -> None:
        quart.g.quart_auth_current_user = None

    # pylint: disable=invalid-overridden-method
    # pyright: ignore[reportIncompatibleMethodOverride]
    @typing.override
    async def _template_context(self) -> dict[str, quart_auth.AuthUser]:  # type: ignore[override]
        try:
            await self.ensure_user_loaded()
            template_context = super()._template_context()
            assert "current_user" in template_context
            template_context["current_user"] = self.current_user  # type: ignore[assignment]
            return template_context
        except Exception:
            logger.warning(
                "テンプレートコンテキストのユーザーロードに失敗しました。current_userをAnonymousUserとして描画を続ける。"
                "原因は付記した例外を参照し、user_loaderの実装を見直す",
                exc_info=True,
            )
            return {"current_user": AnonymousUser()}  # type: ignore[dict-item]

    @typing.overload
    def user_loader(self, user_loader: typing.Callable[[str], UserType | None]) -> typing.Callable[[str], UserType | None]:
        pass

    @typing.overload
    def user_loader(
        self, user_loader: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]]
    ) -> typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]]:
        pass

    def user_loader(
        self,
        user_loader: typing.Callable[[str], UserType | None]
        | typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]],
    ) -> (
        typing.Callable[[str], UserType | None]
        | typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]]
    ):
        if inspect.iscoroutinefunction(user_loader):
            self.user_loader_func = None
            self.auser_loader_func = typing.cast(
                typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]], user_loader
            )
        else:
            self.user_loader_func = typing.cast(typing.Callable[[str], UserType | None], user_loader)
            self.auser_loader_func = None
        return user_loader

    async def ensure_user_loaded(self) -> UserType | AnonymousUser:
        if getattr(quart.g, "quart_auth_current_user", None) is not None:
            return quart.g.quart_auth_current_user

        auth_id = quart_auth.current_user.auth_id
        if auth_id is None:
            quart.g.quart_auth_current_user = AnonymousUser()
        elif self.auser_loader_func is not None:
            quart.g.quart_auth_current_user = await self.auser_loader_func(auth_id)
        elif self.user_loader_func is not None:
            quart.g.quart_auth_current_user = self.user_loader_func(auth_id)
        else:
            raise RuntimeError("user_loaderが設定されていません。@auth_manager.user_loaderでユーザーを読み込む関数を登録する")

        return self._finish_user_load(auth_id)

    def _finish_user_load(self, auth_id: str | None) -> UserType | AnonymousUser:
        if auth_id is not None and quart.g.quart_auth_current_user is None:
            logger.error(
                f"ユーザーロードエラー: {auth_id}。user_loaderがNoneを返したため、ログアウトして未認証として処理を続ける。"
                "ユーザーが削除されていないか、user_loaderの実装を確かめる"
            )
            quart.g.quart_auth_current_user = AnonymousUser()
            quart_auth.logout_user()
        elif auth_id is not None and getattr(quart.g, "quart_auth_set_cookie", True):
            quart_auth.renew_login()

        return quart.g.quart_auth_current_user  # pyright: ignore[reportReturnType]

    @property
    def current_user(self) -> UserType | AnonymousUser:
        if getattr(quart.g, "quart_auth_current_user", None) is not None:
            return quart.g.quart_auth_current_user

        assert self.user_loader_func is not None
        auth_id = quart_auth.current_user.auth_id
        if auth_id is None:
            quart.g.quart_auth_current_user = AnonymousUser()
        else:
            assert auth_id is not None
            quart.g.quart_auth_current_user = self.user_loader_func(auth_id)
        return self._finish_user_load(auth_id)


def reset_user(user: UserMixin) -> None:
    quart.g.quart_auth_current_user = user


def login_user(auth_id: str, remember: bool = True, set_cookie: bool = True) -> None:
    user = quart_auth.AuthUser(auth_id)
    quart.g.quart_auth_set_cookie = set_cookie
    if set_cookie:
        quart_auth.login_user(user, remember=remember)
    else:
        assert user.action == quart_auth.Action.PASS
        _find_extension().login_user(user)
    quart.g.quart_auth_current_user = None


def logout_user() -> None:
    quart_auth.logout_user()


async def ensure_user_loaded() -> None:
    await _find_extension().ensure_user_loaded()


def is_authenticated() -> bool:
    return quart_auth.current_user.auth_id is not None


@pytilpack.python.deprecated("Use pytilpack.quart_auth.acurrent_user instead.")
def current_user() -> UserMixin:
    return _find_extension().current_user


async def acurrent_user() -> UserMixin:
    return await _find_extension().ensure_user_loaded()


@pytilpack.python.deprecated("Use pytilpack.quart_auth.ais_admin instead.")
def is_admin(attr_name: str = "is_admin") -> bool:
    return is_authenticated() and getattr(_find_extension().current_user, attr_name)


async def ais_admin(attr_name: str = "is_admin") -> bool:
    user = await acurrent_user()
    return user.is_authenticated and getattr(user, attr_name)


def admin_only[**P, R](func: typing.Callable[P, R]) -> typing.Callable[P, R]:
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if not is_authenticated():
                quart.abort(401)
            if not await ais_admin():
                quart.abort(403)
            return await func(*args, **kwargs)

        return typing.cast(typing.Callable[P, R], async_wrapper)

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not is_authenticated():
                quart.abort(401)
            ext = _find_extension()
            if not getattr(ext.current_user, "is_admin", False):
                quart.abort(403)
            return func(*args, **kwargs)

    return sync_wrapper


def _find_extension(app: quart.Quart | None = None) -> QuartAuth:
    if app is None:
        app = quart.current_app
    extension = typing.cast(
        QuartAuth | None,
        next(
            (extension for extension in app.extensions["QUART_AUTH"] if extension.singleton),
            None,
        ),
    )
    assert extension is not None
    return extension
