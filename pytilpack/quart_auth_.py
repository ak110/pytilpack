"""Quart-Auth関連のユーティリティ。"""

import typing

import quart
import quart_auth


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


class QuartAuth(typing.Generic[UserType], quart_auth.QuartAuth):
    """Quart-Authの独自拡張。

    Flask-Loginのように@auth_manager.user_loaderを定義できるようにする。
    読み込んだユーザーインスタンスは quart.g.current_user に格納する。
    テンプレートでも {{ current_user }} でアクセスできるようにする。

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_loader_func: (
            typing.Callable[[str], typing.Awaitable[UserType | None]] | None
        ) = None

    @typing.override
    def init_app(self, app: quart.Quart) -> None:
        """初期化処理。"""
        super().init_app(app)

        # リクエスト前処理を登録
        app.before_request(self._before_request)

    def user_loader(
        self, user_loader: typing.Callable[[str], typing.Awaitable[UserType | None]]
    ) -> typing.Callable[[str], typing.Awaitable[UserType | None]]:
        """ユーザーローダーのデコレータ。"""
        self.user_loader_func = user_loader
        return user_loader

    async def _before_request(self) -> None:
        """リクエスト前処理。user_loader_funcを実行する。"""
        assert self.user_loader_func is not None
        if await quart_auth.current_user.is_authenticated:
            # 認証済みの場合はuser_loader_funcを実行する
            auth_id = quart_auth.current_user.auth_id
            assert auth_id is not None
            quart.g.current_user = await self.user_loader_func(auth_id)
            if quart.g.current_user is None:
                # ユーザーが見つからない場合はAnonymousUserにする
                quart.g.current_user = AnonymousUser()
            else:
                # ログイン状態を更新する
                quart_auth.renew_login()
        else:
            # 未認証の場合はAnonymousUserにする
            quart.g.current_user = AnonymousUser()

    @typing.override
    def _template_context(self) -> dict[str, quart_auth.AuthUser]:
        """テンプレートでcurrent_userがquart.g.current_userになるようにする。"""
        template_context = super()._template_context()
        assert "current_user" in template_context
        template_context["current_user"] = quart.g.current_user
        return template_context


def login_user(auth_id: str, remember: bool = True) -> None:
    """ログイン処理。

    Args:
        auth_id: 認証ID
        remember: ログイン状態を保持するかどうか

    """
    quart_auth.login_user(quart_auth.AuthUser(auth_id), remember=remember)


def logout_user() -> None:
    """ログアウト処理。"""
    quart_auth.logout_user()


def current_user() -> UserMixin:
    """現在のユーザーを取得する。"""
    return quart.g.current_user
