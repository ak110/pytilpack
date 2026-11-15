"""ログ関連。"""

__lazy_modules__ = [
    "contextlib",
    "contextvars",
    "datetime",
    "hashlib",
    "io",
    "json",
    "logging",
    "logging.handlers",
    "pathlib",
    "pytilpack.python",
    "re",
    "time",
    "typing",
    "uuid",
]

# pylint: disable=redefined-builtin

import contextlib
import contextvars
import datetime as dt
import hashlib
import io
import json
import logging
import logging.handlers
import pathlib
import re
import time
import typing
import uuid

import pytilpack.python

_logger = logging.getLogger(__name__)


def _json_default(o: typing.Any) -> typing.Any:
    """JSONエンコードできないオブジェクトの変換処理。

    jsonifyで使用する。挙動互換のため、pytilpack.json.converterとは別関数として持つ
    （converterはbytesをbase64化するが、jsonifyは元々bytesを`str(o)`にフォールバック
    していたため）。
    """
    if isinstance(o, dt.datetime):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, dt.date):
        return o.isoformat()
    if isinstance(o, dt.time):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, pathlib.Path):
        return str(o)
    if hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


_exception_history: dict[str, tuple[dt.datetime, int]] = {}
"""例外フィンガープリント → (最終発生時刻, 最終WARNING以降の発生回数)。"""


def clear_exception_history() -> None:
    """例外重複排除の履歴をクリアする。"""
    _exception_history.clear()


def stream_handler(
    stream: io.TextIOBase | None = None,
    level: int | None = logging.INFO,
    format: str | None = "[%(levelname)-5s] %(message)s",
) -> logging.Handler:
    """標準エラー出力用のハンドラを作成する。"""
    handler = logging.StreamHandler(stream)
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


def file_handler(
    log_path: str | pathlib.Path,
    mode: str = "w",
    encoding: str = "utf-8",
    level: int | None = logging.DEBUG,
    format: str | None = "[%(levelname)-5s] %(message)s",
    max_bytes: int | None = None,
    when: str | None = None,
    backup_count: int = 5,
) -> logging.Handler:
    """ファイル出力用のハンドラを作成する。"""
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler: logging.Handler
    if max_bytes is not None:
        assert when is None, "max_bytesとwhenは同時に指定できません。"
        handler = logging.handlers.RotatingFileHandler(
            log_path, mode=mode, encoding=encoding, maxBytes=max_bytes, backupCount=backup_count
        )
    elif when is not None:
        handler = logging.handlers.TimedRotatingFileHandler(log_path, when=when, backupCount=backup_count, encoding=encoding)
    else:
        handler = logging.FileHandler(log_path, mode=mode, encoding=encoding)
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


def multiprocess_file_handler(
    log_path: str | pathlib.Path,
    max_bytes: int,
    backup_count: int = 5,
    encoding: str = "utf-8",
    level: int | None = logging.DEBUG,
    format: str | None = "[%(levelname)-5s] %(message)s",
) -> logging.Handler:
    """複数プロセスで同じファイルへ追記し、容量でローテーションするハンドラを作成する。

    `pip install pytilpack[logging]`で導入する`filelock`が必要。

    `<log_path>.lock`のプロセス間ロックの内側で、容量の判定、世代の移動、追記、flushを行い、
    ロックを解放する前にログ本体を閉じる。書き込みや世代の移動が失敗した場合も同様に閉じてから解放する。
    書き込みの合間は本体を開かないため、待機中のプロセスが他プロセスの世代の移動を妨げない
    （Windowsでは開いているファイルを移動できない）。
    容量の判定と世代の移動は標準の`logging.handlers.RotatingFileHandler`に従う。

    同じログへ書く各プロセスは、同じパス・容量・世代数で自身のハンドラを作成する。
    `file_handler`など排他しないハンドラを同じログへ混在させると、この保証は失われる。
    ハンドラの作成ではログを開かず、既存の内容を切り詰めない。

    Args:
        log_path: ログファイルのパス。
        max_bytes: ローテーションする容量（バイト）。
        backup_count: 保存する世代数。
        encoding: 文字エンコーディング。
        level: ログレベル。Noneの場合は設定しない。
        format: ログの書式。Noneの場合は設定しない。

    Returns:
        loggerへ登録できるハンドラ。

    Raises:
        ImportError: `filelock`が導入されていない場合。
    """
    try:
        # logging extraの任意依存のため、この機能の利用時だけ読み込む
        import filelock  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise ImportError(
            "multiprocess_file_handlerにはfilelockが必要です。`pip install pytilpack[logging]`で導入してください。"
        ) from e
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = _MultiprocessRotatingFileHandler(
        log_path,
        filelock.FileLock,
        max_bytes=max_bytes,
        backup_count=backup_count,
        encoding=encoding,
    )
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


