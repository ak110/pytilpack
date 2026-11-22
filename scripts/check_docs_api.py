import ast
import collections
import pathlib
import re
import sys
import tomllib
import typing


def check(root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    extras = project["optional-dependencies"]
    extra_modules = _definition(root / "scripts/check_extras_imports.py", "EXTRA_MODULES")
    commands = _definition(root / "pytilpack/cli/main.py", "_SUBCOMMANDS")
    guide = (root / "docs/guide/index.md").read_text(encoding="utf-8")
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
    listed = [module for names in categories.values() for module in names]
    _compare(errors, "docs/guide/index.md:モジュール一覧", public, set(listed))
    duplicates = [name for name, count in collections.Counter(listed).items() if count != 1]
    if duplicates:
        errors.append(f"docs/guide/index.md: モジュールの重複を除いてください: {duplicates}")
    if len(categories) != 8:
        errors.append("docs/guide/index.md: モジュール一覧を指定の8分類へそろえてください")
    cli = (root / "docs/guide/cli.md").read_text(encoding="utf-8")
    headings = set(re.findall(r"^## `pytilpack ([\w-]+)`", cli, re.MULTILINE))
    _compare(errors, "docs/guide/cli.md:サブコマンド節", {name for name, _, _ in commands}, headings)
    for name, _, extra in commands:
        section = re.search(rf"^## `pytilpack {re.escape(name)}`.*?(?=^## |\Z)", cli, re.MULTILINE | re.DOTALL)
        if section and extra and f"pytilpack[{extra}]" not in section[0]:
            errors.append(f"docs/guide/cli.md:{name}: pytilpack[{extra}]の導入例を記載してください")
    return errors


def main() -> int:
    try:
        errors = check(pathlib.Path.cwd())
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print(
            f"整合検査の入力を読み込めません: {exc}。"
            "例外が示すファイル（pyproject.toml、docs/guide/index.md、docs/guide/cli.md、"
            "scripts/check_extras_imports.pyのEXTRA_MODULES、pytilpack/cli/main.pyの_SUBCOMMANDS）の記載を修正して再実行する",
            file=sys.stderr,
        )
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


def _definition(path: pathlib.Path, name: str) -> typing.Any:
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
            categories[current].extend(re.findall(r"^- `pytilpack\.(\w+)`", line))
    return categories


def _get_public_modules(root: pathlib.Path) -> set[str]:
    pkg = root / "pytilpack"
    modules: set[str] = set()
    for f in sorted(pkg.glob("*.py")):
        name = f.stem
        if name == "__init__":
            continue
        if name.startswith("_"):
            continue
        modules.add(name)
    for d in sorted(pkg.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in ("__pycache__", "cli"):
            modules.add(d.name)
    return modules


if __name__ == "__main__":
    sys.exit(main())
