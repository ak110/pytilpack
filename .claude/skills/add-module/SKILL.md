---
name: add-module
description: Use when adding a new top-level module under pytilpack/ — either a single-file module pytilpack/<name>.py or a subpackage pytilpack/<name>/ (like pytilpack/asyncio/, pytilpack/sqlalchemy/). Walks through the required extras, docs/api/<name>.md (one file per top-level module, with show_submodules for subpackages), tests/<name>_test.py or tests/<name>/, README/docs/index extras table, and mkdocs.yml nav updates from CLAUDE.md so nothing is forgotten.
---

# pytilpack 新モジュール追加チェックリスト

pytilpackに新モジュールを追加する際、更新漏れが起きやすいポイントが複数箇所に分散している。
以下を上から順に実施し、最後に検証コマンドまで実行して完了とする。

## 0. 前提情報の整理

新モジュールについて以下を決める。

- モジュール形態: **単一ファイル** (`pytilpack/<name>.py`) か **サブパッケージ** (`pytilpack/<name>/`) か
  - 複数ファイルに分割したい場合や、ライブラリごとに名前空間を切りたい場合はサブパッケージにする
  - 既存例: 単一ファイル `pytilpack/openai.py` / サブパッケージ `pytilpack/sqlalchemy/`, `pytilpack/asyncio/`
- トップレベル名 `<name>` の確定
  - Pythonキーワードと衝突する場合はファイル名を `<name>_.py` にする（例: `pytilpack/json_.py` はない想定だが、将来的に衝突する場合）
- 必要なサードパーティextras（ベース依存で済む場合はextras追加不要）

## 1. 依存関係 (`pyproject.toml`)

サードパーティに依存する場合は `uv` コマンドで追加する（手編集はPreToolUse hookでブロック）。

```bash
uv add --optional <name> <library>
uv add --optional all <library>
```

- 対象モジュールが他のpytilpackモジュールをimportする場合、**推移的依存** も `<name>` extrasに含める必要がある
- `[all]` extrasには必ず同じパッケージを追加すること
- コア依存 (`[project.dependencies]`) は最小限に保つ方針。ベースパッケージに入れるのは原則禁止

## 2. docs/api

`docs/api/<name>.md` を作成する。トップレベル名1つにつき1ファイル。

単一ファイルモジュール:

````markdown
# pytilpack.<name>

!!! note "必要なextra"

    `pip install pytilpack[<name>]`

::: pytilpack.<name>
````

サブパッケージ (`show_submodules: true` で1ファイルに集約):

````markdown
# pytilpack.<name>

!!! note "必要なextra"

    `pip install pytilpack[<name>]`

::: pytilpack.<name>
    options:
      show_submodules: true
````

extras不要ならば `!!! note` ブロックは省略する (既存の `docs/api/json.md` 等を参照)。

## 3. テスト

配置規約（CLAUDE.mdより）:

- 単一ファイル `pytilpack/<name>.py` → `tests/<name>_test.py` (例: `pytilpack/json.py` → `tests/json_test.py`)
- サブパッケージ `pytilpack/<name>/foo.py` → `tests/<name>/foo_test.py` (例: `pytilpack/asyncio/` → `tests/asyncio/`)
- 万が一Pythonキーワードと衝突して `<name>_.py` を使う場合は、テストも `<name>_test.py`（アンダースコアは無視）。現時点で該当モジュールはなし

新しいpublic関数には必ずテストを書く。CRUDのような一連の流れは1つのテスト関数にまとめるのを優先する。既存の `tests/` ディレクトリから近い形式のものを選んで真似る。

## 4. extras 一覧の更新 (2 か所)

- `README.md` のextras一覧テーブル
- `docs/index.md` のextras一覧テーブル

両方に同じ行を追加すること。片方だけだと `scripts/check_docs_api.py` / CIで検出される。extras不要モジュールの場合も、ベースパッケージ側の箇条書きに追加する。

## 5. mkdocs.yml の更新 (2 か所)

`mkdocs.yml` の以下の **両方** に `api/<name>.md` を追加する。`scripts/check_docs_api.py` が両方を検査する。

- `nav:` → `APIリファレンス` の下
- `plugins:` → `llmstxt.sections` の該当カテゴリ（extras別の分類）

ファイル名のアルファベット順で並べるのが慣例。

## 6. 検証 (必須)

以下を順番に実行し、警告ゼロにする。

```bash
uv run python scripts/check_docs_api.py
uv run pyfltr run-for-agent
```

`uv run pyfltr run-for-agent` が通ったらコミットしてよい。

## よく使う参考ファイル

- `CLAUDE.md`（「モジュール追加時のextrasチェックリスト」の原典）
- `scripts/check_docs_api.py`（整合性チェックのロジック）
- 既存モジュール例（単一ファイル）: `pytilpack/openai.py` + `docs/api/openai.md` + `tests/openai_test.py`
- 既存モジュール例（サブパッケージ）: `pytilpack/sqlalchemy/` + `docs/api/sqlalchemy.md` + `tests/sqlalchemy/`
