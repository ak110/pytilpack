# CLAUDE.md: pytilpack

主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用し、利用者は必要なモジュールだけ取り込む。

## 開発手順

コミット前の検証方法: `uvx pyfltr run-for-agent`

## アーキテクチャの参照先

[docs/development/architecture.md](docs/development/architecture.md) — モジュール構成方針・extrasマッピング・テスト配置規約など

## 実装上の不変条件・コーディング規約

- コア依存（`[project.dependencies]`）は最小限に保つ（現在: `beautifulsoup4`/`httpx`/`mcp`/`werkzeug`）
- サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する
- インポートは原則トップレベルで行う（`.pylintrc`で`import-outside-toplevel`は有効）

### モジュール→extrasキーマッピング（要点）

モジュール名とextrasキー名が異なる主なケース（詳細は`architecture.md`参照）:

- `pytilpack.pycrypto` → `pycryptodome`
- `pytilpack.yaml` → `pyyaml`
- `pytilpack.flask_login` / `pytilpack.quart_auth` / `pytilpack.i18n` → それぞれ`flask`/`quart`/`babel`に含まれる

上記以外は原則としてモジュール名とextrasキー名が一致する。
`.claude/agents/extras-consistency-checker.md`はこのマッピングを参照して判定する。

## 注意点

- モジュール追加時は必ず`/add-module`スキルを使用する
