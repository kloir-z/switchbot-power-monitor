# SwitchBot Power Monitor

Raspberry Pi 4用のSwitchBot Plug Miniリアルタイム電力監視システム

## 機能

- **リアルタイム電力監視**: SwitchBot Plug Mini APIから20秒間隔でデータ取得
- **Webダッシュボード**: Chart.jsを使った美しいリアルタイムグラフ表示（データベース専用）
- **データベース保存**: SQLiteでの電力データ履歴保存
- **RESTful API**: FastAPIによるJSON API提供
- **systemdサービス**: 自動起動・再起動対応
- **自動データ収集**: systemdタイマーによる20秒間隔収集
- **データベース管理**: CSV出力、データ削除、統計表示機能

## セットアップ

### 1. SwitchBot APIトークンの取得

1. SwitchBotアプリを開く
2. プロフィール > 設定 > アプリバージョンを10回タップ
3. 開発者オプション > Open Token を生成
4. TokenとSecretをメモ

### 2. 環境設定

```bash
cd /home/user/switchbot-power-monitor
cp .env.example .env
# .envファイルを編集してトークンを設定
```

### 3. プロジェクトのセットアップ

```bash
cd /home/user/switchbot-power-monitor
# 依存関係をインストール
uv sync

# デバイスIDを確認（一時的にテスト用エンドポイントを作成）
# または SwitchBot アプリで Device ID を確認して .env に設定
```

### 4. systemdサービスとして登録（推奨）

```bash
# サービスファイルをコピー
sudo cp switchbot-power-monitor.service /etc/systemd/system/
sudo cp switchbot-data-collector.service switchbot-data-collector.timer /etc/systemd/system/

# サービスを有効化・開始
sudo systemctl daemon-reload
sudo systemctl enable switchbot-power-monitor.service
sudo systemctl enable switchbot-data-collector.timer
sudo systemctl start switchbot-power-monitor.service
sudo systemctl start switchbot-data-collector.timer
```

## 使用方法

### Webダッシュボード（推奨）

ブラウザで `http://localhost:8001/dashboard` にアクセス

**機能:**
- リアルタイム電力・電圧・電流・日次消費量表示
- マルチデバイス対応（複数のPlug Miniデバイス監視）
- 時間範囲選択（1時間・6時間・24時間・1週間）
- 自動更新（現在値10秒・履歴30秒ごと）
- データベース管理（統計表示、CSV出力、データ削除）

### 手動サーバー起動

```bash
cd /home/user/switchbot-power-monitor
uv run main.py
```

### API エンドポイント

**データ取得（データベース専用）:**
- `GET /` - API情報
- `GET /dashboard` - Webダッシュボード
- `GET /power/history/{device_id}?hours=24` - 電力履歴
- `GET /power/latest/{device_id}` - 最新の保存データ
- `GET /power/db/current` - 全デバイスの現在データ（DB専用）
- `GET /health` - ヘルスチェック

**データベース管理:**
- `GET /database/stats` - データベース統計
- `POST /database/export/all?hours=24` - 全デバイスCSV出力
- `POST /database/export/{device_id}?hours=24` - 個別デバイスCSV出力
- `DELETE /database/delete/{device_id}?confirm=true` - デバイスデータ削除
- `DELETE /database/delete/old?minutes=1440&confirm=true` - 古いデータ削除

**システム専用（systemdタイマー使用）:**
- `POST /power/collect/all` - 全デバイスデータ収集（SwitchBot API呼び出し）

### API使用例

```bash
# 過去24時間の履歴を取得  
curl http://localhost:8001/power/history/YOUR_DEVICE_ID?hours=24

# データベースから現在の全デバイス状況を取得
curl http://localhost:8001/power/db/current

# データベース統計を確認
curl http://localhost:8001/database/stats

# CSV出力（過去24時間）
curl -X POST http://localhost:8001/database/export/all?hours=24 -o power_data.csv
```

## データ構造

```json
{
  "device_id": "デバイスID",
  "timestamp": 1693123456,
  "voltage": 100.0,
  "electric_current": 0.5,
  "power": 50.0,
  "electricity_of_day": 1.2,
  "power_on": true
}
```

## 自動データ収集

### systemdタイマー（推奨・設定済み）

20秒間隔の自動データ収集が設定されています（API使用量最適化）：

```bash
# タイマー状態確認
sudo systemctl status switchbot-data-collector.timer

# タイマー停止
sudo systemctl stop switchbot-data-collector.timer

# タイマー開始
sudo systemctl start switchbot-data-collector.timer
```

### 手動cronジョブ（非推奨）

cronは最小1分間隔のため、リアルタイム監視には不適切：

```bash
# 5分ごとにデータ収集（参考）
*/5 * * * * curl -X POST http://localhost:8001/power/collect/YOUR_DEVICE_ID
```

## システム管理

### サービス管理コマンド

```bash
# APIサーバー管理
sudo systemctl status switchbot-power-monitor.service
sudo systemctl stop switchbot-power-monitor.service
sudo systemctl start switchbot-power-monitor.service
sudo systemctl restart switchbot-power-monitor.service

# データ収集タイマー管理
sudo systemctl status switchbot-data-collector.timer
sudo systemctl stop switchbot-data-collector.timer
sudo systemctl start switchbot-data-collector.timer

# ログ確認
sudo journalctl -u switchbot-power-monitor.service -f
sudo journalctl -u switchbot-data-collector.service -f
```

## トラブルシューティング

### よくある問題

1. **APIエラー（401 Unauthorized）**
   - `.env`ファイルのトークンを確認
   - SwitchBotアプリで新しいトークンを生成

2. **ポート競合**
   - デフォルトポート8001が使用中の場合、`main.py`のポート番号を変更

3. **データが収集されない**
   - Hub Mini2がオンラインか確認
   - デバイスIDが正しいか確認

## SwitchBot API使用量について

このシステムは **SwitchBot APIの1日10,000回制限** を考慮して設計されています：

### 現在の使用量
- **データ収集**: 20秒間隔 × 2デバイス = 8,640回/日
- **WebUI**: データベースのみアクセス（APIアクセス0回）
- **合計**: 8,640回/日（制限の86.4%）

### API制限の管理
- WebUIはすべてデータベースから取得（リアルタイム表示維持）
- 不要なAPIエンドポイントを削除してAPI呼び出しを最小化
- systemdタイマー間隔を調整してAPI使用量をコントロール可能