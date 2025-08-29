# SwitchBot Power Monitor

Raspberry Pi 4用のSwitchBot Plug Miniリアルタイム電力監視システム

## 機能

- SwitchBot Plug Miniからリアルタイム電力データを取得
- SQLiteデータベースでの電力データ保存  
- FastAPI を使った簡単なJSON API
- 電力履歴の取得と表示

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

### 3. デバイスIDの確認

```bash
cd /home/user/switchbot-power-monitor
uv run main.py &
# 別ターミナルで
curl http://localhost:8000/devices
# device IDをメモして .env に設定
```

## 使用方法

### サーバー起動

```bash
cd /home/user/switchbot-power-monitor
uv run main.py
```

### API エンドポイント

- `GET /` - API情報
- `GET /devices` - デバイス一覧
- `GET /power/current/{device_id}` - リアルタイム電力データ
- `GET /power/history/{device_id}?hours=24` - 電力履歴
- `POST /power/collect/{device_id}` - 手動データ収集
- `GET /power/latest/{device_id}` - 最新の保存データ
- `GET /health` - ヘルスチェック

### 使用例

```bash
# 現在の電力データを取得
curl http://localhost:8000/power/current/YOUR_DEVICE_ID

# 過去24時間の履歴を取得  
curl http://localhost:8000/power/history/YOUR_DEVICE_ID?hours=24

# データを手動収集・保存
curl -X POST http://localhost:8000/power/collect/YOUR_DEVICE_ID
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

定期的なデータ収集のためにcronジョブを設定できます：

```bash
# 5分ごとにデータ収集
*/5 * * * * curl -X POST http://localhost:8000/power/collect/YOUR_DEVICE_ID
```