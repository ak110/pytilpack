"""docs/api/ の整合性チェック。

pytilpackの全publicモジュールに対応するdocs/api/*.mdが存在するか検証する。
"""

import pathlib
import sys

pkg = pathlib.Path("pytilpack")
api = pathlib.Path("docs/api")

missing: list[str] = []

# 直下の.pyファイル
for f in sorted(pkg.glob("*.py")):
    name = f.stem
    if name == "__init__":
        continue
    if not (api / f"{name}.md").exists():
        missing.append(name)

# サブパッケージ（cliは既存のdocs/cli.mdがあるため除外）
for d in sorted(pkg.iterdir()):
    if (
        d.is_dir()
        and (d / "__init__.py").exists()
        and d.name not in ("__pycache__", "cli")
        and not (api / f"{d.name}.md").exists()
    ):
        missing.append(d.name)

if missing:
    print(f"docs/api/ に不足: {missing}", file=sys.stderr)
    sys.exit(1)

print("docs/api/ の整合性OK")
