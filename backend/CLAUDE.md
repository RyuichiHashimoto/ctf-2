# バックエンド開発ガイド

このファイルは `backend/` 配下で作業するときの追加ルールです。リポジトリ全体の方針は `../CLAUDE.md` を参照してください。

## 役割

バックエンドは Attack Path Visualizer の API サーバーです。ネットワーク構成 JSON のアップロード、グラフ正規化、攻撃経路予測、パイプライン実行、MITRE ATT&CK 参照、攻撃シナリオ参照、検知イベント受信を担当します。

## 技術スタック

- Python: 3.x 系
- API: FastAPI
- ASGI server: Uvicorn
- DB access: Peewee
- Database: SQLite
- Graph processing: NetworkX
- Upload handling: python-multipart
- Dependency file: `requirements.txt`
- Runtime path: Docker では `/app`、アプリコードは `/app/src`

## 主要ファイル

```text
backend/
├── Dockerfile
├── requirements.txt
└── src/
    ├── app.py
    ├── routes/
    │   ├── attack_graph.py
    │   └── attack_pipeline.py
    ├── libs/
    │   ├── attack_graph_lib/
    │   │   ├── api.py
    │   │   ├── filter.py
    │   │   ├── node.py
    │   │   ├── postprocessing.py
    │   │   ├── prediction.py
    │   │   ├── preprocessing.py
    │   │   ├── schema.py
    │   │   └── storage.py
    │   ├── attack_pipeline_lib/
    │   │   ├── augmentation.py
    │   │   ├── config.py
    │   │   ├── metrics.py
    │   │   ├── pipeline.py
    │   │   ├── preprocessing.py
    │   │   ├── schema.py
    │   │   └── storage.py
    │   ├── attack_scenario.py
    │   ├── mitre.py
    │   └── recieve_detection.py
    ├── experiments/
    └── network-sample-small.json
```

## アプリ構成

`src/app.py` が FastAPI アプリの入口です。

- アプリ名: `Attack Path Visualizer API`
- 起動時に `libs.attack_graph_lib.init_db()` を実行
- CORS は `FRONTEND_ORIGIN` 環境変数で制御
- 登録ルーター:
  - `routes.attack_graph.router`
  - `routes.attack_pipeline.router`
  - `libs.attack_scenario.router`
  - `libs.mitre.router`
  - `libs.recieve_detection.router`

## 主な API

- `POST /graph/upload`
  - JSON ファイルを受け取り、検証後に `/app/data/uploads/{file_id}/` へ保存する
  - `network_content.json` と `network_content.db` を生成する
- `GET /graph/upload/{file_id}`
  - 保存済み JSON を読み込み、正規化済みグラフを返す
- `GET /graph/uploads`
  - アップロード済みファイル一覧を返す
- `DELETE /graph/uploads/clear`
  - アップロード済みファイルを削除する
- `POST /predict/paths`
  - 指定されたアップロード済みグラフと開始ノードから攻撃経路を予測する
- `POST /pipeline/predict`
  - グラフ補完、脆弱性・脅威情報統合、経路探索、後処理、メトリクス収集をまとめて実行する
- `GET /mitre/tactics`
  - MITRE ATT&CK タクティク一覧を返す
- `GET /mitre/techniques`
  - MITRE ATT&CK テクニック一覧を返す。`tactic` クエリで絞り込み可能
- `GET /scenarios`
  - 攻撃シナリオ一覧を返す
- `GET /scenario`
  - 指定シナリオのステップを返す

検知イベント API は `libs/recieve_detection.py` の既存実装に合わせて扱います。

## レイヤーごとの責務

- `app.py`
  - アプリ生成、CORS、ログ整形、起動時初期化、ルーター登録だけを担当する
- `routes/`
  - HTTP リクエスト/レスポンス、入力の取り出し、`HTTPException` への変換を担当する
- `libs/attack_graph_lib/schema.py`
  - JSON から `GraphData` への変換、グラフ構造の検証を担当する
- `libs/attack_graph_lib/storage.py`
  - Peewee モデル、SQLite 接続、アップロードファイル管理、グラフ保存/読み込みを担当する
- `libs/attack_graph_lib/prediction.py` と `api.py`
  - 経路探索とリスク付き予測を担当する
- `libs/attack_graph_lib/filter.py`
  - 攻撃者が得た情報から next/via/target 条件を導出する
- `libs/attack_pipeline_lib/`
  - パイプライン入力、補完、前処理、探索、後処理、メトリクス、保存を担当する
- `libs/mitre.py`
  - MITRE ATT&CK SQLite DB の読み取りを担当する
- `libs/attack_scenario.py`
  - 攻撃シナリオ SQLite DB の読み取りを担当する

