"""Flask-SQLAlchemy版のテストコード。"""

import datetime
import typing

import pytest
import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.exc
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase):  # type: ignore[name-defined]
    """ベースクラス。"""

    __test__ = False


class Test1(Base, pytilpack.sqlalchemy.Mixin, pytilpack.sqlalchemy.UniqueIDMixin):  # pylint: disable=too-many-ancestors
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base, pytilpack.sqlalchemy.Mixin):
    """テストクラス。"""

    # pylint: disable=duplicate-code
    # async/sync版（tests.sqlalchemy.async_test.Test2・tests.sqlalchemy.sync_test.Test2）と
    # 並行実装のため許容する。
    __test__ = False
    __tablename__ = "test2"
    __table_args__ = (sqlalchemy.UniqueConstraint("value1", "value2", name="uc1"),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(250), nullable=False, unique=True, doc="名前")
    pass_hash = sqlalchemy.Column(sqlalchemy.String(100), default=None, comment="パスハッシュ")
    # 有効フラグ
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(  # このコメントは無視されてほしい
        sqlalchemy.Boolean, nullable=False, default=False
    )
    value1 = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    value2 = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=512)
    value3 = sqlalchemy.Column("value0", sqlalchemy.Float, nullable=False, default=1.0)
    value4 = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    value5 = sqlalchemy.Column(sqlalchemy.Text, nullable=False, default=lambda: "func")


# register_ping()はグローバルなPoolクラスへリスナーを登録するため、呼ぶたびに蓄積する。
# moduleスコープにすると、pytest-xdistのworksteal分配で同一モジュールのテストが同一ワーカーへ
# 非連続に割り当たった際にsetupが繰り返され、リスナーが増え続ける。sessionスコープでは
# ワーカーごとに1回だけ登録されるため、分配のされ方によらず一定となる。
@pytest.fixture(name="engine", scope="session", autouse=True)
def _engine() -> typing.Generator[sqlalchemy.engine.Engine, None, None]:
    """DB接続。"""
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    pytilpack.sqlalchemy.register_ping()
    yield engine


@pytest.fixture(name="session", scope="function")
def _session(engine: sqlalchemy.engine.Engine) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
    """セッション。

    Mixin.get_by_id()などが参照するクラス変数queryを、ここで生成したSessionへ束縛する。
    Sessionはfunctionスコープで閉じるため、束縛を残すとクローズ済みのSessionを
    次のテストが参照する。終了時に解除し、Sessionを持たないテストからの利用は
    エラーとして表面化させる。

    """
    with sqlalchemy.orm.Session(engine) as session:
        Test1.query = session.query(Test1)
        try:
            yield session
        finally:
            Test1.query = None


@pytest.fixture(autouse=True)
def _clean_tables(engine: sqlalchemy.engine.Engine) -> typing.Generator[None, None, None]:
    """各テストの前に共有DBのテーブルを空にする。

    engineはsessionスコープで共有されるため、コミットした行はテストをまたいで残る。
    pytest-xdistのworksteal分配では同一ワーカー内の実行順が収集順と一致しないため、
    他テストが挿入した行の有無に依存すると分配のされ方によって結果が変わる。
    Sessionはfunctionスコープで閉じて未確定状態を破棄し、ここで全テーブルの行を削除する。

    """
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


def test_repr() -> None:
    """__repr__のテスト。"""
    # pylint: disable=duplicate-code
    # async版（tests.sqlalchemy.async_test.test_repr）と並行実装のため許容する。
    # デフォルト: idを表示
    test1 = Test1(id=1)
    r = repr(test1)
    assert r == f"<{Test1.__module__}.{Test1.__qualname__}(id=1)>"
    assert str(test1) == r

    # idがNoneの場合
    test1_no_id = Test1()
    assert repr(test1_no_id) == f"<{Test1.__module__}.{Test1.__qualname__}(id=None)>"

    # _repr_attrsをオーバーライドしたケース
    class CustomRepr(Test1):  # pylint: disable=too-many-ancestors
        """カスタムreprのテスト用クラス。"""

        __test__ = False

        @typing.override
        def _repr_attrs(self):
            return {"id": self.id, "unique_id": self.unique_id}

    custom = CustomRepr(id=42, unique_id="abc")
    assert "id=42" in repr(custom)
    assert "unique_id='abc'" in repr(custom)


def test_get_by_id(session: sqlalchemy.orm.Session) -> None:
    Base.metadata.create_all(session.bind)  # type: ignore
    session.add(Test1(id=1))
    session.commit()

    assert Test1.get_by_id(1).id == 1  # type: ignore
    assert Test1.get_by_id(2) is None
    assert Test1.get_by_id(1, for_update=True).id == 1  # type: ignore


