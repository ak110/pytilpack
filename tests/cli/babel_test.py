import gettext
import subprocess
import sys
from pathlib import Path


def test_babel_cli_catalog_lifecycle(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    messages = source / "messages.py"
    messages.write_text('_("hello")\n', encoding="utf-8")
    template = tmp_path / "messages.pot"
    locales = tmp_path / "locales"

    def run(*args: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "pytilpack.cli.main", "babel", *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr

    run("extract", str(source), "--output", str(template))
    assert 'msgid "hello"' in template.read_text(encoding="utf-8")

    run("init", "--locale", "ja", "--input-file", str(template), "--output-dir", str(locales))
    catalog = locales / "ja" / "LC_MESSAGES" / "messages.po"
    original_catalog = catalog.read_text(encoding="utf-8")
    assert 'msgid "hello"\nmsgstr ""' in original_catalog
    catalog.write_text(
        original_catalog.replace('msgid "hello"\nmsgstr ""', 'msgid "hello"\nmsgstr "こんにちは"'), encoding="utf-8"
    )

    messages.write_text('_("hello")\n_("welcome")\n', encoding="utf-8")
    run("extract", str(source), "--output", str(template))
    run("update", "--input-file", str(template), "--output-dir", str(locales))
    assert 'msgid "welcome"' in catalog.read_text(encoding="utf-8")

    run("compile", "--directory", str(locales))
    with catalog.with_suffix(".mo").open("rb") as file:
        assert gettext.GNUTranslations(file).gettext("hello") == "こんにちは"
