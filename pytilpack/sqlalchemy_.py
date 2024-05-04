"""SQLAlchemy用のユーティリティ集。"""

import logging
import time

import sqlalchemy
import sqlalchemy.orm

try:
    from typing import Self  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Self

logger = logging.getLogger(__name__)


def register_ping():
    """コネクションプールの切断対策。"""

    @sqlalchemy.event.listens_for(sqlalchemy.pool.Pool, "checkout")
    def _ping_connection(dbapi_connection, connection_record, connection_proxy):
        """コネクションプールの切断対策。"""
        _ = connection_record, connection_proxy  # noqa
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1")
        except Exception as e:
            raise sqlalchemy.exc.DisconnectionError() from e
        finally:
            cursor.close()


class IDMixin:
    """models.Class.query.get()がdeprecatedになるため"""

    @classmethod
    def get_by_id(cls: type[Self], id_: int, for_update: bool = False) -> Self | None:
        """IDを元にインスタンスを取得。"""
        q = cls.query.filter(cls.id == id_)  # type: ignore
        if for_update:
            q = q.with_for_update()
        return q.one_or_none()


def wait_for_connection(url: str, timeout: float = 10.0) -> None:
    """DBに接続可能になるまで待機する。"""
    failed = False
    start_time = time.time()
    while True:
        try:
            engine = sqlalchemy.create_engine(url)
            try:
                with engine.connect() as connection:
                    result = connection.execute(sqlalchemy.text("SELECT 1"))
                try:
                    # 接続成功
                    if failed:
                        logger.info("DB接続成功")
                    break
                finally:
                    result.close()
            finally:
                engine.dispose()
        except Exception:
            # 接続失敗
            if not failed:
                failed = True
                logger.info(f"DB接続待機中 . . . (URL: {url})")
            if time.time() - start_time >= timeout:
                raise
            time.sleep(1)


def safe_close(session: sqlalchemy.orm.Session):
    """例外を出さずにセッションをクローズ。"""
    try:
        session.close()
    except Exception:
        pass