def test_get_by_id_not_null(session: sqlalchemy.orm.Session) -> None:
    """get_by_id_not_nullが同期呼び出しで動作することを確認。

    修正前は async def で定義されており、awaitせずに呼ぶとコルーチンオブジェクトが
    返り、ValueErrorが送出されなかった。修正後は同期的に値を返すことを検証する。
    """
    Base.metadata.create_all(session.bind)  # type: ignore

    session.add(Test1(id=10))
    session.commit()

    # 存在するIDでは正常にインスタンスが返る（awaitなし）
    result = Test1.get_by_id_not_null(10)
    assert result.id == 10

    # 存在しないIDではValueErrorが送出される（awaitなし）
    with pytest.raises(ValueError):
        Test1.get_by_id_not_null(9999)


def test_get_by_unique_id(session: sqlalchemy.orm.Session) -> None:
    Base.metadata.create_all(session.bind)  # type: ignore
    test1 = Test1(id=2, unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    session.commit()

    assert Test1.get_by_unique_id(unique_id).id == 2  # type: ignore
    assert Test1.get_by_unique_id(unique_id, allow_id=True).id == 2  # type: ignore
    assert Test1.get_by_unique_id(2) is None
    assert Test1.get_by_unique_id(2, allow_id=True).id == 2  # type: ignore
    assert Test1.get_by_unique_id("2", allow_id=True) is None


def test_to_dict() -> None:
    """to_dictのテスト。"""
    # pylint: disable=duplicate-code
    # async/sync版（tests.sqlalchemy.async_test.test_to_dict・tests.sqlalchemy.sync_test.test_to_dict）と
    # 並行実装のため許容する。
    test2 = Test2(name="test2", enabled=True, value4=datetime.datetime(2021, 1, 1))
    assert test2.to_dict(excludes=["pass_hash"]) == {
        "id": None,
        "name": "test2",
        "enabled": True,
        "is_admin": None,
        "value1": None,
        "value2": None,
        "value3": None,
        "value4": "2021-01-01T00:00:00",
        "value5": None,
    }
    assert test2.to_dict(includes=["name", "value3"], exclude_none=True) == {"name": "test2"}


def test_describe() -> None:
    """describe()のテスト。"""
    # pylint: disable=duplicate-code
    # async/sync版（tests.sqlalchemy.async_test.test_describe・tests.sqlalchemy.sync_test.test_describe）と
    # 並行実装のため許容する。テスト対象モデルの構造が同一であるため出力アサーションも一致する。
    desc = pytilpack.sqlalchemy.describe(Base)
    print(f"{'=' * 64}")
    print(desc)
    print(f"{'=' * 64}")
    assert (
        desc
        == """\
Table: test
+-----------+-------------+--------+-------+-----------+----------------+------------+
| Field     | Type        | Null   | Key   | Default   | Extra          | Comment    |
+===========+=============+========+=======+===========+================+============+
| id        | INTEGER     | NO     | PRI   | NULL      | auto_increment |            |
+-----------+-------------+--------+-------+-----------+----------------+------------+
| unique_id | VARCHAR(43) | YES    | UNI   | NULL      |                | ユニークID |
+-----------+-------------+--------+-------+-----------+----------------+------------+

Table: test2
+-----------+--------------+--------+-------+------------+----------------+--------------+
| Field     | Type         | Null   | Key   | Default    | Extra          | Comment      |
+===========+==============+========+=======+============+================+==============+
| id        | INTEGER      | NO     | PRI   | NULL       | auto_increment |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| name      | VARCHAR(250) | NO     | UNI   | NULL       |                | 名前         |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| pass_hash | VARCHAR(100) | YES    |       | NULL       |                | パスハッシュ |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| enabled   | BOOLEAN      | NO     |       | True       |                | 有効フラグ   |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| is_admin  | BOOLEAN      | NO     |       | False      |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value1    | INTEGER      | YES    |       | 0          |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value2    | INTEGER      | NO     |       | 512        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value0    | FLOAT        | NO     |       | 1.0        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value4    | DATETIME     | NO     |       | NULL       |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value5    | TEXT         | NO     |       | (function) |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
"""
    )


def test_wait_for_connection() -> None:
    """wait_for_connectionのテスト。"""
    # 正常系
    pytilpack.sqlalchemy.wait_for_connection("sqlite:///:memory:", timeout=0.1)

    # 異常系: タイムアウト
    with pytest.raises(RuntimeError):
        pytilpack.sqlalchemy.wait_for_connection("sqlite:////nonexistent/path/db.sqlite3", timeout=0.1)


def test_safe_close() -> None:
    """safe_closeのテスト。"""
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    session = sqlalchemy.orm.Session(engine)
    pytilpack.sqlalchemy.safe_close(session)  # 正常ケース

    # エラーケース（既にクローズ済み）
    session.close()
    pytilpack.sqlalchemy.safe_close(session)
    pytilpack.sqlalchemy.safe_close(session, log_level=None)
