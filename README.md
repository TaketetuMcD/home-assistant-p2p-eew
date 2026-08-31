# P2P EEW for Home Assistant

Home Assistantで、P2P地震情報のWebSocketから**気象庁 緊急地震速報（警報）**を受信するカスタム統合です。

## 主な機能

- P2P地震情報 WebSocket (`code: 556`) を常時監視
- 都道府県 / 細分区域で監視地域を指定
- 第1報で対象外でも、**後続報で対象地域になった瞬間に発火**
- 同一地震の続報による警報アクションの多重発火を抑止
- WebSocket再接続時、直近EEWをJSON APIで補完
- `EEW警報` binary sensor
- `接続` binary sensor
- `EEWテスト` button
- `p2p_eew_warning` イベント
- 警告音とAutomation Blueprintを統合に同梱し、再起動時に自動配置

## HACSからインストール

このリポジトリをHACSの **Custom repositories** に追加してください。

- Repository: `https://github.com/TaketetuMcD/home-assistant-p2p-eew`
- Category: `Integration`

その後 `P2P EEW` をダウンロードしてHome Assistantを再起動し、

**設定 → デバイスとサービス → 統合を追加 → P2P EEW**

から設定します。

監視地域の例:

- `神奈川県`
- `神奈川県東部`
- `東京都`
- 空欄: 全国

## Automation

統合はEEWが初めて監視地域を対象にした時点で、

`p2p_eew_warning`

イベントを発火します。

同梱BlueprintはHome Assistant再起動時に次へ配置されます。

`/config/blueprints/automation/p2p_eew/eew_alarm.yaml`

警告音は次へ配置されます。

`/media/eew_warning.wav`

Media Source:

`media-source://media_source/local/eew_warning.wav`

### テスト

統合が作成する `EEWテスト` ボタンを押すと、実EEWと同じ
`p2p_eew_warning` イベント経路をテストできます。

イベントデータの `test` は:

- 実警報: `false`
- EEWテスト: `true`

です。

## EEWの続報

同じ `eventId` の情報でも、監視地域が対象になるまでは各続報を判定します。

例:

1. 第1報: 神奈川県対象外 → 発火しない
2. 第2報: 神奈川県対象外 → 発火しない
3. 第3報: 神奈川県が対象に追加 → **ここで発火**
4. 第4報以降: 情報更新のみ、警報イベントは再発火しない

## 注意

P2P地震情報は、緊急地震速報（警報）の内容・配信品質を保証しておらず、
公式にも警報用途としての利用は非推奨とされています。

この統合は補助的な防災Automation用途として利用し、
スマートフォン、テレビ、防災行政等の正式な緊急地震速報を併用してください。

## License

MIT
