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

## モジュールの構成と依存

pytilpackは主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用する。
利用者は必要なモジュールだけを取り込むことができる。

### コア依存とextras

コア依存（`[project.dependencies]`）は最小限に保つ。
サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する。
`mcp`の推移的依存は、MCPサーバーを`pip install pytilpack`だけで利用できる状態を保つため受け入れている。
新規依存の追加にはこの判断を流用せず、コア依存の最小化を適用する。

コア依存の版指定には原則上限を設けない。上流のメジャー更新を利用者が選べる状態を保ち、上限が放置されることを防ぐ。
上流の更新でimportが失敗した場合は、その時点で追随する。
依存更新の担当者が実機実行・公式移行資料・公式セキュリティ情報で、対象メジャー版に次のいずれかを確認した場合だけ上限を設ける。

- import失敗や、それに起因する要求機能の不成立
- 既存APIの非互換変更
- 未修正の脆弱性など、採用を維持できない事由

上限には移行対応の完了・対象メジャー版でのテスト成功・脆弱性修正版の公開など、実行結果か公式資料で確認できる解除条件をコメントで添える。

### 対応情報の定義元

- コア依存と各extraの直接依存は`pyproject.toml`に定義する
- extraで提供するモジュールは`scripts/check_extras_imports.py`の`EXTRA_MODULES`に定義する
- CLIの名前・実装・必要extraは`pytilpack/cli/main.py`の`_SUBCOMMANDS`に定義する

利用者が読む対応表とモジュール分類は[利用者向けガイド](../guide/index.md)に置く。
分類はモジュールの主な用途で1つに決め、MkDocsのnavとllmstxtにも同じ所属を記載する。
`all`は他の全extraの直接依存の和集合を持ち、`sqlalchemy[asyncio]`のような依存先のextraも保持する。

### 依存の向きとimport

標準ライブラリやコア依存を使う基盤モジュールを、ライブラリ別・フレームワーク別の支援から利用する。
`functools`は`http`、`secrets`は`functools`、`json`は`jsonc`と`io`、`sqlalchemy`は`asyncio`・`paginator`・`python`を利用する。
同じ処理を公開窓口ごとに写さず、共通の内部実装へ委ねる。同期と非同期のセッション実行や初期化状態はそれぞれが保持する。

importは原則トップレベルに置く。ベースのモジュールが任意extraを要する機能を持つ場合は、その関数内で依存を読み込む。
たとえば`asyncio.io_`のYAML操作は、呼び出す場合だけ`pytilpack.yaml`を読み込む。
Unix専用依存については後掲のプラットフォーム依存の規則を適用する。

任意extraを要するモジュールをトップレベルでimportする側は、そのextraの直接依存も自分のextraと`all`へ含める。

### サブパッケージ共通モジュールの依存

`pytilpack/_web_asserts.py`のように複数のフレームワーク向けサブパッケージから共通利用される
私的モジュールがある。
これらが特定のサードパーティに依存する場合、そのパッケージを依存元の各フレームワークextras
（`flask`・`quart`・`fastapi`等）と`all` extrasの双方に含める。

具体例: `pytilpack/_web_asserts.py`の`assert_xml_core`はXML外部実体攻撃を防ぐため
`defusedxml`を使用する。
このため`flask`・`quart`・`fastapi`・`all` extrasに`defusedxml`を含める。

## 公開API設計方針

- 各モジュールは対象ライブラリ（`pytilpack.fastapi`・`pytilpack.flask`等）ごとに独立した名前空間を持つ
- `pytilpack.cli`配下はコマンドラインインターフェースの実装で、パッケージのpublic APIには含めない

同期・非同期を包むデコレーターは、コルーチン関数かどうかを判別して両方に対応する。
デコレーター以外で非同期版を持つ関数は、同じモジュールに`a`接頭辞の名前で置く。
`pytilpack.asyncio`は標準ライブラリと他モジュールのI/Oの非同期版を置く。
既存の`threadinga`は互換のため維持する。
各サブモジュールの`__all__`には意図して公開する関数・クラスを記載し、importした名前や内部処理を漏らさない。