class _MultiprocessRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """プロセス間ロックの内側でだけログ本体を開くRotatingFileHandler。"""

    def __init__(
        self,
        log_path: pathlib.Path,
        lock_factory: typing.Callable[[str], contextlib.AbstractContextManager[typing.Any]],
        max_bytes: int,
        backup_count: int,
        encoding: str,
    ) -> None:
        # delay=Trueで本体を遅延オープンし、ロック待ちの間や作成時に開かない。
        # mode="a"で既存の内容を切り詰めない。
        super().__init__(log_path, mode="a", maxBytes=max_bytes, backupCount=backup_count, encoding=encoding, delay=True)
        # ロックファイルは本体と同じ絶対パス（baseFilename）から決める。
        # 相対パスのまま渡すと、作成後にカレントディレクトリが変わった場合や別の表記で作成した場合に、
        # 同じ本体へ別々のロックを使ってしまう。
        self.process_lock = lock_factory(f"{self.baseFilename}.lock")

    def emit(self, record: logging.LogRecord) -> None:
        """ロックの内側で容量判定・世代移動・追記を行い、解放前に本体を閉じる。"""
        with self.process_lock:
            try:
                super().emit(record)
            finally:
                self._close_stream()

    def _close_stream(self) -> None:
        if self.stream is not None:
            stream, self.stream = self.stream, None
            stream.close()


@contextlib.contextmanager
def timer(name: str, logger: logging.Logger | None = None):
    """処理時間を計測してログ出力するコンテキストマネージャー。"""
    start_time = time.perf_counter()
    has_error = False
    try:
        yield
    except Exception:
        has_error = True
        raise
    finally:
        elapsed = time.perf_counter() - start_time
        if logger is None:
            logger = _logger
        if has_error:
            logger.warning(f"[{name}] failed in {elapsed:.0f} s. The exception was re-raised; see its traceback for the cause.")
        else:
            logger.info(f"[{name}] done in {elapsed:.0f} s")


def exception_with_dedup(
    logger: logging.Logger,
    exc: BaseException | str,
    msg: str = "Unhandled exception occurred",
    dedup_window: dt.timedelta | None = None,
    dedup_count: int | None = None,
    now: dt.datetime | None = None,
) -> None:
    """同一 fingerprint が重複排除ウィンドウ内にあれば INFO、そうでなければ WARN でログ出力する。

    exc に例外オブジェクトを渡した場合は WARN 時に exc_info=True が付く。
    文字列を渡した場合は exc_info なしで出力される。

    dedup_window（時間窓）と dedup_count（個数窓）は併用可能で、
    いずれかの条件を超えた場合に再度 WARN で出力される。
    両方 None の場合は dedup_window のデフォルト（24 時間）が適用される。

    Args:
        logger: 出力先ロガー
        exc: 例外オブジェクトまたは文字列。fingerprint の生成に使用する。
        msg: ログメッセージ。fingerprint にも含まれる。
        dedup_window: 同一エラーとみなす時間幅。デフォルト 24 時間（dedup_count 指定時は None）。
        dedup_count: 同一エラーとみなす回数。WARN の後は dedup_count - 1 回 INFO で出力し、
            前回の WARN より後の発生回数が dedup_count に達した呼び出しで再度 WARN で出力する
            （dedup_count=3 なら WARN → INFO → INFO → WARN）。
        now: 現在時刻。
    """
    if dedup_window is None and dedup_count is None:
        dedup_window = dt.timedelta(days=1)
    if now is None:
        now = dt.datetime.now()

    is_exception = isinstance(exc, BaseException)
    # 種別タグとJSON配列の要素境界により、例外と文字列の違い・区切り文字の位置・
    # 別モジュールの同名クラスが異なる入力を、別々の履歴として扱う
    parts = (
        ["exception", f"{type(exc).__module__}.{type(exc).__qualname__}", str(exc), msg]
        if is_exception
        else ["str", str(exc), msg]
    )
    raw = json.dumps(parts)
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    last = _exception_history.get(fingerprint)
    if last is None:
        should_warn = True
    else:
        last_seen, count = last
        time_expired = dedup_window is not None and (now - last_seen) >= dedup_window
        count_expired = dedup_count is not None and count + 1 >= dedup_count
        should_warn = time_expired or count_expired

    if should_warn:
        if is_exception:
            logger.warning(msg, exc_info=True)
        else:
            logger.warning(msg)
        _exception_history[fingerprint] = (now, 0)
    else:
        logger.info(msg)
        assert last is not None
        _exception_history[fingerprint] = (now, last[1] + 1)


