# アーキテクチャ

## リポジトリ構成

```text
pytilpack/          # メインパッケージ
  cli/              # CLIサブコマンド群
tests/              # テストコード
docs/               # ドキュメント
  api/              # APIリファレンス（モジュールごとの.md）
  guide/            # 利用者向けガイド
  development/      # 開発者向けドキュメント
scripts/            # 開発用スクリプト
```

## モジュール構成方針

pytilpackは主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用する。
利用者は必要なモジュールだけを取り込むことができる。

### コア依存とextras

コア依存（`[project.dependencies]`）は最小限に保つ（現在: `beautifulsoup4`/`httpx`/`mcp`/`werkzeug`）。
サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する。
インポートは原則トップレベルで行う（`.pylintrc`で`import-outside-toplevel`は有効）。

### モジュール→extrasキーマッピング

モジュール名とextrasキー名が異なるケースを以下に示す。

| モジュール名 | extrasキー | 主な依存パッケージ |
| --- | --- | --- |
| `pytilpack.pycrypto` | `pycryptodome` | pycryptodome |
| `pytilpack.yaml` | `pyyaml` | pyyaml |
| `pytilpack.flask_login` | `flask` | flask, flask-login（`flask`extrasに含まれる） |
| `pytilpack.quart_auth` | `quart` | quart-auth（`quart`extrasに含まれる） |
| `pytilpack.i18n` | `babel` | babel（`babel`extrasに含まれる） |

上記以外は原則としてモジュール名とextrasキー名が一致する。
`.claude/agents/extras-consistency-checker.md`はこのマッピングを参照して判定する。

### サブパッケージ共通モジュールの依存

`pytilpack/_web_asserts.py`のように複数のフレームワーク向けサブパッケージから共通利用される
私的モジュールがある。
これらが特定のサードパーティに依存する場合、当該パッケージは依存元の各フレームワークextras
（`flask`・`quart`・`fastapi`等）と`all` extrasの双方に含める。

具体例: `pytilpack/_web_asserts.py`の`assert_xml_core`はXML外部実体攻撃を防ぐため
`defusedxml`を使用する。
このため`flask`・`quart`・`fastapi`・`all` extrasに`defusedxml`を含める。

## 公開API設計方針

- 各モジュールは対象ライブラリ（`pytilpack.fastapi`・`pytilpack.flask`等）ごとに独立した名前空間を持つ
- モジュール間の横断依存は原則持たない（各モジュールを単独で利用可能とするため）
- `pytilpack.cli`配下はコマンドラインインターフェースの実装で、パッケージのpublic APIには含めない

## テスト配置規約

- `pytilpack/xxx.py` → `tests/xxx_test.py`
- `pytilpack/xxx/yyy.py` → `tests/xxx/yyy_test.py`
- `xxx`がPythonキーワード等と衝突する場合は`xxx_.py`となる。テストは`xxx_test.py`（末尾アンダースコアは除く）
- 既存モジュールへ公開関数・公開クラスを追加した場合は、対応する`tests/.../xxx_test.py`に単体テストも追加する

### テスト用ローカルポートの割り当て

`tests/`配下でローカルHTTPサーバーを起動するテストは、pytest-xdistの並列実行（`-n 4`）で
ポート衝突によるハング・失敗を避けるため、テストファイル単位で固定のポート番号を割り当てる。

| テストファイル | ポート |
| --- | --- |
| `tests/flask/misc_test.py::test_run` | 5000 |
| `tests/httpx_test.py` | 5001, 5002 |
| `tests/http_test.py` | 5003 |
| `tests/quart/misc_test.py::test_run` | 5004 |

新規にローカルサーバーを起動するテストを追加する場合は、本表を参照して未使用のポートを割り当てる。

## ドキュメント構成

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

- `docs/api/<name>.md` — 各モジュールのAPIリファレンス（mkdocstringsによる自動生成の設定ファイル）
- `docs/guide/index.md` — extras一覧・モジュール一覧（APIリファレンスへのリンク集）
- `mkdocs.yml` — nav・llmstxt sectionsで全モジュールを列挙

`docs/api/<name>.md`・`docs/guide/index.md`・`mkdocs.yml`の3箇所はモジュール一覧を同期して保つ必要があり、
`scripts/check_docs_api.py`でCI時に整合性を検証する。
