# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. セットアップを実行する

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

依存パッケージの脆弱性検知の仕組み（Dependabot alerts・定期監査ワークフロー）は設けない。
本リポジトリはライブラリであり`uv.lock`は開発専用のため、利用者の実行環境への脆弱性の影響は限定的である。

## ドキュメントサイト運用

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

### モジュール追加時

新しいモジュールを追加した場合は`/add-module`スキルの手順に従う。
`docs/api/<name>.md`の作成を忘れた場合はコミット時のフックおよびCIで検出される。

## リリース手順

事前に`gh`コマンドをインストールして`gh auth login`でログインし、以下のコマンドのいずれかを実行。

```bash
gh workflow run release.yaml --field="bump=PATCH"
gh workflow run release.yaml --field="bump=MINOR"
gh workflow run release.yaml --field="bump=MAJOR"
```

<https://github.com/ak110/pytilpack/actions>で状況を確認できる。
