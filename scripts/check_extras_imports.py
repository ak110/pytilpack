"""配布wheelの各extraを単独導入し、importに必要な依存がそろうことを検証する。

依存不足は配布モジュールを利用できなくするためエラーとする。
開発依存や他のextraによる補完を避けるため、uvの隔離環境とPythonの隔離モードを使う。
"""

import argparse
import email
import pathlib
import subprocess
import sys
import zipfile

# 対応名が異なるモジュールと、複数モジュールを提供するextraも検証する。
EXTRA_MODULES = {
    "babel": ("pytilpack.babel", "pytilpack.i18n"),
    "bleach": ("bleach",),
    "environ": ("pytilpack.environ",),
    "fastapi": ("pytilpack.fastapi",),
    "flask": ("pytilpack.flask", "pytilpack.flask_login"),
    "htmlrag": ("pytilpack.htmlrag",),
    "markdown": ("pytilpack.markdown",),
    "mcp": ("pytilpack.cli.mcp",),
    "msal": ("pytilpack.msal",),
    "pycryptodome": ("pytilpack.pycrypto",),
    "pydantic": ("pytilpack.pydantic",),
    "pytest": ("pytilpack.pytest",),
    "pyyaml": ("pytilpack.yaml",),
    "quart": ("pytilpack.quart", "pytilpack.quart_auth"),
    "sqlalchemy": ("pytilpack.sqlalchemy",),
    "tiktoken": ("pytilpack.tiktoken",),
    "tqdm": ("pytilpack.tqdm",),
    "web": ("pytilpack.web",),
}


def main() -> int:
    """各extraの隔離import検証を実行する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=pathlib.Path)
    parser.add_argument("--extra", action="append", default=None, help="検証するextra。省略時はベースと全extra")
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        metadata_path = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = email.message_from_bytes(archive.read(metadata_path))
        extras = set(metadata.get_all("Provides-Extra", []))
        modules = sorted(
            {
                name[:-3].replace("/", ".").removesuffix(".__init__")
                for name in archive.namelist()
                if name.startswith("pytilpack/") and name.endswith(".py")
            }
        )

    if extras != set(EXTRA_MODULES) | {"all"}:
        print("wheelのextrasと検証対象が一致しません。EXTRA_MODULESを配布モジュールへ合わせてください。", file=sys.stderr)
        return 1

    optional_modules = {module for names in EXTRA_MODULES.values() for module in names}
    base_modules = [
        module
        for module in modules
        if module.count(".") <= 1 and not module.startswith("pytilpack._") and module not in optional_modules
    ]
    selections = args.extra if args.extra is not None else ["", *sorted(extras)]
    failed = False
    for extra in selections:
        if extra == "all":
            selected_modules = modules
        elif extra:
            if extra not in EXTRA_MODULES:
                parser.error(f"未定義のextra: {extra}")
            selected_modules = list(EXTRA_MODULES[extra])
        else:
            selected_modules = base_modules
        requirement = f"pytilpack[{extra}] @ {wheel.as_uri()}" if extra else wheel.as_uri()
        command = [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            "--python",
            sys.executable,
            "--with",
            requirement,
            "python",
            "-I",
            "-c",
            "import importlib, sys; [importlib.import_module(name) for name in sys.argv[1:]]",
            *selected_modules,
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=180)
        if result.returncode:
            failed = True
            print(
                f"extra {extra or 'ベース'} のimportに失敗しました。依存宣言と対象モジュールを確認してください。\n"
                f"{result.stdout}{result.stderr}",
                file=sys.stderr,
            )
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
