# SwitchBot Power Monitor

Raspberry Pi 4用のSwitchBot Plug Miniリアルタイム電力監視システム

## 機能

- **リアルタイム電力監視**: SwitchBot Plug Mini APIから10秒間隔でデータ取得
- **Webダッシュボード**: Chart.jsを使った美しいリアルタイムグラフ表示
- **データベース保存**: SQLiteでの電力データ履歴保存
- **RESTful API**: FastAPIによるJSON API提供
- **systemdサービス**: 自動起動・再起動対応
- **自動データ収集**: systemdタイマーによる10秒間隔収集

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

# デバイスIDを確認
uv run main.py &
curl http://localhost:8001/devices
# device IDをメモして .env に設定
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
- 時間範囲選択（1時間・6時間・24時間・1週間）
- 自動更新（現在値10秒・履歴30秒ごと）

### 手動サーバー起動

```bash
cd /home/user/switchbot-power-monitor
uv run main.py
```

### API エンドポイント

- `GET /` - API情報
- `GET /dashboard` - Webダッシュボード
- `GET /devices` - デバイス一覧
- `GET /power/current/{device_id}` - リアルタイム電力データ
- `GET /power/history/{device_id}?hours=24` - 電力履歴
- `POST /power/collect/{device_id}` - 手動データ収集
- `GET /power/latest/{device_id}` - 最新の保存データ
- `GET /health` - ヘルスチェック

### API使用例

```bash
# 現在の電力データを取得
curl http://localhost:8001/power/current/YOUR_DEVICE_ID

# 過去24時間の履歴を取得  
curl http://localhost:8001/power/history/YOUR_DEVICE_ID?hours=24

# データを手動収集・保存
curl -X POST http://localhost:8001/power/collect/YOUR_DEVICE_ID
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

10秒間隔の自動データ収集が設定されています：

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