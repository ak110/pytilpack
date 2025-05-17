# プロダクトコンテキスト

## 解決する問題

- ボイラープレートコードの削減
- 一貫性のある操作の提供
- 開発効率の向上

## インストール

```bash
# 最小インストール
pip install pytilpack

# 全機能インストール
pip install pytilpack[all]

# 個別機能インストール
pip install pytilpack[fastapi]
```

## 主要機能グループ

### 標準ライブラリ拡張

- asyncio_: 非同期処理
- pathlib_: ファイル操作
- base64_: エンコード/デコード
- json_/yaml_: データシリアライズ
- csv_: データ処理

### Webフレームワーク

- FastAPI: アサーション、ユーティリティ
- Flask: アサーション、プロキシ対応
- Quart: アサーション、プロキシ対応

### データ処理

- htmlrag: HTML RAG処理
- data_url: データURL操作
- sqlalchemy_: SQLAlchemy拡張
- sse: Server-Sent Events処理

### AI/ML

- openai_: OpenAI API関連
- tiktoken_: トークン処理

## 使用パターン

```python
# ライブラリ固有
import pytilpack.xxx_  # xxxはライブラリ名

# 汎用機能
import pytilpack.xxx   # 共通機能
```

## 共通規約

- 型ヒント必須（Python 3.11+）
- テストコード完備
- 一貫したコードスタイル
- 明確なドキュメント
