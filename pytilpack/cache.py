"""ファイルの最終更新日時に基づいてキャッシュを管理するモジュール。"""

import dataclasses
import pathlib
import typing

T = typing.TypeVar("T")


@dataclasses.dataclass
class CacheEntry(typing.Generic[T]):
    """キャッシュエントリ。

    タイムスタンプ、データ、ローダー関数を保持します。
    """

    mtime: float
    data: T
    loader: typing.Callable[[pathlib.Path], T]


class CachedFileLoader(typing.Generic[T]):
    """ファイルの最終更新日時に基づいてキャッシュを管理するローダー。

    使用例::
        ```python
        # テキストファイルを読み込むローダー
        loader = CachedFileLoader[str](lambda p: p.read_text())
        # デフォルトローダーでファイルを読み込み
        content = loader.load(pathlib.Path("file.txt"))
        # カスタムローダーでオーバーライド
        uppercase = loader.load(pathlib.Path("file.txt"), lambda p: p.read_text().upper())
        ```
    """

    def __init__(
        self, loader: typing.Callable[[pathlib.Path], T] | None = None
    ) -> None:
        """デフォルトのローダー関数を設定してインスタンスを初期化。

        Args:
            loader: デフォルトのローダー関数。省略可能。
        """
        self._loader = loader
        self._cache: dict[pathlib.Path, CacheEntry[T]] = {}

    def load(
        self,
        path: pathlib.Path,
        loader: typing.Callable[[pathlib.Path], T] | None = None,
    ) -> T:
        """キャッシュを利用してファイルを読み込み。

        Args:
            path: ファイルパス。
            loader: ローダー関数。省略時は__init__で指定したローダーを使用。

        Returns:
            読み込んだデータ。キャッシュがある場合はキャッシュから返す。

        Raises:
            ValueError: ローダー関数が指定されていない場合。
            FileNotFoundError: ファイルが存在しない場合。
        """
        if not path.exists():
            raise FileNotFoundError(str(path))

        # 現在のファイル情報を取得
        stats = path.stat()
        current_mtime = stats.st_mtime

        # キャッシュが存在し最新かチェック
        if cache_entry := self._cache.get(path):
            if cache_entry.mtime >= current_mtime and (
                loader is None or loader is cache_entry.loader
            ):
                return cache_entry.data
            # ファイルが更新されたかローダーが変更された場合、キャッシュを無効化
            self.remove(path)

        # 使用するローダーを決定
        effective_loader = loader if loader is not None else self._loader
        if effective_loader is None:
            raise ValueError("ローダー関数が指定されていません")

        # データを読み込みキャッシュに保存
        data = effective_loader(path)
        self._cache[path] = CacheEntry(current_mtime, data, effective_loader)
        return data

    def clear(self) -> None:
        """すべてのキャッシュエントリをクリア。"""
        self._cache.clear()

    def remove(self, path: pathlib.Path) -> None:
        """指定されたパスのキャッシュを削除。

        Args:
            path: 削除するキャッシュのパス。
        """
        self._cache.pop(path, None)