_current_context_id: contextvars.ContextVar[str] = contextvars.ContextVar("_current_context_id", default="")


@contextlib.asynccontextmanager
async def capture_context(
    target_logger: logging.Logger,
    formatter: logging.Formatter,
    level: int = logging.INFO,
) -> typing.AsyncGenerator[typing.Callable[[], str], None]:
    """指定ロガーに対して“この非同期コンテキストのログだけ”をStringIOへ集約する。

    Args:
        target_logger: ハンドラを一時的に取り付ける対象のロガー。
        formatter: このキャプチャ専用のフォーマッタ。
        level: このキャプチャハンドラのログレベル。

    Yields:
        get_value: これまでにバッファへ書かれた文字列を返す関数。
    """
    context_id: str = str(uuid.uuid4())
    token = _current_context_id.set(context_id)
    try:
        buffer: io.StringIO = io.StringIO()
        handler: logging.StreamHandler = logging.StreamHandler(buffer)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        handler.addFilter(ContextFilter(context_id))
        target_logger.addHandler(handler)
        try:

            def get_value() -> str:
                return buffer.getvalue()

            yield get_value
        finally:
            target_logger.removeHandler(handler)
            handler.close()
            buffer.close()
    finally:
        _current_context_id.reset(token)


class ContextFilter(logging.Filter):
    """_context_idと一致するログだけを通すフィルタ。"""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id

    def filter(self, record: logging.LogRecord) -> bool:
        """フィルタ処理。"""
        del record  # noqa
        return _current_context_id.get("") == self.target_id


def jsonify(
    data: typing.Any, indent: int | None = None, truncate: bool = True, model_dump_kwargs: dict[str, typing.Any] | None = None
) -> str:
    """オブジェクトをJSON文字列に変換する。

    Args:
        data: JSON化するオブジェクト。
        indent: インデント幅。Noneの場合は改行なし。
        truncate: 長い文字列/バイト列を省略するかどうか。
        model_dump_kwargs: pydanticモデルをdictに変換する際の追加引数。

    Returns:
        JSON文字列。
    """
    if model_dump_kwargs is None:
        model_dump_kwargs = {}
    try:
        if truncate:
            data = truncate_values(data, bytes_to_str=True, model_dump_kwargs=model_dump_kwargs)
        else:
            data = pytilpack.python.pydantic_to_dict(data, **model_dump_kwargs)

        separators = None if indent is not None else (",", ":")
        return json.dumps(data, ensure_ascii=False, indent=indent, separators=separators, default=_json_default)
    except Exception:
        # この関数はログ出力が主目的であるため、失敗しても例外を送出せずreprを返す。
        _logger.warning("jsonify失敗。repr()の文字列を返して処理を続ける（対応不要）", exc_info=True)
        return repr(data)


