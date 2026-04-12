# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. [uvをインストール](https://docs.astral.sh/uv/getting-started/installation/)する
3. セットアップを実行する

    ```bash
    make setup
    ```

4. サプライチェーン攻撃対策として、`uvx`/`pnpx`用のグローバル設定をする

    ```bash
    mkdir -p ~/.config/uv && echo 'exclude-newer = "1 day"' >> ~/.config/uv/uv.toml
    pnpm config set minimum-release-age 1440 --global
    ```

## UV_FROZENによるlockfile尊重（サプライチェーン攻撃対策）

CI/`make`などの自動実行環境で`uv sync`/`uv run`が依存解決を再実行せず`uv.lock`をそのまま使うよう、環境変数`UV_FROZEN=1`を常時有効化している。
意図しない再resolveでロックファイルが書き換わるリスクを抑え、`pyproject.toml`の`exclude-newer = "1 day"`と組み合わせて二重防御として機能する。

- `make format`/`make test`/`make setup`は`Makefile`の`export UV_FROZEN := 1`で自動適用される
- CIは`.github/workflows/*.yaml`の`env.UV_FROZEN`で自動適用される
- `git commit`経由のpre-commitフックは`.pre-commit-config.yaml`のlocal hookのentryに`--frozen`を明示している

開発者のシェルでは`UV_FROZEN`を設定しない前提なので、依存の追加・更新は通常どおり`uv add`/`uv remove`/`uv lock --upgrade-package`を使えばよい。
`make update`も内部で自動的にUV_FROZENを外すため、そのまま実行してよい。

## READMEとdocsの役割分担

本プロジェクトのドキュメントは以下の構成で配置している。

- README.md: 概要・特徴・インストール手順・extras一覧・ドキュメントへのリンクを網羅する「玄関」。README.mdだけを読めばプロジェクトの目的と使い始めるための入口が把握できる状態を保つ
- docs/guide/: 利用者向けの詳細情報（インストール・extras一覧・モジュール一覧・CLIコマンドなど）
- docs/api/: モジュールごとのAPIリファレンス（mkdocstringsで自動生成）
- docs/development/: 開発者向けの情報（セットアップ・モジュール追加手順・リリース手順など）

README.mdとdocs側で概要・特徴・インストール手順が部分的に重複する場合があるが、README.mdはGitHubトップとして、docs側は公開ドキュメントの入口としてそれぞれ自己完結する必要があるため、この重複は許容する。本プロジェクトの`docs/index.md`はREADMEへの参照のみに留めており、インストール手順の重複は発生させていない。

変更頻度が低いため二重管理のコストより一貫性・可読性のメリットが上回ると判断した。変更時は、docs側で同じ情報を再掲している箇所があれば同じコミット内で合わせて更新する。

## ドキュメント

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイしている。

### ローカルでの確認

```bash
make docs   # ローカルプレビュー (http://127.0.0.1:8000/)
```

### GitHub Pages の初期設定

masterへのプッシュ時に`.github/workflows/docs.yaml`が自動実行されるが、初回のみGitHub側の設定が必要。

1. リポジトリの `Settings` → `Pages` を開く
2. `Build and deployment` の `Source` を `GitHub Actions` に変更する

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

## コミットメッセージ (Conventional Commits)

Conventional Commits形式に従う。ただし記述の方向性があまり変わらないような軽微な修正は`chore`などにしてよい。
