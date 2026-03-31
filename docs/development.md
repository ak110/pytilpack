# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする。
2. [uvをインストール](https://docs.astral.sh/uv/getting-started/installation/)する。
3. [pre-commit](https://pre-commit.com/)フックをインストールする。

    ```bash
    uv run pre-commit install
    ```

4. サプライチェーン攻撃対策として、`uvx`/`pnpx`用のグローバル設定をする。

    ```bash
    mkdir -p ~/.config/uv && echo 'exclude-newer = "1 day"' >> ~/.config/uv/uv.toml
    pnpm config set minimum-release-age 1440 --global
    ```

## ドキュメント

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイしている。

### ローカルでの確認

```bash
make docs   # ローカルプレビュー (http://127.0.0.1:8000/)
```

### GitHub Pages の初期設定

masterへのプッシュ時に`.github/workflows/docs.yaml`が自動実行されるが、初回のみGitHub側の設定が必要。

1. リポジトリの Settings > Pages を開く
2. Build and deployment の Source を **GitHub Actions** に変更する

設定後、masterにプッシュすれば <https://ak110.github.io/pytilpack/> に自動デプロイされる。

### モジュール追加時

新しいモジュール `pytilpack/xxx.py` を追加した場合、対応する `docs/api/xxx.md` も作成する必要がある。

```markdown
# pytilpack.xxx

::: pytilpack.xxx
```

サブパッケージの場合:

```markdown
# pytilpack.xxx

::: pytilpack.xxx
    options:
      show_submodules: true
```

作成を忘れた場合はpre-commitおよびCIで検出される。

## リリース手順

事前に`gh`コマンドをインストールして`gh auth login`でログインしておき、以下のコマンドのいずれかを実行。

```bash
gh workflow run release.yaml --field="bump=バグフィックス"
gh workflow run release.yaml --field="bump=マイナーバージョンアップ"
gh workflow run release.yaml --field="bump=メジャーバージョンアップ"
```

<https://github.com/ak110/pytilpack/actions> で状況を確認できる。
