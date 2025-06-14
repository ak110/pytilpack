"""SyncMixinのテストコード。"""

import pathlib

import pytest
import sqlalchemy
import sqlalchemy.orm

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.SyncMixin):
    """ベースクラス。"""


class Test1(Base, pytilpack.sqlalchemy_.AsyncUniqueIDMixin):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test2"
    __table_args__ = (sqlalchemy.UniqueConstraint("value1", "value2", name="uc1"),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(250), nullable=False, unique=True, doc="名前"
    )
    pass_hash = sqlalchemy.Column(
        sqlalchemy.String(100), default=None, comment="パスハッシュ"
    )
    # 有効フラグ
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(  # このコメントは無視されてほしい
        sqlalchemy.Boolean, nullable=False, default=False
    )
    value1 = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    value2 = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=512)
    value3 = sqlalchemy.Column(sqlalchemy.Float, nullable=False, default=1.0)
    value4 = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    value5 = sqlalchemy.Column(sqlalchemy.Text, nullable=False, default=lambda: "func")


def test_mixin_basic_functionality(tmp_path: pathlib.Path) -> None:
    """SyncMixinの基本機能をテスト。"""
    Base.init(f"sqlite:///{tmp_path}/test.db")

    # テーブル作成
    with Base.connect() as conn:
        Base.metadata.create_all(conn)

    # セッションスコープのテスト
    with Base.session_scope():
        # 件数取得 (0件)
        assert Base.count(Test1.select()) == 0

        # データ挿入
        test_record = Test1(unique_id="test_name")
        Base.session().add(test_record)
        Base.session().commit()

        # データ取得
        result = Test1.get_by_id(test_record.id)
        assert result is not None
        assert result.unique_id == "test_name"

        # 件数取得 (1件)
        assert Base.count(Test1.select()) == 1

        # 削除
        Base.session().execute(Test1.delete())
        Base.session().commit()

        # 件数取得 (0件)
        assert Base.count(Test1.select()) == 0


def test_sync_mixin_context_vars(tmp_path: pathlib.Path) -> None:
    """SyncMixinのcontextvar管理をテスト。"""
    Base.init(f"sqlite:///{tmp_path}/test.db")

    # テーブル作成
    with Base.connect() as conn:
        Base.metadata.create_all(conn)

    # start_session / close_sessionのテスト
    token = Base.start_session()
    try:
        # セッションが取得できることを確認
        session = Base.session()
        assert session is not None

        # データ操作
        test_record = Test1(unique_id="test_context")
        session.add(test_record)
        session.commit()

        # select メソッドのテスト
        query = Test1.select().where(Test1.unique_id == "test_context")
        result = session.execute(query).scalar_one()
        assert result.unique_id == "test_context"

    finally:
        Base.close_session(token)

    # セッションがリセットされていることを確認
    with pytest.raises(RuntimeError):
        Base.session()


def test_sync_mixin_to_dict() -> None:
    """to_dictメソッドのテスト。"""
    test_record = Test1(id=1, unique_id="test_dict")
    result = test_record.to_dict()

    assert result == {"id": 1, "unique_id": "test_dict"}

    # includes テスト
    result_includes = test_record.to_dict(includes=["unique_id"])
    assert result_includes == {"unique_id": "test_dict"}

    # excludes テスト
    result_excludes = test_record.to_dict(excludes=["id"])
    assert result_excludes == {"unique_id": "test_dict"}
