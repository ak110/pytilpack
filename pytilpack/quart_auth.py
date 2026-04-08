"""Quart-Auth関連のユーティリティ。"""

import functools
import inspect
import logging
import typing
import warnings

import quart
import quart_auth

logger = logging.getLogger(__name__)


class UserMixin:
    """ユーザー。"""

    @property
    def is_authenticated(self) -> bool:
        """認証済みかどうか。"""
        return True


class AnonymousUser(UserMixin):
    """未ログインの匿名ユーザー。"""

    @property
    @typing.override
    def is_authenticated(self) -> bool:
        """認証済みかどうか。"""
        return False


class QuartAuth[UserType: UserMixin](quart_auth.QuartAuth):
    """Quart-Authの独自拡張。

    Flask-Loginのように@auth_manager.user_loaderを定義できるようにする。
    読み込んだユーザーインスタンスは quart.g.quart_auth_current_user に格納する。
    テンプレートでも {{ current_user }} でアクセスできるようにする。

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_loader_func: typing.Callable[[str], UserType | None] | None = None
        self.auser_loader_func: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, UserType | None]] | None = None

    @typing.override
    def init_app(self, app: quart.Quart) -> None:
        """初期化処理。"""
        super().init_app(app)

        # リクエスト前処理を登録
        app.before_request(self._before_request)

    async def _before_request(self) -> None:
        """リクエスト前処理。"""
        quart.g.quart_auth_current_user = None

    # pylint: disable=invalid-overridden-method
    # pyright: ignore[reportIncompatibleMethodOverride]
    @typing.override
    async def _template_context(self) -> dict[str, quart_auth.AuthUser]:  # type: ignore[override]
        """テンプレートでcurrent_userがquart.g.quart_auth_current_userになるようにする。"""
        try:
            await self.ensure_user_loaded()
            template_context = super()._template_context()
            assert "current_user" in template_context
            template_context["current_user"] = self.current_user  # type: ignore[assignment]
            return template_context
        except Exception:
            logger.warning("テンプレートコンテキストのユーザーロードに失敗しました", exc_info=True)
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
        """ユーザーローダーのデコレータ。"""
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
        """ユーザーをロードする。sync/async両方のuser_loaderに対応。"""
        if getattr(quart.g, "quart_auth_current_user", None) is not None:
            return quart.g.quart_auth_current_user

        # ユーザーの読み込みを行う
        auth_id = quart_auth.current_user.auth_id
        if auth_id is None:
            # 未認証の場合はAnonymousUserにする
            quart.g.quart_auth_current_user = AnonymousUser()
        elif self.auser_loader_func is not None:
            # async版loaderで読み込む
            quart.g.quart_auth_current_user = await self.auser_loader_func(auth_id)
        elif self.user_loader_func is not None:
            # sync版loaderで読み込む
            quart.g.quart_auth_current_user = self.user_loader_func(auth_id)
        else:
            raise RuntimeError("user_loaderが設定されていません")

        if auth_id is not None and quart.g.quart_auth_current_user is None:
            # ユーザーが見つからない場合はAnonymousUserにする
            logger.error(f"ユーザーロードエラー: {auth_id}")
            quart.g.quart_auth_current_user = AnonymousUser()
            quart_auth.logout_user()
        elif auth_id is not None:
            # ログイン状態を更新する
            if getattr(quart.g, "quart_auth_set_cookie", True):
                quart_auth.renew_login()

        # ロジック上、ここでNoneになることはない (未認証→AnonymousUser, ロード失敗→AnonymousUser)
        return quart.g.quart_auth_current_user  # pyright: ignore[reportReturnType]

    @property
    def current_user(self) -> UserType | AnonymousUser:
        """現在のユーザーを取得する。"""
        # ユーザーがロード済みの場合はそれを返す
        if getattr(quart.g, "quart_auth_current_user", None) is not None:
            return quart.g.quart_auth_current_user

        # ユーザーの読み込みを行う
        assert self.user_loader_func is not None
        auth_id = quart_auth.current_user.auth_id
        if auth_id is None:
            # 未認証の場合はAnonymousUserにする
            quart.g.quart_auth_current_user = AnonymousUser()
        else:
            # 認証済みの場合はuser_loader_funcを実行する
            assert auth_id is not None
            quart.g.quart_auth_current_user = self.user_loader_func(auth_id)
            if quart.g.quart_auth_current_user is None:
                # ユーザーが見つからない場合はAnonymousUserにする
                logger.error(f"ユーザーロードエラー: {auth_id}")
                quart.g.quart_auth_current_user = AnonymousUser()
                quart_auth.logout_user()
            else:
                # ログイン状態を更新する
                if getattr(quart.g, "quart_auth_set_cookie", True):
                    quart_auth.renew_login()

        return quart.g.quart_auth_current_user


def reset_user(user: UserMixin) -> None:
    """現在のユーザーをリセットする。DBのセッション切れ対策などに使用する。

    quart.gに直接設定するだけの処理のため、利用時は注意する。
    """
    quart.g.quart_auth_current_user = user


def login_user(auth_id: str, remember: bool = True, set_cookie: bool = True) -> None:
    """ログイン処理。

    Args:
        auth_id: 認証ID
        remember: ログイン状態を保持するかどうか
        set_cookie: 通常のCookie発行を行うか否か (APIキー認証等を自前で実装した場合はFalseにする)

    """
    user = quart_auth.AuthUser(auth_id)
    quart.g.quart_auth_set_cookie = set_cookie
    if set_cookie:
        # Action.WRITE / Action.WRITE_PERMANENTで設定される
        quart_auth.login_user(user, remember=remember)
    else:
        # Action.PASSのまま直接設定する
        assert user.action == quart_auth.Action.PASS
        _find_extension().login_user(user)
    # ユーザーは再ロード要
    quart.g.quart_auth_current_user = None


def logout_user() -> None:
    """ログアウト処理。"""
    quart_auth.logout_user()


async def ensure_user_loaded() -> None:
    """ユーザーをロードする。async版のuser_loaderを使用している場合はこの関数の呼び出しが必要である。"""
    await _find_extension().ensure_user_loaded()


def is_authenticated() -> bool:
    """ユーザー認証済みかどうかを取得する。"""
    return quart_auth.current_user.auth_id is not None


def current_user() -> UserMixin:
    """現在のユーザーを取得する。

    .. deprecated:: acurrent_user() を使用すること。
    """
    warnings.warn(
        "current_user()は非推奨です。acurrent_user()を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    return _find_extension().current_user


async def acurrent_user() -> UserMixin:
    """現在のユーザーを取得する。async版。"""
    return await _find_extension().ensure_user_loaded()


def is_admin(attr_name: str = "is_admin") -> bool:
    """現在のユーザーが認証済みかつ管理者であるか否かを取得する。

    .. deprecated:: ais_admin() を使用すること。

    Args:
        attr_name: 管理者かどうかを判定する属性名。デフォルトは "is_admin"。
    """
    warnings.warn(
        "is_admin()は非推奨です。ais_admin()を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    return is_authenticated() and getattr(_find_extension().current_user, attr_name)


async def ais_admin(attr_name: str = "is_admin") -> bool:
    """現在のユーザーが認証済みかつ管理者であるか否かを取得する。async版。

    Args:
        attr_name: 管理者かどうかを判定する属性名。デフォルトは "is_admin"。
    """
    user = await acurrent_user()
    return user.is_authenticated and getattr(user, attr_name)


def admin_only[**P, R](func: typing.Callable[P, R]) -> typing.Callable[P, R]:
    """管理者のみアクセス可能なルートを定義するデコレータ。"""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if not await ais_admin():
                quart.abort(403)
            return await func(*args, **kwargs)

        return typing.cast(typing.Callable[P, R], async_wrapper)

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ext = _find_extension()
            if not (is_authenticated() and getattr(ext.current_user, "is_admin", False)):
                quart.abort(403)
            return func(*args, **kwargs)

    return sync_wrapper


def _find_extension(app: quart.Quart | None = None) -> QuartAuth:
    """QuartAuthのインスタンスを取得する。"""
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
