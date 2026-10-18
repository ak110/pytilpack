"""依存・extra・CLIの定義と利用文書の整合を検査する。

不足や過剰な記載があると読者が導入・機能選択を誤るため、所在を示してexit 1とする。
検査の入力を読み込めない場合はexit 2とする。
"""

import ast
import collections
import pathlib
import re
import sys
import tomllib
import typing

import yaml


def check(root: pathlib.Path) -> list[str]:
    """指定rootの定義と文書を照合し、不一致を返す。"""
    errors: list[str] = []
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    extras = project["optional-dependencies"]
    extra_modules = _definition(root / "scripts/check_extras_imports.py", "EXTRA_MODULES")
    commands = _definition(root / "pytilpack/cli/main.py", "_SUBCOMMANDS")
    guide = (root / "docs/guide/index.md").read_text(encoding="utf-8")
    config = yaml.safe_load((root / "mkdocs.yml").read_text(encoding="utf-8"))
    core_line = next(line for line in guide.splitlines() if line.startswith("コア依存:"))
    _compare(
        errors,
        "docs/guide/index.md:コア依存",
        {_dependency(dep) for dep in project["dependencies"]},
        {_dependency(dep) for dep in re.findall(r"`([^`]+)`", core_line)},
    )

    _compare(errors, "scripts/check_extras_imports.py:EXTRA_MODULES", set(extras) - {"all"}, set(extra_modules))
    union = {_dependency(dep) for name, deps in extras.items() if name != "all" for dep in deps}
    _compare(errors, "pyproject.toml:all", union, {_dependency(dep) for dep in extras["all"]})
    rows = _extra_rows(guide)
    _compare(errors, "docs/guide/index.md:extras一覧", set(extras), set(rows))
    for name, (modules, dependencies) in rows.items():
        if name not in extras:
            continue
        expected_modules = {module.removeprefix("pytilpack.") for module in extra_modules.get(name, ())}
        if name == "all":
            expected_modules = {"全モジュール"}
        _compare(errors, f"docs/guide/index.md:extra {name} 対象", expected_modules, modules)
        _compare(errors, f"docs/guide/index.md:extra {name} 依存", {_dependency(dep) for dep in extras[name]}, dependencies)
        if not extras[name] and "後方互換" not in _extra_line(guide, name):
            errors.append(f"docs/guide/index.md:extra {name}: 空extraの後方互換説明を記載してください")

    categories = _guide_categories(guide)
    public = _get_public_modules(root)
    api = {path.stem for path in (root / "docs/api").glob("*.md")}
    _compare(errors, "docs/api/", public, api)
    listed = [module for names in categories.values() for module in names]
    _compare(errors, "docs/guide/index.md:モジュール一覧", public, set(listed))
    duplicates = [name for name, count in collections.Counter(listed).items() if count != 1]
    if duplicates:
        errors.append(f"docs/guide/index.md: モジュールの重複を除いてください: {duplicates}")
    if len(categories) != 8:
        errors.append("docs/guide/index.md: モジュール一覧を指定の8分類へそろえてください")
    nav = next(item["APIリファレンス"] for item in config["nav"] if "APIリファレンス" in item)
    nav_categories = {
        name: [pathlib.PurePosixPath(path).stem for item in items for path in item.values()]
        for category in nav
        for name, items in category.items()
    }
    sections = next(
        plugin["llmstxt"]["sections"] for plugin in config["plugins"] if isinstance(plugin, dict) and "llmstxt" in plugin
    )
    llm_categories = {
        name: [pathlib.PurePosixPath(item if isinstance(item, str) else next(iter(item))).stem for item in items]
        for name, items in sections.items()
        if name in categories
    }
    for location, actual in (("mkdocs.yml:nav", nav_categories), ("mkdocs.yml:llmstxt sections", llm_categories)):
        if actual != categories:
            errors.append(f"{location}: 分類名と各分類のモジュールをdocs/guide/index.mdへそろえてください")
    llm_api = _get_llmstxt_modules(config)
    _compare(errors, "mkdocs.yml:llmstxt API", public, llm_api)

    required: dict[str, set[str]] = collections.defaultdict(set)
    for name, modules in extra_modules.items():
        if extras.get(name):
            for module in modules:
                if module.startswith("pytilpack."):
                    required[module.removeprefix("pytilpack.")].add(name)
    for module in api:
        text = (root / f"docs/api/{module}.md").read_text(encoding="utf-8")
        actual = set(re.findall(r"pip install pytilpack\[([\w-]+)\]", text))
        _compare(errors, f"docs/api/{module}.md:必要なextra", required.get(module, set()), actual)
    cli = (root / "docs/guide/cli.md").read_text(encoding="utf-8")
    headings = set(re.findall(r"^## `pytilpack ([\w-]+)`", cli, re.MULTILINE))
    _compare(errors, "docs/guide/cli.md:サブコマンド節", {name for name, _, _ in commands}, headings)
    for name, _, extra in commands:
        section = re.search(rf"^## `pytilpack {re.escape(name)}`.*?(?=^## |\Z)", cli, re.MULTILINE | re.DOTALL)
        if section and extra and f"pytilpack[{extra}]" not in section[0]:
            errors.append(f"docs/guide/cli.md:{name}: pytilpack[{extra}]の導入例を記載してください")
    return errors


