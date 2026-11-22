__lazy_modules__ = ["dataclasses", "pathlib", "typing"]

import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class CacheEntry[T]:
    mtime: float
    data: T
    loader: typing.Callable[[pathlib.Path], T]


class CachedFileLoader[T]:
    def __init__(self, loader: typing.Callable[[pathlib.Path], T] | None = None) -> None:
        self._loader = loader
        self._cache: dict[pathlib.Path, CacheEntry[T]] = {}

    def load(
        self,
        path: pathlib.Path,
        loader: typing.Callable[[pathlib.Path], T] | None = None,
    ) -> T:
        if not path.exists():
            raise FileNotFoundError(f"ファイルが存在しません: {path}。パスの指定を見直すか、ファイルを作成してから呼び出す")

        stats = path.stat()
        current_mtime = stats.st_mtime

        if cache_entry := self._cache.get(path):
            if cache_entry.mtime >= current_mtime and (loader is None or loader is cache_entry.loader):
                return cache_entry.data
            self.remove(path)

        effective_loader = loader if loader is not None else self._loader
        if effective_loader is None:
            raise ValueError("ローダー関数が指定されていません。load()のloader引数か、CachedFileLoader()のloader引数で指定する")

        data = effective_loader(path)
        self._cache[path] = CacheEntry(current_mtime, data, effective_loader)
        return data

    def clear(self) -> None:
        self._cache.clear()

    def remove(self, path: pathlib.Path) -> None:
        self._cache.pop(path, None)
