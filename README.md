# pytilpack

[![CI][ci-badge]][ci-url]

[ci-badge]: https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg
[ci-url]: https://github.com/ak110/pytilpack/actions/workflows/ci.yaml
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

## 特徴

- モジュール単位の個別import: 必要なモジュールだけ取り込む
- extrasによる依存の最小化: 対象ライブラリごとに追加インストール
- CLI同梱: `pytilpack`コマンドで各種サブコマンドを提供
- 主要Pythonライブラリ向けユーティリティ（FastAPI / Flask / Quart / SQLAlchemy / Pydanticなど）

## インストール

```bash
pip install pytilpack
```

extras一覧と各モジュールが必要とする依存は[ドキュメント](https://ak110.github.io/pytilpack/guide/)を参照。
extras付きインストール例（`pip install pytilpack[fastapi]`等）もドキュメントに記載している。

## 主な使い方

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

`xxx` には対象ライブラリ名（`httpx` や `pathlib` など）が入る。

モジュール一覧は[ドキュメント](https://ak110.github.io/pytilpack/)を参照し、APIの詳細はソースコードを読む。
一部はCLIもある。詳細は[CLIコマンド](https://ak110.github.io/pytilpack/guide/cli/)を参照。

## ドキュメント

- [アクセシビリティ](ACCESSIBILITY.md)
- [利用者向けガイド](https://ak110.github.io/pytilpack/guide/)、インストール・extras一覧・モジュール一覧・CLI
- [開発者向け情報](https://github.com/ak110/pytilpack/blob/master/docs/development/development.md)、セットアップ・モジュール追加・リリース手順
- [貢献ガイド](https://github.com/ak110/.github/blob/master/CONTRIBUTING.md)
- [セキュリティポリシー](https://github.com/ak110/.github/blob/master/SECURITY.md)