API 層に DB モデルや探索アルゴリズムを直接増やさず、既存ライブラリ層へ寄せてください。

## グラフデータの扱い

内部表現は `GraphData` を基本にします。

- `GraphNode`
  - `id`, `label`, `type`, `techniques`, `features`
- `GraphEdge`
  - `id`, `source`, `target`, `risk`
- `GraphContain`
  - `id`, `parent`, `child`, `label`
- `NodeType`
  - `entry`, `pivot`, `asset`, `unknown`

入力 JSON は `nodes/edges` 形式と `graph.node/graph.edge/graph.contains` 形式の両方を扱います。新しい処理を追加するときは、文字列辞書を各所で直接触るよりも、まず `GraphData` に正規化してから処理します。

## 攻撃経路予測の注意

- `predict_paths_with_risk()` はグラフ、開始ノード、シナリオ、最大ノード数、経由/到達条件を受け取る
- `/predict/paths` は `network_configuration_file_id` と互換用の `netowork_configuration_file_id` の両方を受け付けている
- `attacker_obtained_data` と `attack_data` は既存互換のため両方を考慮する
- パイプラインでは `prediction_method` に `exhaustive_specified` / `exhaustive_unspecified` を使う
- `specified`, `start_end`, `unspecified`, `all` は既存 alias として扱われる
- `exhaustive_specified` では `start_node` と `end_node` / `end_nodes` / `target_node` / `target_nodes` が必要

既存フロントエンドが依存しているキー名やレスポンス形式は、理由なく変更しないでください。

## データベースとファイル

Docker 実行時の主なパス:

- `/app/data/attack_graph.db`
- `/app/data/uploads/uploads.db`
- `/app/data/uploads/{file_id}/network_content.json`
- `/app/data/uploads/{file_id}/network_content.db`
- `/app/data/mitre_attack.db`
- `/app/data/attack_scenario.db`

ルール:

- Peewee の既存モデルと `sqlite_db_connection()` を使う
- DB 接続は `connect(reuse_if_open=True)` と確実な `close()` の流れを守る
- `with db.atomic():` を使える保存処理ではトランザクションを使う
- アップロード保存先や DB パスを変更するときは Docker volume と `docker-compose.yml` への影響を確認する
- MITRE DB と攻撃シナリオ DB は読み取り前提で扱う
- `data/uploads/` の削除や `uploads.db` の再作成は明示指示なしに行わない

## エラー処理

- API 境界では `HTTPException` を使う
- 入力不足・形式不正は基本的に `400`
- 保存済みファイルが見つからない場合は `404`
- サーバー側の予期しない失敗はログに詳細を残し、レスポンスは必要以上に内部情報を出さない
- 既に `HTTPException` が投げられている場合は握りつぶさず再送出する

例:

```python
try:
    graph = load_uploaded_graph_payload(file_id)
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="File not found")
except Exception:
    logger.exception("failed to load uploaded graph")
    raise HTTPException(status_code=400, detail="Invalid stored JSON")
```

## ログ

- ロガーは `logging.getLogger("uvicorn.error")` の既存方針に合わせる
- 失敗時は `logger.exception()` を優先し、スタックトレースを残す
- 大きなグラフ全体や秘密情報をログに出さない
- 正常系ログでは件数、ID、ステータスなど追跡に必要な最小情報にする

## 依存関係

依存関係は `backend/requirements.txt` に固定されています。追加する場合は、本当にバックエンドで必要かを確認し、Docker build への影響も考えます。

現在の主要依存:

- `fastapi`
- `uvicorn`
- `websockets`
- `networkx`
- `python-multipart`
- `peewee`

## ローカル実行

```bash
cd backend
PYTHONPATH=src uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

Docker Compose ではリポジトリルートから起動します。

```bash
docker compose up --build backend
```

## 検証

最低限の構文確認:

```bash
python3 -m compileall backend/src
```

API を手動確認する場合の例:

```bash
curl -sS http://localhost:8000/graph/uploads
curl -sS http://localhost:8000/mitre/tactics
curl -sS http://localhost:8000/scenarios
```

実行環境に DB やアップロードデータがない場合、空配列や `404` が正常なケースもあります。検証結果は、成功/失敗だけでなく前提も添えて報告します。

## 禁止事項

- SQL/DB ファイルを手動で破壊的に変更しない
- 指示なしに `data/uploads/`、`mitre_attack.db`、`attack_scenario.db` を削除・再生成しない
- API 互換性に関わる typo を安易に改名しない
- フロントエンドが使っているレスポンスキーを理由なく変えない
- `app.py` にルート固有のビジネスロジックを増やさない
- 大きな JSON や DB 内容をログや回答へ丸ごと貼らない
