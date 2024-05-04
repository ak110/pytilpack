"""テストコード。"""

import pytest
import sqlalchemy

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase):
    """ベースクラス。"""


@pytest.fixture(name="engine", scope="module")
def _engine():
    """DB接続。"""
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    pytilpack.sqlalchemy_.register_ping()
    yield engine


@pytest.fixture(name="session", scope="module")
def _session(engine: sqlalchemy.engine.Engine):
    """セッション。"""
    yield sqlalchemy.orm.Session(engine)


def test_id_mixin(session: sqlalchemy.orm.Session) -> None:
    """register_ping()のテスト。"""

    class Test(Base, pytilpack.sqlalchemy_.IDMixin):
        """テストクラス。"""

        __tablename__ = "test"

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    Test.query = session.query(Test)  # 仮

    Base.metadata.create_all(session.bind)  # type: ignore
    session.add(Test(id=1))
    session.commit()

    assert Test.get_by_id(1).id == 1  # type: ignore
    assert Test.get_by_id(2) is None
    assert Test.get_by_id(1, for_update=True).id == 1  # type: ignore
