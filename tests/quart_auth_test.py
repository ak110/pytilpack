"""Quart-Auth関連のユーティリティのテスト。"""

import typing

import pytest
import pytest_asyncio
import quart
import quart.typing
import quart_auth

import pytilpack.quart
import pytilpack.quart_auth


class User(pytilpack.quart_auth.UserMixin):
    """テスト用ユーザーモデル。"""

    def __init__(self, name: str, is_admin: bool = False) -> None:
        self.name = name
        self.is_admin = is_admin


@pytest.fixture(name="app", scope="module")
def _app() -> quart.Quart:
    """テスト用アプリケーション。"""
    app = quart.Quart(__name__)
    app.secret_key = "secret"  # 暗号化に必要

    # Quart-Authの設定
    auth_manager = pytilpack.quart_auth.QuartAuth[User]()
    auth_manager.init_app(app)

    # ユーザーローダーの設定
    users = {"user1": User("test user"), "admin1": User("admin user", is_admin=True)}

    @auth_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return users.get(user_id)

    assert auth_manager.user_loader_func is not None

    # テスト用ルート
    @app.route("/public")
    async def public():
        return "public page"

    @app.route("/login")
    async def login():
        # ログイン処理
        pytilpack.quart_auth.login_user("user1")
        return "logged in"

    @app.route("/logout")
    async def logout():
        # ログアウト処理
        pytilpack.quart_auth.logout_user()
        return "logged out"

    @app.route("/private")
    @quart_auth.login_required
    async def private():
        return "private page"

    @app.route("/user")
    async def user():
        return await quart.render_template_string(
            "User: {{ current_user.name if current_user.is_authenticated else '<anonymous>' }}"
        )

    @app.route("/admin")
    @pytilpack.quart_auth.admin_only
    async def admin():
        return "admin page"

    @app.route("/admin-sync")
    @pytilpack.quart_auth.admin_only
    def admin_sync():
        return "admin sync page"

    @app.route("/login_admin")
    async def login_admin():
        # 管理者ログイン処理
        pytilpack.quart_auth.login_user("admin1")
        return "admin logged in"

    @app.route("/login_no_cookie")
    async def login_no_cookie():
        # Cookieなしログイン処理
        pytilpack.quart_auth.login_user("user1", set_cookie=False)
        assert pytilpack.quart_auth.is_authenticated(), "直後はログイン済みにはなる"
        return "logged in without cookie"

    return app


@pytest_asyncio.fixture(name="client", scope="function")
async def _client(
    app: quart.Quart,
) -> typing.AsyncGenerator[quart.typing.TestClientProtocol, None]:
    """テスト用クライアント。"""
    async with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_public_access(client: quart.typing.TestClientProtocol) -> None:
    """未ログイン状態でも公開ページにアクセスできる。"""
    response = await client.get("/public")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "public page"


@pytest.mark.asyncio
async def test_private_access_unauthorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    """未ログイン状態で非公開ページにアクセスするとリダイレクトされる。"""
    response = await client.get("/private")
    assert response.status_code == 401  # 未認証


@pytest.mark.asyncio
async def test_private_access_authorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    """ログイン状態で非公開ページにアクセスできる。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        # 非公開ページにアクセス
        response = await client.get("/private")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "private page"


@pytest.mark.asyncio
async def test_current_user_anonymous(client: quart.typing.TestClientProtocol) -> None:
    """未ログイン状態ではcurrent_userが匿名ユーザーになる。"""
    response = await client.get("/user")
    text = await response.get_data(as_text=True)
    assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_current_user_authenticated(
    client: quart.typing.TestClientProtocol,
) -> None:
    """ログイン状態ではcurrent_userが認証済みユーザーになる。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: test user"


@pytest.mark.asyncio
async def test_logout(client: quart.typing.TestClientProtocol) -> None:
    """ログアウト後はcurrent_userが匿名ユーザーに戻る。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        # ログアウト
        response = await client.get("/logout")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged out"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_admin_only(client: quart.typing.TestClientProtocol) -> None:
    # 未認証状態でadmin_onlyデコレータ付きの非同期関数にアクセスすると403エラー。
    response = await client.get("/admin")
    assert response.status_code == 403

    # 未認証状態でadmin_onlyデコレータ付きの同期関数にアクセスすると403エラー。
    response = await client.get("/admin-sync")
    assert response.status_code == 403

    # 一般ユーザーでadmin_onlyデコレータ付きの非同期関数にアクセスすると403エラー。
    async with client.session_transaction():
        # 一般ユーザーでログイン
        response = await client.get("/login")
        assert response.status_code == 200

        # 管理者専用ページにアクセス
        response = await client.get("/admin")
        assert response.status_code == 403

        # 管理者専用ページにアクセス
        response = await client.get("/admin-sync")
        assert response.status_code == 403

    # 管理者ユーザーでadmin_onlyデコレータ付きの非同期関数にアクセスできる。
    async with client.session_transaction():
        # 管理者ユーザーでログイン
        response = await client.get("/login_admin")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin logged in"

        # 管理者専用ページにアクセス
        response = await client.get("/admin")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin page"

        # 管理者専用ページにアクセス
        response = await client.get("/admin-sync")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin sync page"

    # admin_onlyデコレータが関数のメタデータを保持することをテスト。

    @pytilpack.quart_auth.admin_only
    async def test_async_function() -> str:
        """非同期テスト関数。"""
        return "test"

    @pytilpack.quart_auth.admin_only
    def test_sync_function() -> str:
        """同期テスト関数。"""
        return "test"

    # 非同期関数のメタデータ確認
    assert test_async_function.__name__ == "test_async_function"
    assert test_async_function.__doc__ == "非同期テスト関数。"

    # 同期関数のメタデータ確認
    assert test_sync_function.__name__ == "test_sync_function"
    assert test_sync_function.__doc__ == "同期テスト関数。"


@pytest.mark.asyncio
async def test_login_user_set_cookie_false(
    client: quart.typing.TestClientProtocol,
) -> None:
    """set_cookie=Falseの場合は通常のCookieベースのログイン処理が行われない。"""
    async with client.session_transaction():
        # set_cookie=Falseでログイン
        response = await client.get("/login_no_cookie")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in without cookie"

        # この時点では通常のCookieベースのログイン状態になっていない
        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: &lt;anonymous&gt;"

        # 非公開ページにもアクセスできない
        response = await client.get("/private")
        assert response.status_code == 401
