"""Flaskの保護エンドポイントを通す認可テスト。"""

import flask
import flask_login

import pytilpack.flask_login


def test_admin_only_endpoint() -> None:
    """未認証者と一般利用者を拒否し、管理者だけを通す。"""
    app = flask.Flask(__name__)
    app.secret_key = "test-only-secret"
    login_manager = flask_login.LoginManager(app)

    class User(flask_login.UserMixin):
        def __init__(self, name: str, *, is_admin: bool) -> None:
            self.id = name
            self.is_admin = is_admin

    users = {"user": User("user", is_admin=False), "admin": User("admin", is_admin=True)}

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return users.get(user_id)

    @app.get("/login/<name>")
    def login(name: str) -> str:
        flask_login.login_user(users[name])
        return "ok"

    @app.get("/admin")
    @pytilpack.flask_login.admin_only
    def admin() -> str:
        assert pytilpack.flask_login.is_admin()
        return "ok"

    client = app.test_client()
    assert client.get("/admin").status_code == 401
    assert client.get("/login/user").status_code == 200
    assert client.get("/admin").status_code == 403
    assert client.get("/login/admin").status_code == 200
    assert client.get("/admin").status_code == 200