### 非推奨と削除

関数全体の非推奨には`pytilpack.python.deprecated`を使い、警告文に現行の完全修飾名で移行先を示す。
特定の引数だけの非推奨は、その引数を使った場合に警告する。
公開インターフェースの削除は非互換変更としてメジャー版の更新で行う。後方互換用の空extraも同じ扱いとする。

### プラットフォーム依存とファイル権限

`fcntl`などUnix専用モジュールに依存するモジュールは、API文書でUnix専用であることを案内する。
他のモジュールから最上位で読み込まず、その機能を使う関数内でimportする。

umaskによらず厳密な権限が必要なファイルは、`os.open(..., mode=0o600)`などで作成時点から権限を確定する。
`Path.open`の後に`chmod`する方法は権限変更前に他プロセスが開ける時間窓を持つため使わない。
鍵を保存する`pytilpack.secrets`にも適用する。

## テスト規約

- `pytilpack/xxx.py` → `tests/xxx_test.py`
- `pytilpack/xxx/yyy.py` → `tests/xxx/yyy_test.py`
- `xxx`がPythonキーワード等と衝突する場合は`xxx_.py`となる。テストは`xxx_test.py`（末尾アンダースコアは除く）
- 既存モジュールへ公開関数・公開クラスを追加した場合は、対応する`tests/.../xxx_test.py`に単体テストも追加する

リポジトリの設定を検証するテストは、この配置規約の対象外とする。
たとえば`tests/precommit_test.py`は`.pre-commit-config.yaml`の設定を検証する。

### SQLAlchemyのfixture（厳守規定）

`SyncMixin`と`AsyncMixin`は各サブクラスのクラス変数で初期化状態を保持し、二重の`init()`を拒否する。
`AsyncMixin.term()`はスレッド単位のengineを`dispose()`し、engineとsessionmakerの参照を`None`へ戻すが、クラスの初期化状態を戻さない。
このため`init()`→`term()`→`init()`は成立しない。

同じサブクラスを複数回のfixture setupで使う場合は、`scope="session"`でワーカーごとに1回だけ初期化する。
moduleスコープではpytest-xdistの分配によってsetupが繰り返され、2回目の`init()`が失敗する。
共有engineが残す行の影響を除くため、使用する各テストモジュールは次の2点も守る。

- functionスコープのautouse fixtureで各テスト前に全テーブルの行を削除する
- 検証をそのテスト自身が挿入した行へ限定し、他テストの残した行で変わる絶対値アサーションを避ける

### テスト用ローカルポートの割り当て

`tests/`配下でローカルHTTPサーバーを起動するテストは、pytest-xdistの並列実行（`-n 4`）で
ポート衝突によるハング・失敗を避けるため、`port=0`でOSに空きポートを割り当てさせる。
Flask・Quartの`run`が返す実ポートへ接続し、コンテキストを抜けて停止・回収する。起動待ちは間隔と上限を持つ。

## ドキュメント構成と対応情報の確認

サイトの生成・配布とモジュール追加の手順は[開発手順](development.md)の「ドキュメントサイト運用」を参照する。

- `docs/api/<name>.md`、各モジュールのAPI生成設定と必要extra・プラットフォームの注記
- `docs/guide/index.md`、extras一覧と唯一のモジュール分類
- `docs/guide/cli.md`、各CLIの用途・代表例・ヘルプへの案内
- `mkdocs.yml`、navとllmstxt sectionsの同じ分類

`scripts/check_docs_api.py`は公開モジュール一覧、extra・対象モジュール・直接依存、コア依存、
`all`の和集合、APIの必要extra注記、CLI節、8分類の所属が定義元と一致するか確かめる。
pre-commitとCIが同じスクリプトを実行し、不一致では所在を示して非0で終了する。
配布wheelの単独extraでのimportとWebアサーションは`scripts/check_extras_imports.py`が隔離環境で検証する。
