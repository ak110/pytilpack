# CLAUDE.md: pytilpack

主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用し、利用者は必要なモジュールだけ取り込む。

## 開発手順

コミット前の検証方法: `make test`（特定ファイルに限定する場合は`uvx pyfltr run <path>`）

## アーキテクチャの参照先

[docs/development/architecture.md](docs/development/architecture.md) —
モジュール構成方針・extrasマッピング・テスト配置規約など

## 実装上の不変条件・コーディング規約

- コア依存（`[project.dependencies]`）は最小限に保つ（現在: `beautifulsoup4`/`httpx`/`mcp`/`werkzeug`）
- サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する
- 依存パッケージのトップレベル以外のサブモジュールパスをimport文で直接指定する場合は、
  上流のメジャー更新で当該パスが変わる可能性があるため版指定に上限を設ける。
  現行の該当依存は`mcp<2`と`werkzeug<4`である。
  トップレベルの公開APIだけを利用する依存には上限を設けず、上流の更新を利用者が選べる状態を保つ。
  全依存への一律の上限付与はしない
- インポートは原則トップレベルで行う（`pyproject.toml`の`[tool.pylint."messages control"]`で`import-outside-toplevel`は有効）
- ファイル作成時に厳密なパーミッションを固定する必要がある場合（umask非依存）は
  `os.open(..., mode=0o600)`等で作成時点から確定させる。
  `pathlib.Path.open`+`chmod`の二段では作成→`chmod`の隙間で他プロセスがファイルを開ける
  時間窓が生じる（`pytilpack/secrets.py`が該当）

### モジュール→extrasキーマッピング（要点）

モジュール名とextrasキー名が異なる主なケース（詳細は`architecture.md`参照）:

- `pytilpack.pycrypto` → `pycryptodome`
- `pytilpack.yaml` → `pyyaml`
- `pytilpack.flask_login` / `pytilpack.quart_auth` / `pytilpack.i18n` → それぞれ`flask`/`quart`/`babel`に含まれる

上記以外は原則としてモジュール名とextrasキー名が一致する。
`.claude/agents/extras-consistency-checker.md`はこのマッピングを参照して判定する。

## 注意点

- モジュール追加時は必ず`/add-module`スキルを使用
