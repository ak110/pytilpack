"""JSONC(JSON with Comments)関連。"""

import dataclasses
import json
import re
import typing

import pytilpack.io

_PathKey = str | int
_Path = typing.Sequence[_PathKey]


def load(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    """JSONCファイルの読み込み。"""
    try:
        return loads(pytilpack.io.read_text(source, encoding=encoding, errors=errors), **kwargs)
    except FileNotFoundError:
        if strict:
            raise
        return {}


def loads(text: str, **kwargs) -> typing.Any:
    """JSONC文字列のパース。"""
    return json.loads(_remove_trailing_commas(_remove_comments(text)), **kwargs)


def _remove_comments(text: str) -> str:
    """JSONCのコメントを除去する。"""
    # 文字列リテラル、行コメント、ブロックコメントを正規表現で処理する
    pattern = re.compile(
        r'"(?:[^"\\]|\\.)*"'  # 文字列リテラル
        r"|//[^\n]*"  # 行コメント
        r"|/\*.*?\*/",  # ブロックコメント
        re.DOTALL,
    )

    def replacer(m: re.Match) -> str:
        s = m.group(0)
        # 文字列リテラルはそのまま返す
        if s.startswith('"'):
            return s
        # ブロックコメントは改行を保持する
        if s.startswith("/*"):
            return "\n" * s.count("\n")
        # 行コメントは空文字
        return ""

    return pattern.sub(replacer, text)


def edit(
    text: str,
    updates: typing.Mapping[_Path, typing.Any],
    ensure_ascii: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] | None = None,
    **dumps_kwargs: typing.Any,
) -> str:
    """JSONC文字列中の指定パスの値を書き換えつつコメント・空行・インデントを維持する。

    ``updates``のキーはパス（オブジェクトキー名の文字列または配列インデックスの整数の並び）、
    値は書き込む新しいPythonオブジェクトとする。空タプルはルート全体を指す。
    値の書き換えのみを対象とし、キーの追加・削除・配列要素の追加は扱わない。
    書き換え後の値のシリアライズは``json.dumps``に委譲するため、
    ``ensure_ascii``・``default``などの追加キーワード引数はそのまま渡す。

    存在しないパスを指定した場合は``KeyError``（オブジェクト）または``IndexError``（配列）が発生する。
    パスの途中で辿った値がオブジェクト・配列でない場合は``TypeError``が発生する。

    Args:
        text: 元のJSONC文字列。
        updates: パスから新しい値へのマッピング。
        ensure_ascii: ``json.dumps``へ渡すフラグ。既定は``False``。
        default: ``json.dumps``へ渡す``default``コールバック。
        **dumps_kwargs: ``json.dumps``へ渡す追加キーワード引数。

    Returns:
        更新後のJSONC文字列。

    """
    root = _Parser(text).parse()
    replacements: list[tuple[int, int, str]] = []
    for path, value in updates.items():
        node = _resolve(root, tuple(path))
        dumped = json.dumps(value, ensure_ascii=ensure_ascii, default=default, **dumps_kwargs)
        replacements.append((node.start, node.end, dumped))
    replacements.sort(key=lambda r: r[0], reverse=True)
    # オフセット重複の検出（同一位置または包含関係を持つ書き換えは順序に依存し曖昧なため拒否する）
    for i in range(len(replacements) - 1):
        curr_start = replacements[i][0]
        next_end = replacements[i + 1][1]
        if curr_start < next_end:
            raise ValueError("updates contains overlapping paths")
    result = text
    for start, end, new_text in replacements:
        result = result[:start] + new_text + result[end:]
    return result


def edit_file(
    path: pytilpack.io.PathOrIO,
    updates: typing.Mapping[_Path, typing.Any],
    encoding: str = "utf-8",
    errors: str = "replace",
    ensure_ascii: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] | None = None,
    **dumps_kwargs: typing.Any,
) -> None:
    """JSONCファイルを``edit``で書き換えて上書き保存する。

    コメント・空行・インデントを維持したままファイル内の値を差し替える。

    """
    original = pytilpack.io.read_text(path, encoding=encoding, errors=errors)
    updated = edit(original, updates, ensure_ascii=ensure_ascii, default=default, **dumps_kwargs)
    pytilpack.io.write_text(path, updated, encoding=encoding, errors=errors)


@dataclasses.dataclass
class _Node:
    """パース時に値の範囲と構造を保持する内部ノード。"""

    kind: str  # "object" | "array" | "string" | "number" | "true" | "false" | "null"
    start: int
    end: int
    members: dict[str, "_Node"] | None = None
    items: list["_Node"] | None = None


