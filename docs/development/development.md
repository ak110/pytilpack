# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. [uvをインストール](https://docs.astral.sh/uv/getting-started/installation/)する
3. セットアップを実行する

    ```bash
    make setup
    ```

## 開発コマンド

| コマンド | 用途 |
| --- | --- |
| `make format` | 整形 + 軽量lint + 自動修正（開発時の手動実行用） |
| `make test` | 全チェック実行（コミット前の最終確認用） |
| `make update` | 依存更新 |
| `make docs` | ドキュメントのローカルプレビュー（`http://127.0.0.1:8000/`） |

## サプライチェーン攻撃対策

ロックファイル尊重・公開待機・ピン留め運用の3点を基本方針とする。

- `uv.lock`をそのまま使うため`UV_FROZEN=1`を常時有効化している
- `pyproject.toml`の`exclude-newer`で公開直後パッケージの即時導入を抑制している
- GitHub Actionsは`pinact`でハッシュピン留めし、定期更新している

依存の追加・更新は`uv add`/`uv remove`/`uv lock --upgrade-package`で行う。

## ドキュメントサイト運用

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

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
