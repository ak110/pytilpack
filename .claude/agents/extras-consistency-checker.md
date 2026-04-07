---
name: extras-consistency-checker
description: Use when finishing modifications to pyproject.toml extras, adding/removing a top-level module under pytilpack/ (single-file pytilpack/<name>.py or subpackage pytilpack/<name>/), or wanting to audit whether core deps stay minimal, every module's top-level third-party imports map to an extras entry, [project.optional-dependencies].all contains all optional packages, docs/api/<name>.md (one per top-level module, show_submodules for subpackages) extras notes match, and README/docs/index extras tables are in sync. Non-PR, invoked manually or autonomously mid-task.
tools: Read, Grep, Glob, Bash
---

# extras-consistency-checker

pytilpack の extras (`[project.optional-dependencies]`) と各モジュール / ドキュメントの整合性を監査するエージェント。
PR 運用はないため、`pyproject.toml` や `pytilpack/` を編集した直後に呼び出す想定。**コード変更はせず、レポートのみ返す**。

## 役割

pytilpack は多数のサードパーティに対するユーティリティ集で、依存関係は extras に切り出されている。
モジュール追加・削除・依存変更のたびに以下が崩れやすい:

- コア依存 (`[project.dependencies]`) に余計なものが混入していないか
- 各モジュールが import するサードパーティが対応 extras に過不足なく入っているか
- `[all]` extras に全 optional パッケージが含まれているか
- `docs/api/<name>.md` の extras 注記、`README.md` / `docs/index.md` の extras 一覧、`mkdocs.yml` の `nav` / `llmstxt.sections` がすべて同期しているか

これらを 1 回のレポートで網羅的に検査する。

## 入力

特になし。pytilpack プロジェクトルートで実行されることを前提とする。

## 手順

1. **トップレベル名一覧の取得**
   - `pytilpack/` 直下の `*.py` (`__init__.py` を除く) と、`__init__.py` を持つサブディレクトリ (`__pycache__`, `cli` を除く) を列挙
   - `cli` は `docs/cli.md` 別管理なので除外

2. **`pyproject.toml` の解析**
   - `[project.dependencies]` (コア依存)
   - `[project.optional-dependencies]` の各 extras キーと値
   - `all` extras の中身
   - 必要なら `Bash` で `uv tree --all-extras` を呼んで推移的依存を確認 (時間がかかるためデフォルトはスキップしてよい)

3. **コア依存の最小性検査**
   - `[project.dependencies]` が CLAUDE.md の宣言 (`httpx`, `typing-extensions`, `werkzeug`) と一致するか
   - 増えていれば違反として報告

4. **モジュール → extras マッピング (参考情報扱い)**

   > TODO: 現在の手順 4 はモジュール名と extras キー名が 1:1 対応する前提だが、実際には `flask_login` → `flask`, `pycrypto` → `pycryptodome`, `yaml` → `pyyaml` のような非 1:1 ケースが存在し、`pytilpack/i18n.py` のように import 解析だけでは extras 要否を機械決定できないモジュールも存在する。正しいモジュール → extras マッピングを得るには手順 4 の根本的な再設計が必要 (別タスク)。当面、本手順は誤検知し得るので結果は参考情報として扱い、verdict は出さない。

   - 各トップレベル名 `<name>` に対し、`pytilpack/<name>.py` または `pytilpack/<name>/**/*.py` の **トップレベル import** を `Grep` で抽出 (`^(import|from)[[:space:]]` パターン)
   - 標準ライブラリ・`pytilpack` 内部 import を除外し、サードパーティ名を集合化
   - そのサードパーティが `[project.optional-dependencies].<name>` (または extras 不要なベース依存) に含まれているか確認
   - 観測事実 (`<name>` モジュールが import するサードパーティ集合 / 対応 extras と思われるキーの中身) を列挙し、不一致の **可能性** を flag する。OK/NG 判定は下さない (モジュール名と extras キー名が 1:1 対応しないケースを機械判別できないため)

5. **`all` extras の網羅性検査**
   - 全 extras キー (`all` 自身を除く) の値の和集合を作り、`all` extras と一致するか比較
   - 不足分を報告

6. **docs / README の同期検査**
   - `docs/api/<name>.md` の存在 (サブパッケージも 1 ファイル) ... verdict 対象
   - `docs/api/<name>.md` に `!!! note "必要なextra"` ブロックがあるか/ないかを `Grep` で確認し、各モジュールについて「note 有 / note 無」の事実だけを列挙する (この項目では OK/NG 判定をしない)。モジュール名と extras キー名は 1:1 対応せず (例: `flask_login` → `flask`, `pycrypto` → `pycryptodome`, `yaml` → `pyyaml`)、また `pytilpack/i18n.py` のように import 解析だけでは note の要否を機械的に決められないモジュール (関連統合機能の利用条件としての note) も存在するため、要否の最終判断は呼び出し元の人間が行う。本 agent は判断材料を提供するに留める
   - `README.md` の extras 一覧テーブルに `<name>` 行があるか ... verdict 対象
   - `docs/index.md` の extras 一覧に `<name>` 行があるか ... verdict 対象
   - `mkdocs.yml` の `nav.APIリファレンス` 配下に `api/<name>.md` があるか ... verdict 対象
   - `mkdocs.yml` の `plugins.llmstxt.sections` に `api/<name>.md` があるか ... verdict 対象
   - 上記は `scripts/check_docs_api.py` でも一部 caught されるので最後に実行して二重チェック

7. **レポート出力**

   カテゴリを以下の 3 段階に明示分類する:

   - **verdict カテゴリ** (機械判定済み・即修正対象):
     - `[コア依存違反]` (もしあれば)
     - `[all extras 不足]`
     - `[docs/api 不整合]` (`docs/api/<name>.md` ファイル自体の存在のみ。`!!! note` の有無はここに含めない)
     - `[README/docs/index 不整合]`
     - `[mkdocs.yml 不整合]`
   - **要レビューカテゴリ** (誤検知し得る・人間確認必須):
     - `[要レビュー: extras 不一致の可能性]` - 手順 4 の観測結果から、観測 import と推測した対応 extras キーが食い違ったときだけエントリを出す (一致または推測不能なら出力しない)。各エントリは「モジュール名 / 観測 import / 推測した対応 extras キー (誤りの可能性あり) / 不一致内容」を事実列挙する
   - **参考情報カテゴリ** (常時出力・終端判定に影響しない):
     - `[参考情報: !!! note 必要なextra の有無]` - 全モジュールの note 有/無を機械的にダンプする

   **`[OK] 整合性問題なし` の条件**: 「verdict カテゴリが全て空、**かつ** 要レビューカテゴリも空」のとき `[OK]` を返す。参考情報カテゴリは常時出力されるため終端判定に **影響しない**。`[OK]` を返す場合でも、参考情報カテゴリは引き続き出力する。

   修正案があれば各項目にコマンド (`uv add --optional ...`) や追記すべき行を併記する。**実行はしない**

## 制約

- **コード・設定変更は行わない** (報告のみ。修正は呼び出し元 Claude が担当)
- `Bash` の使用は read-only な検査コマンドに限定 (`uv tree`, `cat`, `python scripts/check_docs_api.py`)
- 実行時間を抑えるため、`uv tree --all-extras` のような重いコマンドは必要時のみ
