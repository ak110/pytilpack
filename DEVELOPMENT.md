# 開発手順

## 開発環境構築手順

1. 本リポジトリをcloneする。
2. [uvをインストール](https://docs.astral.sh/uv/getting-started/installation/)する。
3. [pre-commit](https://pre-commit.com/)フックをインストールする。

    ```bash
    uv run pre-commit install
    ```

## リリース手順

事前に`gh`コマンドをインストールし、`gh auth login`でログインしておく。

1. 変更がコミット・プッシュ済みでアクションが成功していることを確認:
   `git status ; gh run list --commit=$(git rev-parse HEAD)`
    - 未完了の場合は `gh run watch run_id` で完了を待機する
2. 現在のバージョンの確認:
  `git fetch --tags && git tag --sort=version:refname | tail -n1`
3. GitHubでリリースを作成:
  `gh release create --target=master --generate-notes v1.x.x`
4. リリースアクションの確認:
  `gh run list --commit=$(git rev-parse HEAD)`
