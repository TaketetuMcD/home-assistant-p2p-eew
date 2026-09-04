# P2P EEW for Home Assistant

[![Validate HACS](https://github.com/TaketetuMcD/home-assistant-p2p-eew/actions/workflows/validate.yml/badge.svg)](https://github.com/TaketetuMcD/home-assistant-p2p-eew/actions/workflows/validate.yml)
[![Hassfest](https://github.com/TaketetuMcD/home-assistant-p2p-eew/actions/workflows/hassfest.yml/badge.svg)](https://github.com/TaketetuMcD/home-assistant-p2p-eew/actions/workflows/hassfest.yml)
[![GitHub Release](https://img.shields.io/github/v/release/TaketetuMcD/home-assistant-p2p-eew)](https://github.com/TaketetuMcD/home-assistant-p2p-eew/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

P2P地震情報から**気象庁の緊急地震速報（警報）**をリアルタイムに受信し、Home Assistantのスピーカー、照明、通知などを自動化するカスタム統合です。

複数地域、細分区域、最低予測震度を設定できます。初報では対象外でも、続報で条件を満たした瞬間に通知します。

> **重要:** 本統合は補助的な防災オートメーション用です。公式の緊急地震速報を置き換えるものではありません。必ずスマートフォン、テレビ、防災行政無線などの正式な情報源を併用してください。

## できること

- P2P地震情報 WebSocketのEEW（`code: 556`）を常時監視
- 気象庁の府県予報区を**複数選択**（OR条件）
- `神奈川県東部` のような細分区域をカスタム指定
- 通知する最低予測震度を設定（指定なし、4、5弱、5強、6弱、6強、7）
- 初報が対象外・震度未達でも、後続報を継続判定
- 同じ地震の重複通知を抑えつつ、予測最大震度が上がった続報は再通知可能
- 取消報で警報状態を解除し、Blueprintの音声再生を停止可能
- WebSocket再接続時に直近の有効なEEWを履歴APIから補完
- 警報・接続状態のbinary sensorと、動作確認用ボタンを提供
- 音声警報用Automation Blueprintを同梱
- APIキー不要。Home AssistantのUIだけで設定・変更可能

## 必要環境

- Home Assistant `2026.8.0` 以降
- HACS（推奨）または手動インストール
- P2P地震情報のAPIへ接続できるネットワーク

## インストール

### HACS（推奨）

1. HACSを開き、右上メニューから **Custom repositories** を選びます。
2. Repositoryに `https://github.com/TaketetuMcD/home-assistant-p2p-eew` を入力します。
3. Categoryは **Integration** を選び、追加します。
4. `P2P EEW` をダウンロードし、Home Assistantを再起動します。
5. **設定 → デバイスとサービス → 統合を追加 → P2P EEW** を開きます。

### 手動

1. このリポジトリの `custom_components/p2p_eew` を、Home Assistantの `/config/custom_components/p2p_eew` にコピーします。
2. Home Assistantを再起動します。
3. **設定 → デバイスとサービス → 統合を追加 → P2P EEW** から追加します。

## 設定

| 項目 | 内容 | 既定値 |
|---|---|---|
| 監視地域 | 複数選択可。どれか1つに該当すれば通知 | 未選択（全国） |
| 最低予測震度 | 対象地域の `scaleTo`（予測範囲の上限）がこの震度以上なら通知 | 指定なし |
| 震度上昇時の再通知 | 同一地震の続報で予測最大震度が上がった場合に `p2p_eew_update` を発火 | オン |

設定後は、統合の **設定** からいつでも変更できます。保存すると自動的に再読み込みされます。

### 地域名について

選択肢には、気象庁の「緊急地震速報／府県予報区」に対応する地域を表示します。P2P地震情報では、たとえば次のように配信されます。

| 選びたい範囲 | 設定値 | P2Pの例 |
|---|---|---|
| 神奈川県全域 | `神奈川` または `神奈川県` | `areas[].pref: 神奈川` |
| 神奈川県東部だけ | `神奈川県東部` をカスタム入力 | `areas[].name: 神奈川県東部` |
| 東京都 | `東京` または `東京都` | `areas[].pref: 東京` |
| 北海道全域 | `北海道` をカスタム入力 | 道央・道南・道北・道東をまとめて対象 |
| 沖縄県全域 | `沖縄県` をカスタム入力 | 沖縄本島・大東島・宮古島・八重山をまとめて対象 |

細分区域はP2Pの `areas[].name` と一致する名前を指定してください。表記は[P2P地震情報 JSON API v2仕様](https://github.com/p2pquake/epsp-specifications/blob/master/json-api-v2.yaml)と[気象庁防災情報XMLのコード表](https://xml.kishou.go.jp/tec_material.html)で確認できます。

### 震度コード

イベントデータの `max_scale_from` / `max_scale_to` はP2P地震情報の震度コードです。

| コード | 震度 |
|---:|---|
| `10` | 1 |
| `20` | 2 |
| `30` | 3 |
| `40` | 4 |
| `45` | 5弱 |
| `50` | 5強 |
| `55` | 6弱 |
| `60` | 6強 |
| `70` | 7 |

## エンティティ

| エンティティ | 種類 | 用途 |
|---|---|---|
| `EEW警報` | binary sensor | 条件に合う警報を受信するとオン。続報のたびに属性を更新し、通常60秒後に自動解除 |
| `接続` | binary sensor | P2P WebSocketへの接続状態 |
| `EEWテスト` | button | 現在の設定を使ってテスト警報を発生 |

テストはHome Assistant内部でだけ発生し、P2P地震情報へ送信されません。イベントデータの `test` が `true` になるため、実警報と区別できます。

## Automation Blueprint

統合を読み込むと、同梱Blueprintが次の場所へ自動配置されます。

```text
/config/blueprints/automation/p2p_eew/eew_alarm.yaml
```

1. Home Assistantの `/media` フォルダーに `eew_warning.wav` を置きます。
2. **設定 → オートメーションとシーン → Blueprint** を開きます。
3. **緊急地震速報警報（P2P地震情報）** からオートメーションを作成します。
4. スピーカー、音量、音声ファイル、取消時に停止するかを選びます。
5. `EEWテスト` ボタンで動作を確認します。

既定のMedia Source URIは次のとおりです。

```text
media-source://media_source/local/eew_warning.wav
```

警告音ファイル自体は同梱していません。利用環境とスピーカーに適した音源を用意してください。

## イベント

| イベント | 発火タイミング |
|---|---|
| `p2p_eew_warning` | 1つの地震が初めて地域・震度条件を満たしたとき |
| `p2p_eew_update` | 条件を満たした地震の予測最大震度が続報で上がったとき（設定で無効化可） |
| `p2p_eew_cancel` | 通知済みの地震に取消報が届いたとき |

主なイベントデータ:

| キー | 内容 |
|---|---|
| `event_id`, `serial` | 地震イベントID、報番号 |
| `issue_time`, `origin_time` | 発表時刻、地震発生時刻 |
| `hypocenter`, `magnitude`, `depth_km` | 震源名、マグニチュード、深さ |
| `latitude`, `longitude` | 震源座標 |
| `max_scale_from`, `max_scale_to` | 条件に合った地域の予測震度範囲 |
| `matched_area_names`, `areas` | 条件に合った地域名とP2Pの地域データ |
| `arrival_times`, `kind_codes` | 地域別の主要動到達予測時刻と到達状況コード |
| `selected_areas`, `minimum_scale` | 統合で設定した地域と最低震度 |
| `test` | テストボタンなら `true`、実警報なら `false` |
| `recovered_after_reconnect` | 再接続時の履歴補完なら `true` |

`p2p_eew_update` には、直前までの最大値 `previous_max_scale_to` と更新理由 `update_reason` も含まれます。

### 独自Automationの例

震度5弱以上の初回警報をスマートフォンへ通知する例です。最低震度は統合側でも設定できますが、イベントデータを使えばAutomationごとに条件を変えられます。

```yaml
alias: EEWをスマートフォンへ通知
triggers:
  - trigger: event
    event_type: p2p_eew_warning
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.max_scale_to | int(-1) >= 45 }}"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "緊急地震速報"
      message: >-
        {{ trigger.event.data.hypocenter }}で地震。
        対象地域の予測最大震度は{{ trigger.event.data.max_scale_to }}です。
mode: single
```

`notify.mobile_app_your_phone` は、実際の通知先サービス名に置き換えてください。

## 続報・重複・再接続の動作

同一 `eventId` の各報を、通知済みになるまで地域と震度の両方で判定します。

1. 第1報: 選択地域なし → 通知しない
2. 第2報: 選択地域が追加されたが最低震度未満 → 通知しない
3. 第3報: 選択地域が最低震度以上 → `p2p_eew_warning`
4. 第4報: 条件は同じ → センサー属性だけ更新
5. 第5報: 予測最大震度が上昇 → `p2p_eew_update`
6. 取消報 → `p2p_eew_cancel`、警報センサーを解除

同一メッセージIDの重複配送は無視します。WebSocketが切断された場合は最大30秒まで間隔を延ばしながら再接続し、接続後に直近5分の履歴から有効な最新報を補完します。

## トラブルシューティング

### `接続` センサーがオフのまま

- Home Assistantホストから `wss://api.p2pquake.net/v2/ws` へ接続できるか確認してください。
- DNS、ファイアウォール、プロキシ、時刻設定を確認してください。
- 一時的な切断なら自動的に再接続します。

### 警報が鳴らない

- まず `EEWテスト` ボタンでHome Assistant内のAutomation経路を確認してください。
- 選択した地域名と最低予測震度を確認してください。
- 細分区域は `areas[].name` と完全一致する必要があります。
- スピーカーが対応する音声形式、Media Source URI、音量を確認してください。

### 更新後に設定を変えたい

**設定 → デバイスとサービス → P2P EEW → 設定** を開いてください。v0.4以前の単一地域設定は、v0.5への更新時に自動移行します。

## 通信・プライバシー

この統合にログイン情報やAPIキーは不要です。Home AssistantからP2P地震情報のWebSocketと履歴APIへ接続し、受信した情報をローカルのエンティティとイベントへ反映します。本統合から利用者固有の設定やデータをP2P地震情報へ送信する処理はありません。

## 制限と免責

- P2P地震情報は、情報の内容・配信速度・可用性を保証していません。
- ネットワーク、Home Assistant本体、スピーカーなどの状態により、通知が遅延または失敗する可能性があります。
- 震度や到達時刻は予測であり、続報で変わることがあります。
- 生命・身体・財産の安全を本統合だけに依存しないでください。

データ提供元については[P2P地震情報](https://www.p2pquake.net/)を、配信形式については[P2P地震情報 EPSP specifications](https://github.com/p2pquake/epsp-specifications)を参照してください。

## 開発・フィードバック

不具合報告や機能提案は[GitHub Issues](https://github.com/TaketetuMcD/home-assistant-p2p-eew/issues)へお願いします。報告時は、Home Assistantのバージョン、統合のバージョン、再現手順、個人情報を除いたログがあると調査しやすくなります。

地域判定の単体テストはHome Assistant本体をインストールせず実行できます。

```bash
python3 -m unittest discover -s tests -v
```

## License

[MIT License](LICENSE)
