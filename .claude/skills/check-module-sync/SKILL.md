---
name: check-module-sync
description: >
  Use when editing any file under pytilpack/<name>.py or pytilpack/<name>/ (subpackages like
  pytilpack/asyncio/, pytilpack/sqlalchemy/ count as a single module <name>). Verifies
  docs/api/<name>.md exists, its 必要なextra note matches pyproject.toml,
  [project.optional-dependencies].all includes every optional package the module pulls in,
  README/docs/index extras tables are current, and mkdocs.yml nav and llmstxt sections contain it.
---

# check-module-sync

pytilpackの既存モジュールを編集したとき、関連するドキュメント・extras・テストの整合性が崩れていないか
確認するためのチェックリスト。
編集ファイルから **トップレベル名** を特定し、その単位で同期を確認する。

## トップレベル名の特定方法

編集対象パス → トップレベル名 `<name>` の対応:

- `pytilpack/<name>.py` → `<name>`（単一ファイルモジュール）
- `pytilpack/<name>/...` → `<name>` (サブパッケージ。例: `pytilpack/sqlalchemy/types.py` → `sqlalchemy`)
- `pytilpack/cli/...` → `cli`（`docs/guide/cli.md` が別管理。本skillのチェック対象外）
- `pytilpack/__init__.py` → 対象外

## チェック項目

### 1. `docs/api/<name>.md` の存在

サブパッケージでも1ファイルにまとめる規約 (`show_submodules: true` 付き)。
存在しなければ `add-module` skillの手順に従って作成する。

### 2. extras 注記の整合性

サードパーティに依存するモジュールであれば `docs/api/<name>.md` に以下のような注記が入っているはず:

```markdown
!!! note "必要なextra"

    `pip install pytilpack[<name>]`
```

`pyproject.toml` の `[project.optional-dependencies]` に `<name>` が定義されていることを確認。
extras不要モジュール（ベース依存のみで動く）ならばこの注記がないことを確認。

### 3. `[project.optional-dependencies].all` の網羅

`<name>` extrasの各パッケージが `all` extrasにも含まれていることを `pyproject.toml` で確認。
`uv add --optional all <library>` を打ち忘れているケースがある。

### 4. トップレベル import との突き合わせ

`pytilpack/<name>.py`（または `pytilpack/<name>/**/*.py`）の **トップレベル import** を
`grep -E '^(import|from)' pytilpack/<name>...'` で抽出する。
サードパーティ（`pytilpack` / 標準ライブラリ以外）が `<name>` extrasに過不足なくマッピングされているか確認する。

`.pylintrc` で `import-outside-toplevel` が有効なため、関数内importは基本的にない前提でOK。

### 5. extras 一覧テーブル

- `README.md` のextras一覧テーブルに `<name>` 行があるか
- `docs/index.md` のextras一覧に `<name>` 行があるか

### 6. mkdocs.yml の同期

- `nav:` → `APIリファレンス` 下に `api/<name>.md` があるか
- `plugins:` → `llmstxt.sections` のカテゴリに `api/<name>.md` があるか

### 7. テストの存在

- `tests/<name>_test.py` または `tests/<name>/` があるか
- 編集したpublic関数に対応するテストがあるか（新規publicは必ずテスト追加）

### 8. 整合性チェックスクリプトの実行

```bash
uv run python scripts/check_docs_api.py
```

これが警告を出さなければ最低限の整合性はOK。

## 不整合が見つかったとき

- 単純な追記漏れ (`README.md` / `docs/index.md` / `mkdocs.yml`) はそのまま修正
- extrasの構成変更が必要なら `uv add --optional ...` / `uv remove --optional ...` を使う（手編集禁止）
- ドキュメント追加が必要なら `add-module` skillを参照
