# CLAUDE.md: pytilpack

主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用し、利用者は必要なモジュールだけ取り込む。

## 開発手順

コミット前の検証方法: `make test`（特定ファイルに限定する場合は`uvx pyfltr run <path>`）

## アーキテクチャの参照先

[docs/development/architecture.md](docs/development/architecture.md)は、
モジュール構成方針・extrasマッピング・テスト配置規約などを定める。

## 実装上の不変条件・コーディング規約

- コア依存（`[project.dependencies]`）は最小限に保つ（現在: `beautifulsoup4`/`httpx`/`mcp`/`werkzeug`）。
  ただし`mcp`は多数の推移的依存（`httpx2`・`mcp-types`・`starlette`・`uvicorn`・`pydantic`・
  `pyjwt`・`opentelemetry-api`・`jsonschema`・`python-multipart`・`sse-starlette`）を持ち込む。
  MCPサーバー機能を`pip install pytilpack`だけで利用できる状態を保つため、当該増加を受け入れている。
  新規の依存追加ではこの例外を根拠にせず、最小限方針を適用する
- サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する
- コア依存（`[project.dependencies]`）の版指定には、原則として上限を設けない。
  上限は上流のメジャー更新を利用者が選べなくする一方、現在の運用には上限を引き上げる契機が無く、
  設定した上限が放置されるためである。
  上流のメジャー更新でimportが失敗した場合は、その時点で追随する。
  例外として上限を設けられるのは、依存更新の担当者が対象メジャー版について次のいずれかを確認した場合に限る。
  確認手段は実機実行、公式移行資料、公式セキュリティ情報のいずれかとする
  - import失敗、またはimport失敗に起因する要求機能の不成立
  - 既存APIの非互換変更
  - 未修正のセキュリティ脆弱性など、対象メジャー版の採用を維持できない事由
  上限を設ける場合は、上限を外す条件を版指定のコメントへ併記する。
  条件は移行対応の完了、対象メジャー版でのテスト成功、脆弱性修正版の公開など、実行結果または公式資料で確認できる事実とする
- インポートは原則トップレベルで行う（`pyproject.toml`の`[tool.pylint."messages control"]`で`import-outside-toplevel`は有効）
- ファイル作成時に厳密なパーミッションを固定する必要がある場合（umask非依存）は
  `os.open(..., mode=0o600)`等で作成時点から確定させる。
  `pathlib.Path.open`+`chmod`の二段では作成→`chmod`の隙間で他プロセスがファイルを開ける
  時間窓が生じる（`pytilpack/secrets.py`が該当）
- `pytilpack.sqlalchemy`の`SyncMixin`と`AsyncMixin`は初期化状態をクラス変数で保持し、`init()`の二重呼び出しを拒否する。
  `AsyncMixin.term()`はスレッド単位のengineを`dispose()`し、engineとsessionmakerの参照を`None`へ戻すのみで当該状態を戻さないため、
  `init()`→`term()`→`init()`は成立しない。
  テスト規約（厳守規定）として、同一の`SyncMixin`または`AsyncMixin`サブクラスを複数回のfixture setupで再利用する場合、
  fixtureを`scope="session"`としワーカーごとに1回だけ初期化する必要がある
  （`scope="module"`ではpytest-xdistの分配次第でsetupが繰り返され、同じクラスで2回目の`init()`が失敗する）。
  sessionスコープで共有したengineはテストをまたいで行を残すため、当該fixtureを使うテストモジュールでは次の2点も厳守規定とする
  - 各テストの前に全テーブルの行を削除するfunctionスコープのautouse fixtureを置く
  - 検証対象を当該テストが挿入した行に限定し、他テストが残した行の有無で結果が変わる絶対値アサーションを書かない

### モジュール→extrasキーマッピング（要点）

モジュール名とextrasキー名が異なる主なケース（詳細は`architecture.md`参照）:

- `pytilpack.pycrypto` → `pycryptodome`
- `pytilpack.yaml` → `pyyaml`
- `pytilpack.flask_login` / `pytilpack.quart_auth` / `pytilpack.i18n` → それぞれ`flask`/`quart`/`babel`に含まれる

上記以外は原則としてモジュール名とextrasキー名が一致する。
`.claude/agents/extras-consistency-checker.md`はこのマッピングを参照して判定する。

## 注意点

- モジュール追加時は必ず`/add-module`スキルを使用
