"""Quart-Auth関連のユーティリティ。"""

import functools
import inspect
import logging
import typing

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
    def is_authenticated(self) -> bool:
        """認証済みかどうか。"""
        return False


UserType = typing.TypeVar("UserType", bound=UserMixin)


class QuartAuth[UserType](quart_auth.QuartAuth):
    """Quart-Authの独自拡張。

    Flask-Loginのように@auth_manager.user_loaderを定義できるようにする。
    読み込んだユーザーインスタンスは quart.g.quart_auth_current_user に格納する。
    テンプレートでも {{ current_user }} でアクセスできるようにする。

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_loader_func: typing.Callable[[str], UserType | None] | None = None

    @typing.override
    def init_app(self, app: quart.Quart) -> None:
        """初期化処理。"""
        super().init_app(app)

        # リクエスト前処理を登録
        app.before_request(self._before_request)

    async def _before_request(self) -> None:
        """リクエスト前処理。"""
        quart.g.quart_auth_current_user = None

    @typing.override
    def _template_context(self) -> dict[str, quart_auth.AuthUser]:
        """テンプレートでcurrent_userがquart.g.quart_auth_current_userになるようにする。"""
        template_context = super()._template_context()
        assert "current_user" in template_context
        template_context["current_user"] = self.current_user  # type: ignore[assignment]
        return template_context

    def user_loader(self, user_loader: typing.Callable[[str], UserType | None]) -> typing.Callable[[str], UserType | None]:
        """ユーザーローダーのデコレータ。"""
        self.user_loader_func = user_loader
        return user_loader

    @property
    def current_user(self) -> UserType | AnonymousUser:
        """現在のユーザーを取得する。"""
        # ユーザーがロード済みの場合はそれを返す
        if quart.g.quart_auth_current_user is not None:
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
                quart_auth.renew_login()

        return quart.g.quart_auth_current_user


def reset_user(user: UserMixin) -> None:
    """現在のユーザーをリセットする。DBのセッション切れ対策など用。

    無理やりquart.gに設定するだけなので要注意。
    """
    quart.g.quart_auth_current_user = user


def login_user(auth_id: str, remember: bool = True, set_cookie: bool = True) -> None:
    """ログイン処理。

    Args:
        auth_id: 認証ID
        remember: ログイン状態を保持するかどうか
        set_cookie: 通常のCookie発行を行うか否か (APIキー認証などを自前でした場合はFalseにする)

    """
    user = quart_auth.AuthUser(auth_id)
    if set_cookie:
        # Action.WRITE / Action.WRITE_PERMANENTで設定される
        quart_auth.login_user(user, remember=remember)
    else:
        # 無理やりAction.PASSのまま設定する
        assert user.action == quart_auth.Action.PASS
        _find_extension().login_user(user)


def logout_user() -> None:
    """ログアウト処理。"""
    quart_auth.logout_user()


def is_authenticated() -> bool:
    """ユーザー認証済みかどうかを取得する。"""
    return quart_auth.current_user.auth_id is not None


def current_user() -> UserMixin:
    """現在のユーザーを取得する。"""
    return _find_extension().current_user


def is_admin(attr_name: str = "is_admin") -> bool:
    """現在のユーザーが認証済みかつ管理者であるか否かを取得する。

    Args:
        attr_name: 管理者かどうかを判定する属性名。デフォルトは "is_admin"。
    """
    return is_authenticated() and getattr(current_user(), attr_name)


def admin_only[**P, R](func: typing.Callable[P, R]) -> typing.Callable[P, R]:
    """管理者のみアクセス可能なルートを定義するデコレータ。"""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if not is_admin():
                quart.abort(403)
            return await func(*args, **kwargs)

        return async_wrapper  # type: ignore[return-value]

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not is_admin():
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
