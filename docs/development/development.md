# 開発手順

## エージェントの共通品質基準

Claude Codeでは`claude plugin marketplace add ak110/dotfiles`の後に
`claude plugin install agent-basics@ak110-dotfiles`で共通品質スキルを導入する。
Codexでは`codex plugin marketplace add ak110/dotfiles`を実行し、`/plugins`から
`agent-basics@ak110-dotfiles`をインストールする。
リポジトリの`.claude/settings.json`と`.codex/config.toml`は導入済みプラグインを有効化する共有設定である。
Codexでは信頼したプロジェクトの設定が読み込まれる。
AGENTS.mdが指定する`writing-standards`・`review-standards`と該当するreferencesを読む。
個人用のagent-toolkitは任意で利用できる。
導入仕様は[Claude Code](https://code.claude.com/docs/en/discover-plugins)と
[Codex](https://developers.openai.com/plugins/build/plugins)の公式資料を参照する。

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. セットアップを実行する

    ```bash
    make setup
    ```

## 開発コマンド

| コマンド | 用途 |
| --- | --- |
| `make format` | 整形 + 軽量lint + 自動修正（開発時の手動実行用）。実行前に仮想環境を`uv.lock`と`.python-version`の版へ同期する |
| `make test` | 全チェック実行（コミット前の最終確認用）。実行前に`make format`と同じ同期を行う |
| `make update` | 依存更新 |
| `make docs` | ドキュメントのローカルプレビュー（`http://127.0.0.1:8000/`） |

## サプライチェーン攻撃対策

ロックファイル尊重・公開待機・ピン留め運用の3点を基本方針とする。

- `uv.lock`をそのまま使うため`UV_FROZEN=1`を常時有効化している
- `pyproject.toml`の`exclude-newer`で公開直後パッケージの即時導入を抑制している
- GitHub Actionsは`pinact`でハッシュピン留めし、定期更新している

依存の追加・更新は`uv add`/`uv remove`/`uv lock --upgrade-package`で行う。

依存パッケージの脆弱性検知の仕組み（Dependabot alerts・定期監査ワークフロー）は設けない。
本リポジトリはライブラリであり`uv.lock`は開発専用のため、利用者の実行環境への脆弱性の影響は限定的である。

`pyproject.toml`の`[tool.uv] override-dependencies`による上書きは本リポジトリの依存解決にのみ適用され、
配布物のメタデータには含まれない。
上流パッケージの厳密ピンにより依存更新だけでは問題を解消できない場合の上書きによる迂回の採否は、
`agent-basics:writing-standards`の`references/dependency-management.md`を参照する。
同スキルでは、利用者環境へ波及する脆弱性は上書きで迂回せず、上流の追従を待つ。
開発時にのみ用いる依存は上書きで迂回してよく、判断の根拠と解除条件をコメントへ残す。
本リポジトリでの依存の分類と検証は、以下の「依存の版制約を変更する場合の確認手順」に従う。
`[project.dependencies]`と`[project.optional-dependencies]`が宣言する依存、および
それらから推移的に解決される依存は利用者環境へ波及する。
開発用の依存グループ経由でのみ入る依存は利用者環境へ波及しない。

### 依存の版制約を変更する場合の確認手順

`pyproject.toml`の`dependencies`・`optional-dependencies`・`override-dependencies`で
版指定を変更する場合は、以下の手順で確認する。

1. 依存を更新する場合は、既存の`override-dependencies`を全件確認する。
    各指定の付随コメントに記録した迂回理由と解除条件が、現行の依存グラフでも成立するかを再点検する。
    逆依存は`uv tree --locked --universal --invert --package <名前>`で確認する。
    対象が依存グラフにない場合もコマンドは終了コード0となり、依存ツリーを出力しない。
    終了コードではなく、出力に迂回対象の依存元が含まれるかで指定の要否を判断する。
    前提を失った指定は撤去し、`uv lock`でロックファイルを再生成する。

2. 変更対象パッケージの逆依存を全件確認する。
    `uv tree --locked --universal --invert --package <名前>`で逆依存を列挙し、
    各逆依存がPyPIの`requires_dist`で課す制約を個別に確認する。
    依存解決は複数制約の連立であり、上限制約を課す逆依存が1件でもあれば、
    他の逆依存が下限を引き上げても解決は成立しない。
    単一パッケージのメタデータだけを根拠に版の引き上げ可否を判断しない。

3. `override-dependencies`を追加または変更する場合は、逆依存を2つに分類する。
    実行時依存と開発用依存をそれぞれ確認する。
    `uv tree --locked --universal --no-dev --invert --package <名前>`が`pytilpack`へ到達する場合、
    到達したパッケージは利用者環境へ波及する実行時依存である。
    到達しない場合は開発用の依存グループ経由でのみ入る依存である。

4. ロックファイルの再解決範囲を意識して版を反映する。
    `uv lock`は制約が緩んでも既存のロック内容を保持し、自動では版を上げない。
    特定パッケージの引き上げは`uv lock --upgrade-package <名前>`、全体更新は`uv lock --upgrade`を指定する。
    制約を変更したのに版が変わらない場合は、他の依存の制約が原因だと判断する前に、再解決の範囲を確認する。

5. 配布物をインストールする流れで依存解決が成立するかを、コマンドを実行して確かめる。
    `uv lock`・`uv sync`・`uv run`の成功だけでは、配布物をインストールする処理が成立するかを確認できない。
    上書き設定が適用されない状態で依存解決が成立することを
    `env --unset=UV_OVERRIDE uvx --no-config --exclude-newer "1 day" --from . pytilpack --help`を実行して確かめる。
    この確認コマンドは利用者環境と同じ流れで配布物の依存を解決するため、
    上書き設定に依存した版指定を検出できる。
    `--no-config`で設定ファイルの探索を無効化し、`env --unset=UV_OVERRIDE`で環境変数による上書きも無効化する。
    この指定では`pyproject.toml`の`exclude-newer`が適用されない。
    公開待機を維持するため`--exclude-newer`を明示する。
    このコマンドが解決するのは配布物のメタデータが宣言する実行時依存に限る。
    extrasは導入しないため、`optional-dependencies`の版指定を変更した場合は、
    対象extraを含む形でもコマンドを実行して確かめる。
    対応するCLIサブコマンドがある場合は、次の形式で機能別に確認する。

    ```bash
    env --unset=UV_OVERRIDE uvx --no-config --exclude-newer "1 day" --from "pytilpack[<extra名>] @ ." pytilpack <サブコマンド> --help
    ```

    対応サブコマンドがない依存の場合は、次の形式で対象extraを導入して共通の処理の流れを検証する。

    ```bash
    env --unset=UV_OVERRIDE uvx --no-config --exclude-newer "1 day" --from "pytilpack[<extra名>] @ ." pytilpack --help
    ```

    開発用の依存グループだけに適用される上書きは観測できない。
    `make test`ではpyfltr本体が`uvx`の解決した独立環境で動き、pytestなどのPython系ツールは
    実行前に`uv.lock`へ同期した本リポジトリの仮想環境で動く。
    どちらの環境も配布物をインストールする流れを通らないため、配布物の依存が解決できない問題を検出しない。
    コマンドの実行が失敗した場合は原因を確認する。
    通信障害・パッケージ索引の障害・ビルド環境の不備など、版指定以外の原因を解消して再度確かめる。
    変更した版指定に起因する依存解決不能を確認した場合は、配布物のインストールを不能にするため
    依存を解決できない版指定は採用しない。

6. 開発環境側でツールが起動することを実行して確かめる。
    `override-dependencies`の追加・変更・撤去は開発環境の依存解決にも影響する。
    上書きにより開発用の依存グループが要求する版が満たされなくなると、上書き対象のパッケージを使う
    開発用ツールが起動しなくなる。前段のどの手順もこの不成立を観測しない。
    上書きを追加・変更・撤去した場合は、`uv lock`で変更をロックファイルへ反映したうえで、
    上書き対象のパッケージへ依存する開発用ツールを`uv run --locked <ツール名> --help`のような
    軽量な指定で変更後のロックから起動し、終了コードが0になることを確かめる。
    `--locked`は`uv.lock`が変更されないことを表明する指定であり、
    ロックファイルへ未反映の変更が残っている場合に実行を失敗させる。
    `--frozen`はロックを更新せずに実行するため、上書きの変更直後は旧ロック由来の環境を観測し、
    起動不能を検出できない。この確認に`--frozen`を用いない。
    起動しない状態を許容する場合は、影響範囲・許容する理由・解除条件を
    変更した`pyproject.toml`の`override-dependencies`のコメントへ残す。

7. 実行時依存へ到達するパッケージのAPIを検証する。
    依存解決の成立は、版を変更したパッケージのAPIに関する機能上の非互換を観測しない。
    逆依存の確認で実行時依存への到達を認めた場合は、そのパッケージのAPIを読み込む処理の流れを特定し、
    最小の実行または対応するテストで検証する。
    コア依存の`mcp`では`pytilpack/cli/mcp.py`が該当するため、
    `uv run --locked pytilpack mcp --help`の終了コードが0であることと、
    `tests/cli/mcp_test.py`が成功することを実行して確かめる。

## ドキュメントサイト運用

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

### モジュールの追加・変更

1. 対応する実装とテストを、[アーキテクチャ](architecture.md)の「テスト規約」に従って追加する
2. 任意依存を使う場合は`pyproject.toml`のextraと`all`へ直接依存を宣言し、`scripts/check_extras_imports.py`の`EXTRA_MODULES`へ対応するモジュールを加える
3. `docs/api/<name>.md`へmkdocstringsの設定と必要なextra・プラットフォームの注記を記載する
4. `docs/guide/index.md`のextra表とモジュール分類を更新し、`mkdocs.yml`のnavとllmstxt sectionsを同じ分類へそろえる。CLIは`_SUBCOMMANDS`と`docs/guide/cli.md`へ加える
5. `uv run --frozen python scripts/check_docs_api.py`で対応情報と定義元の一致を確かめる。`uv build --wheel --out-dir <空の出力ディレクトリ>`でwheelを作成する。生成されたwheelのパスを`uv run --frozen python scripts/check_extras_imports.py <wheelのパス>`へ渡して単独extraのimportを確かめる
6. `make test`と`uv run --frozen mkdocs build --strict`で実装とAPI文書を検証する

対応情報の不足・過剰・分類の不一致では、pre-commitとCIが失敗して所在を表示する。
エージェントの追加作業は`add-module`スキル、既存対応の変更は`check-module-sync`スキルも同じ手順へ接続する。

## リリース手順

事前に`gh`コマンドをインストールして`gh auth login`でログインし、以下のコマンドのいずれかを実行。

```bash
gh workflow run release.yaml --field="bump=PATCH"
gh workflow run release.yaml --field="bump=MINOR"
gh workflow run release.yaml --field="bump=MAJOR"
```

<https://github.com/ak110/pytilpack/actions>で状況を確認できる。
