# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. [uvをインストール](https://docs.astral.sh/uv/getting-started/installation/)する
3. セットアップを実行する

    ```bash
    make setup
    ```

## 開発コマンド

- `make update`: 依存更新 + pre-commit autoupdate + pinactアクション更新 + 全テスト実行
    - `make update-actions`: GitHub Actionsのハッシュピン更新のみ（mise経由でpinact実行）
- コミット前の検証: `uvx pyfltr run-for-agent`
    - ドキュメントのみの変更は省略可（pre-commitで実行されるため）
    - テストコードの単体実行も極力`uvx pyfltr run-for-agent <path>`を使う（pytestを直接呼び出さない）
    - 対象ファイルや対象ツールを限定して実行できる（最終検証はCIに委ねる前提）

```bash
uvx pyfltr run-for-agent --commands=mypy,ruff-check path/to/file
```

## サプライチェーン攻撃対策

`uvx`/`pnpx`用のグローバル設定:

```bash
mkdir -p ~/.config/uv && echo 'exclude-newer = "1 day"' >> ~/.config/uv/uv.toml
```

CI/`make`などの自動実行環境で`uv sync`/`uv run`が依存解決を再実行せず`uv.lock`をそのまま使うよう、
環境変数`UV_FROZEN=1`を常時有効化している。
意図しない再resolveでロックファイルが書き換わるリスクを抑え、
`pyproject.toml`の`exclude-newer = "1 day"`と組み合わせて二重防御として機能する。

- `make format`/`make test`/`make setup`は`Makefile`の`export UV_FROZEN := 1`で自動適用される
- CIは`.github/workflows/*.yaml`の`env.UV_FROZEN`で自動適用される
- `git commit`経由のpre-commitフックは`.pre-commit-config.yaml`のlocal hookのentryに`--frozen`を明示している

開発者のシェルでは`UV_FROZEN`を設定しない前提のため、依存の追加・更新は通常どおり
`uv add`/`uv remove`/`uv lock --upgrade-package`で行う。
`make update`は内部でUV_FROZENを解除して実行する。

## ドキュメントサイト運用

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

### ローカルでの確認

```bash
make docs   # ローカルプレビュー (http://127.0.0.1:8000/)
```

### GitHub Pagesの初期設定

masterへのプッシュ時に`.github/workflows/docs.yaml`が自動実行されるが、初回のみGitHub側の設定が必要。

1. リポジトリの`Settings` → `Pages`を開く
2. `Build and deployment`の`Source`を`GitHub Actions`に変更する

設定後、masterにプッシュすれば<https://ak110.github.io/pytilpack/>に自動デプロイされる。

### モジュール追加時

新しいモジュールを追加した場合は`/add-module`スキルの手順に従う。
`docs/api/<name>.md`の作成を忘れた場合はpre-commitおよびCIで検出される。

## リリース手順

事前に`gh`コマンドをインストールして`gh auth login`でログインし、以下のコマンドのいずれかを実行。

```bash
gh workflow run release.yaml --field="bump=PATCH"
gh workflow run release.yaml --field="bump=MINOR"
gh workflow run release.yaml --field="bump=MAJOR"
```

<https://github.com/ak110/pytilpack/actions>で状況を確認できる。
