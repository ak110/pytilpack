"""JSONC(JSON with Comments)関連。"""

import json
import pathlib
import re
import typing


def load(
    path: str | pathlib.Path,
    errors: str | None = None,
    strict: bool = False,
) -> typing.Any:
    """JSONCファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        return loads(path.read_text(encoding="utf-8", errors=errors))
    else:
        if strict:
            raise FileNotFoundError(f"File not found: {path}")
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