def main() -> int:
    """リポジトリrootで検査を実行する。"""
    try:
        errors = check(pathlib.Path.cwd())
    except (OSError, ValueError, KeyError, StopIteration, yaml.YAMLError) as exc:
        print(
            f"整合検査の入力を読み込めません: {exc}。"
            "例外が示すファイル（pyproject.toml、docs/guide/index.md、docs/guide/cli.md、mkdocs.yml、"
            "scripts/check_extras_imports.pyのEXTRA_MODULES、pytilpack/cli/main.pyの_SUBCOMMANDS）の記載を修正して再実行する",
            file=sys.stderr,
        )
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


def _definition(path: pathlib.Path, name: str) -> typing.Any:
    """依存をimportせず、定義元のリテラルを読み取る。"""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            return ast.literal_eval(node.value)
    raise ValueError(f"{path}:{name}の定義がありません")


def _dependency(value: str) -> str:
    """版指定を除き、依存extraを保ったパッケージ指定を返す。"""
    name = re.split(r"[<>=!~; @]", value.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name.lower())


def _compare(errors: list[str], location: str, expected: set[str], actual: set[str]) -> None:
    if expected != actual:
        errors.append(
            f"{location}: 定義へそろえてください（不足={sorted(expected - actual)}, 過剰={sorted(actual - expected)}）"
        )


def _extra_line(text: str, name: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| `{name}` |"))


def _extra_rows(text: str) -> dict[str, tuple[set[str], set[str]]]:
    rows = {}
    for line in text.splitlines():
        if not re.match(r"\| `[\w-]+` \|", line):
            continue
        name, modules, deps = [cell.strip() for cell in line.strip("|").split("|")]
        names = {item.removeprefix("pytilpack.") for item in re.findall(r"`([^`]+)`", modules)}
        if "全モジュール" in modules:
            names = {"全モジュール"}
        rows[name.strip("`")] = (names, {_dependency(item) for item in re.findall(r"`([^`]+)`", deps)})
    return rows


def _guide_categories(text: str) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    current = None
    for line in text.split("## モジュール一覧\n", 1)[1].splitlines():
        if line.startswith("### "):
            current = line.removeprefix("### ")
            categories[current] = []
        elif current is not None:
            categories[current].extend(re.findall(r"\(\.\./api/(\w+)\.md\)", line))
    return categories


def _get_public_modules(root: pathlib.Path) -> set[str]:
    """pytilpackの全publicモジュール名を取得する。"""
    pkg = root / "pytilpack"
    modules: set[str] = set()
    # 直下の.pyファイル
    for f in sorted(pkg.glob("*.py")):
        name = f.stem
        if name == "__init__":
            continue
        # アンダースコア始まりはprivateモジュールのため除外
        if name.startswith("_"):
            continue
        modules.add(name)
    # サブパッケージ（cliは既存のdocs/guide/cli.mdがあるため除外）
    for d in sorted(pkg.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in ("__pycache__", "cli"):
            modules.add(d.name)
    return modules


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
    sys.exit(main())
