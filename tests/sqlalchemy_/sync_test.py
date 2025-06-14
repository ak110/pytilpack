"""SyncMixinのテストコード。"""

import pathlib

import pytest
import sqlalchemy
import sqlalchemy.orm

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.SyncMixin):
    """ベースクラス。"""


class TestTable(Base):
    """テスト用テーブル。"""

    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(50)
    )


def test_sync_mixin_basic_functionality(tmp_path: pathlib.Path) -> None:
    """SyncMixinの基本機能をテスト。"""
    db_path = tmp_path / "test.db"
    Base.init(f"sqlite:///{db_path}")

    # テーブル作成
    with Base.connect() as conn:
        Base.metadata.create_all(conn)

    # セッションスコープのテスト
    with Base.session_scope() as session:
        # データ挿入
        test_record = TestTable(name="test_name")
        session.add(test_record)
        session.commit()

        # データ取得
        result = TestTable.get_by_id(test_record.id)
        assert result is not None
        assert result.name == "test_name"


def test_sync_mixin_context_vars(tmp_path: pathlib.Path) -> None:
    """SyncMixinのcontextvar管理をテスト。"""
    db_path = tmp_path / "test.db"
    Base.init(f"sqlite:///{db_path}")

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
        test_record = TestTable(name="test_context")
        session.add(test_record)
        session.commit()

        # select メソッドのテスト
        query = TestTable.select().where(TestTable.name == "test_context")
        result = session.execute(query).scalar_one()
        assert result.name == "test_context"

    finally:
        Base.close_session(token)

    # セッションがリセットされていることを確認
    with pytest.raises(RuntimeError):
        Base.session()


def test_sync_mixin_to_dict() -> None:
    """to_dictメソッドのテスト。"""
    test_record = TestTable(id=1, name="test_dict")
    result = test_record.to_dict()

    assert result == {"id": 1, "name": "test_dict"}

    # includes テスト
    result_includes = test_record.to_dict(includes=["name"])
    assert result_includes == {"name": "test_dict"}

    # excludes テスト
    result_excludes = test_record.to_dict(excludes=["id"])
    assert result_excludes == {"name": "test_dict"}