def truncate_values(
    data: typing.Any,
    max_str_len: int = 100,
    max_bytes_len: int = 100,
    bytes_to_str: bool = False,
    model_dump_kwargs: dict[str, typing.Any] | None = None,
    max_num_list_len: int = 3,
) -> typing.Any:
    """dictやlist/tuple内の長いstr/bytesを再帰的に省略する。

    Args:
        data: 処理対象のデータ。
        max_str_len: 文字列の最大長。
        max_bytes_len: バイト列の最大長。
        bytes_to_str: bytesをstrに変換するかどうか。
        model_dump_kwargs: pydanticモデルをdictに変換する際の追加引数。
        max_num_list_len: 全要素が数値型(int/float)のlistの最大表示件数。超えた場合は先頭n件+"..."に省略。

    Returns:
        省略処理を行った新しいオブジェクト。
    """
    if model_dump_kwargs is None:
        model_dump_kwargs = {}
    data = pytilpack.python.pydantic_to_dict(data, **model_dump_kwargs)

    if isinstance(data, str):
        if len(data) > max_str_len:
            return data[:max_str_len] + "..."
        return data
    if isinstance(data, bytes):
        if bytes_to_str:
            decoded = data.decode("utf-8", errors="replace")
            if len(decoded) > max_str_len:
                return decoded[:max_str_len] + "..."
            return decoded
        else:
            if len(data) > max_bytes_len:
                return data[:max_bytes_len] + b"..."
            return data
    if isinstance(data, dict):
        return {
            truncate_values(k, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len): truncate_values(
                v, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len
            )
            for k, v in data.items()
        }
    if isinstance(data, list):
        if len(data) > max_num_list_len and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in data):
            return [*data[:max_num_list_len], "..."]
        return [
            truncate_values(item, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len)
            for item in data
        ]
    if isinstance(data, tuple):
        return tuple(
            truncate_values(item, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len)
            for item in data
        )
    return data


REDACTED = "[REDACTED]"
"""redact_secretsが秘匿部分の置換に使う文字列。"""

_REDACT_HEADER_PATTERN = re.compile(r"(?i)\b((?:proxy-)?authorization)([ \t]*[:=][ \t]*)\S[^\r\n]*")
# 伏せ済みの値（[REDACTED]）は角括弧を含むため専用の選択肢で値全体として読む。
# 後続の文字が続く値（[REDACTED]abcなど）もまとめて伏せ直し、未処理の部分を残さない。
_REDACT_NAMED_PATTERN = re.compile(
    r"""(?i)(["']?)(\b[\w-]*?(?:api[ _-]?key|token|secret|password)[\w-]*)\1([ \t]*[:=][ \t]*)"""
    r"""("(?:\\.|[^"\\\r\n])*"|'(?:\\.|[^'\\\r\n])*'|\[REDACTED\][^\s,;&"')}\]]*|[^\s,;&"')}\]]+)"""
)
_REDACT_KEYLIKE_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])")


def redact_secrets(text: str) -> str:
    r"""診断用の文字列から資格情報らしき部分を`[REDACTED]`へ置換する。

    例外メッセージや外部コマンドのエラー出力をログへ保存する前に、呼び出し元が明示的に適用する。
    エラーの種類・コード・周辺の説明、改行などの非秘匿部分は保持する。
    置換後の文字列へ再適用しても結果は変わらない。

    検出規則:

    - `Authorization`・`Proxy-Authorization`（大文字小文字を区別しない）に`:`か`=`が続く場合、その行末までの値。
    - 名前に`api key`・`token`・`secret`・`password`を含むキー（大文字小文字を区別しない。
      `api key`は空白・ハイフン・アンダースコア区切りや区切りなしにも対応し、`access_token`のような前後の語を含む）に
      `:`か`=`が続く場合の値。値が引用符で囲まれていれば引用符内（空白と`\`でエスケープした引用符を含む）を、
      そうでなければ空白・`,`・`;`・`&`・引用符・閉じ括弧（`)`・`]`・`}`）の直前までを伏せる。キー自体の引用符にも対応する。
    - 英数字・`_`・`-`が32文字以上連続する文字列（API鍵やトークンの形をした値）。

    限界:

    - 文字列だけでは任意の資格情報を判別できないため、完全な漏えい防止は保証しない。
      上記の規則に合わない形の資格情報（31文字以下で名前の付いていない値、URLに埋め込まれた認証情報など）は残る。
    - 32文字以上のハッシュ値・区切りなしのUUID・長い識別子や、`tokens: 5`のように対象の語を含む名前の値も伏せる。

    Args:
        text: 対象の文字列。

    Returns:
        秘匿部分を置換した文字列。対象が無ければ入力をそのまま返す。
    """
    if not text:
        return text
    text = _REDACT_HEADER_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = _REDACT_NAMED_PATTERN.sub(_redact_named_value, text)
    return _REDACT_KEYLIKE_PATTERN.sub(REDACTED, text)


def _redact_named_value(match: re.Match[str]) -> str:
    """名前付きの値を伏せる。値の引用符は保持する。"""
    quote, key, separator, value = match.groups()
    value = f"{value[0]}{REDACTED}{value[0]}" if value[:1] in ("'", '"') else REDACTED
    return f"{quote}{key}{quote}{separator}{value}"
