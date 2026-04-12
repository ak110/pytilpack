"""docs/api/ の整合性チェック。

pytilpackの全publicモジュールに対応するdocs/api/*.mdが存在し、
docs/guide/index.md・mkdocs.yml nav・mkdocs.yml llmstxt sectionsの3箇所で
同期されているか検証する。
"""

import pathlib
import re
import sys
import typing

import yaml


def main() -> None:
    """メイン処理。"""
    public_modules = _get_public_modules()
    docs_api_files = _get_docs_api_files()
    index_modules = _get_index_md_modules()
    config = yaml.safe_load(pathlib.Path("mkdocs.yml").read_text(encoding="utf-8"))
    nav_modules = _get_nav_modules(config)
    llmstxt_modules = _get_llmstxt_modules(config)

    errors: list[str] = []

    # publicモジュール → docs/api/*.md
    missing_api = public_modules - docs_api_files
    if missing_api:
        errors.append(f"docs/api/ に不足: {sorted(missing_api)}")

    # docs/api/*.md → docs/guide/index.md
    missing_index = docs_api_files - index_modules
    if missing_index:
        errors.append(f"docs/guide/index.md に不足: {sorted(missing_index)}")

    # docs/api/*.md → mkdocs.yml nav
    missing_nav = docs_api_files - nav_modules
    if missing_nav:
        errors.append(f"mkdocs.yml nav に不足: {sorted(missing_nav)}")

    # docs/api/*.md → mkdocs.yml llmstxt sections
    missing_llmstxt = docs_api_files - llmstxt_modules
    if missing_llmstxt:
        errors.append(f"mkdocs.yml llmstxt sections に不足: {sorted(missing_llmstxt)}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print("docs/api/ の整合性OK")


def _get_public_modules() -> set[str]:
    """pytilpackの全publicモジュール名を取得する。"""
    pkg = pathlib.Path("pytilpack")
    modules: set[str] = set()
    # 直下の.pyファイル
    for f in sorted(pkg.glob("*.py")):
        name = f.stem
        if name == "__init__":
            continue
        modules.add(name)
    # サブパッケージ（cliは既存のdocs/guide/cli.mdがあるため除外）
    for d in sorted(pkg.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in ("__pycache__", "cli"):
            modules.add(d.name)
    return modules


def _get_docs_api_files() -> set[str]:
    """docs/api/配下の.mdファイルからモジュール名を取得する。"""
    api = pathlib.Path("docs/api")
    return {f.stem for f in api.glob("*.md")}


def _get_index_md_modules() -> set[str]:
    """docs/guide/index.mdから../api/xxx.mdへのリンクを抽出してモジュール名を取得する。"""
    text = pathlib.Path("docs/guide/index.md").read_text(encoding="utf-8")
    return set(re.findall(r"\(\.\./api/(\w+)\.md\)", text))


def _get_nav_modules(config: dict[str, typing.Any]) -> set[str]:
    """mkdocs.ymlのnavからAPIリファレンス配下のモジュール名を取得する。"""
    modules: set[str] = set()
    nav = config.get("nav", [])
    for item in nav:
        if isinstance(item, dict) and "APIリファレンス" in item:
            _collect_nav_api_paths(item["APIリファレンス"], modules)
    return modules


def _collect_nav_api_paths(items: list[typing.Any], modules: set[str]) -> None:
    """navのネスト構造からapi/配下のパスを再帰的に収集する。"""
    for item in items:
        if isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str) and value.startswith("api/"):
                    modules.add(pathlib.PurePosixPath(value).stem)
                elif isinstance(value, list):
                    _collect_nav_api_paths(value, modules)


def _get_llmstxt_modules(config: dict[str, typing.Any]) -> set[str]:
    """mkdocs.ymlのllmstxt sectionsからapi/配下のモジュール名を取得する。"""
    modules: set[str] = set()
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and "llmstxt" in plugin:
            sections = plugin["llmstxt"].get("sections", {})
            for items in sections.values():
                for item in items:
                    # 文字列("api/xxx.md")またはdict({"api/xxx.md": "説明"})
                    path = item if isinstance(item, str) else next(iter(item))
                    if path.startswith("api/"):
                        modules.add(pathlib.PurePosixPath(path).stem)
    return modules


if __name__ == "__main__":
    main()