class _Parser:
    """位置情報付きJSONC最小パーサー。値の(start, end)オフセットのみを追跡する。"""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def parse(self) -> _Node:
        self._skip_ws()
        node = self._parse_value()
        self._skip_ws()
        if self.pos != len(self.text):
            raise ValueError(f"unexpected trailing content at offset {self.pos}")
        return node

    def _skip_ws(self) -> None:
        text = self.text
        n = len(text)
        while self.pos < n:
            ch = text[self.pos]
            if ch in " \t\r\n":
                self.pos += 1
                continue
            if ch == "/" and self.pos + 1 < n:
                nxt = text[self.pos + 1]
                if nxt == "/":
                    end = text.find("\n", self.pos + 2)
                    self.pos = n if end == -1 else end
                    continue
                if nxt == "*":
                    end = text.find("*/", self.pos + 2)
                    if end == -1:
                        raise ValueError("unterminated block comment")
                    self.pos = end + 2
                    continue
            return

    def _parse_value(self) -> _Node:
        self._skip_ws()
        if self.pos >= len(self.text):
            raise ValueError("unexpected end of input")
        ch = self.text[self.pos]
        if ch == "{":
            return self._parse_object()
        if ch == "[":
            return self._parse_array()
        if ch == '"':
            return self._parse_string()
        if ch == "-" or ch.isdigit():
            return self._parse_number()
        if self.text.startswith("true", self.pos):
            node = _Node("true", self.pos, self.pos + 4)
            self.pos += 4
            return node
        if self.text.startswith("false", self.pos):
            node = _Node("false", self.pos, self.pos + 5)
            self.pos += 5
            return node
        if self.text.startswith("null", self.pos):
            node = _Node("null", self.pos, self.pos + 4)
            self.pos += 4
            return node
        raise ValueError(f"unexpected character {ch!r} at offset {self.pos}")

    def _parse_object(self) -> _Node:
        start = self.pos
        self.pos += 1  # consume "{"
        members: dict[str, _Node] = {}
        while True:
            self._skip_ws()
            if self.pos >= len(self.text):
                raise ValueError("unterminated object")
            ch = self.text[self.pos]
            if ch == "}":
                self.pos += 1
                return _Node("object", start, self.pos, members=members)
            key_node = self._parse_string()
            key = json.loads(self.text[key_node.start : key_node.end])
            self._skip_ws()
            if self.pos >= len(self.text) or self.text[self.pos] != ":":
                raise ValueError(f"expected ':' at offset {self.pos}")
            self.pos += 1
            value_node = self._parse_value()
            members[key] = value_node
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
                continue
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == "}":
                self.pos += 1
                return _Node("object", start, self.pos, members=members)
            raise ValueError(f"expected ',' or '}}' at offset {self.pos}")

    def _parse_array(self) -> _Node:
        start = self.pos
        self.pos += 1  # consume "["
        items: list[_Node] = []
        while True:
            self._skip_ws()
            if self.pos >= len(self.text):
                raise ValueError("unterminated array")
            if self.text[self.pos] == "]":
                self.pos += 1
                return _Node("array", start, self.pos, items=items)
            value_node = self._parse_value()
            items.append(value_node)
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
                continue
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == "]":
                self.pos += 1
                return _Node("array", start, self.pos, items=items)
            raise ValueError(f"expected ',' or ']' at offset {self.pos}")

    def _parse_string(self) -> _Node:
        start = self.pos
        if self.text[self.pos] != '"':
            raise ValueError(f"expected string at offset {self.pos}")
        self.pos += 1
        text = self.text
        n = len(text)
        while self.pos < n:
            ch = text[self.pos]
            if ch == "\\":
                self.pos += 2
                continue
            if ch == '"':
                self.pos += 1
                return _Node("string", start, self.pos)
            self.pos += 1
        raise ValueError("unterminated string")

    def _parse_number(self) -> _Node:
        start = self.pos
        text = self.text
        n = len(text)
        if text[self.pos] == "-":
            self.pos += 1
        while self.pos < n and text[self.pos].isdigit():
            self.pos += 1
        if self.pos < n and text[self.pos] == ".":
            self.pos += 1
            while self.pos < n and text[self.pos].isdigit():
                self.pos += 1
        if self.pos < n and text[self.pos] in "eE":
            self.pos += 1
            if self.pos < n and text[self.pos] in "+-":
                self.pos += 1
            while self.pos < n and text[self.pos].isdigit():
                self.pos += 1
        return _Node("number", start, self.pos)


def _resolve(root: _Node, path: tuple[_PathKey, ...]) -> _Node:
    """パスに従いノードを辿る。"""
    node = root
    for i, key in enumerate(path):
        if isinstance(key, str):
            if node.kind != "object" or node.members is None:
                raise TypeError(f"path {path[: i + 1]!r} expects an object but got {node.kind}")
            if key not in node.members:
                raise KeyError(key)
            node = node.members[key]
        elif isinstance(key, int) and not isinstance(key, bool):
            if node.kind != "array" or node.items is None:
                raise TypeError(f"path {path[: i + 1]!r} expects an array but got {node.kind}")
            try:
                node = node.items[key]
            except IndexError as exc:
                raise IndexError(f"array index out of range: {key}") from exc
        else:
            raise TypeError(f"path key must be str or int, got {type(key).__name__}")
    return node


def _remove_trailing_commas(text: str) -> str:
    """Trailing commaを除去する。"""
    # 文字列リテラル、trailing commaを正規表現で処理する
    pattern = re.compile(
        r'"(?:[^"\\]|\\.)*"'  # 文字列リテラル
        r"|,\s*(?=[}\]])",  # trailing comma
        re.DOTALL,
    )

    def replacer(m: re.Match) -> str:
        s = m.group(0)
        # 文字列リテラルはそのまま返す
        if s.startswith('"'):
            return s
        # trailing commaは改行を保持する
        return "\n" * s.count("\n")

    return pattern.sub(replacer, text)
