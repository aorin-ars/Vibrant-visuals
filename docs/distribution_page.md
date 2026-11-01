# VYSE-Vibrant Visuals v{version}

統合版の公式グラフィック「Vibrant Visuals」を、影MOD（シェーダー）のような映画風の映像に仕上げるリソースパックです。
光・空・空気・水・色合いを一から調整し、すべてのバイオームで同じ雰囲気になるようにしています。

## 主な特徴

- **映画のような画づくり**: ACES トーンマップで暗いところは引き締まり、明るい空や夕日はなめらかに白へ抜けます。
- **強い日差しと青い日陰**: 正午は澄んだ白い光です。日陰は黒く潰れず、青みがかったグレーになります。
- **オレンジの夕焼け**: 夕方は空も地面も道もオレンジに染まり、太陽のまわりが大きく輝きます。朝は藍色の空に赤橙の帯が出ます。
- **深い青空**: 真上の濃い青から地平線の淡い色へ、自然なグラデーションになります。
- **ふわふわの雲**: 空一面に晴れの日の雲を描いています。夕方はオレンジ、夜は暗く、雨の日は灰色の曇り空になります。
- **小さく丸い太陽と月**: 月はクレーター付きで、満ち欠けもします。
- **澄んだ空気と光の筋**: 遠くの景色は青くかすみ、谷や洞窟に霞がたまります。木漏れ日や洞窟の入口から光の筋が差し込みます。
- **しっとりした雨の日**: 青みがかった灰色のもやが景色をやわらげます。
- **透き通った水**: 底や水草が透けて見え、穏やかなさざ波に空や岸が映ります。
- **色付きのブロックの光（122種類）**: 松明は橙、魂の炎は水色、レッドストーンは赤、エンドロッドは青白です。光ブロックは蛍光灯のような白です。
- **本物のような夜**: 宵のうちは青い月明かり、深夜は現実の夜のように暗くなります。松明の光は弱めないので、闇の中でくっきり灯ります。
- **すべてのバイオームに対応**: 砂漠は少し暖かく、雪原は白く、沼は霧っぽくなります。

## 空の種類・軽量化モード

リソースパックの一覧で VYSE-Vibrant Visuals をタップし、歯車（⚙）から選べます。

| 設定 | 内容 |
|---|---|
| Sky: soft clouds（初期設定） | 空一面のふわふわの雲。ゲームの四角い雲は自動で消えます |
| Sky: soft clouds, fewer | 雲が少なめ（青空が多い） |
| Sky: soft clouds, more | 雲が多め |
| Sky: soft clouds + the game's clouds | 描いた雲とゲームの雲の両方 |
| Sky: no clouds | 描いた雲なし |
| Lite: the game's clouds, faster | 軽量化モード。描いた雲を使わず、水面の波を軽くします |

重いと感じたときは、軽量化モードに加えてビデオ設定の「アップスケーリングをオン」「点光源の影をオフ」「ボリュメトリックフォグを低〜中」がおすすめです。

## ダウンロード

| ファイル | 内容 |
|---|---|
| **VYSE-Vibrant-Visuals-v{version}.mcpack** | **本体**。これだけで使えます。リソースパックなので**実績もそのまま解除できます** |
| VYSE-Weather-Sync-v{bp_version}.mcpack | **任意**の追加ビヘイビアーパック（下を参照）。入れたワールドは実績が解除されなくなります |

## VYSE Weather Sync（任意）

雨のままワールドを開き直すと、天気が次に変わるまで空が晴れたまま雨が降る、という**ゲーム側の不具合**があります（VYSE が原因ではなく、待っていれば天気が変わったときに直ります）。
リソースパックは天気に触れられないため、これを直したい人向けに別のビヘイビアーパックを用意しています。ワールドに入って 3 秒後、雨なら一瞬だけ雨を止めて降らせ直し、空を雨の空に戻します。

Minecraft の仕様で、**自分で読み込んだビヘイビアーパックを入れたワールドは、中身に関係なく実績が解除されなくなります**。実績が必要なワールドには入れず、本体だけで使ってください。

## 動作環境

- Minecraft 統合版 1.26.0 以降
- Vibrant Visuals に対応した端末（設定 → ビデオで Vibrant Visuals を選べること）

## 導入方法

1. 本体の `.mcpack` を開きます（自動で読み込まれます）。
2. 設定 → ビデオで、Vibrant Visuals をオンにします。
3. ワールドの設定 → リソースパックで「VYSE-Vibrant Visuals」を有効にします。
4. （任意）Weather Sync の `.mcpack` も開き、ワールドの設定 → ビヘイビアーパックで「VYSE Weather Sync」を有効にします（そのワールドは実績が解除されなくなります）。

## 注意

- Vibrant Visuals がオフのときは何も変わりません。
- 描いた雲は空に固定された画像なので、動きません。
- 草の揺れ・動く雲・被写界深度など、シェーダーそのものを書き換える必要がある効果は、リソースパックではできません。
- 見た目は端末やゲームのバージョンによって少し変わることがあります。

## PBR 追加パックについて

ブロックに凹凸・つや・発光を付け、雨でエンティティを濡らす「VYSE-Vibrant Visuals PBR」もあります。Mojang のテクスチャを含むためファイルとしては配布せず、専用ページで**自分の端末の中で作る**形にしています（画像は端末が Mojang 公式の bedrock-samples から直接読み込みます）。できたパックは自分用で、再配布はできません。

## 利用規約・クレジット

- 制作: aorin-ars
- 自分の Minecraft で使うこと、スクリーンショットや動画を公開することはできます。
- **改変・再配布（転載）・販売は禁止**です。紹介するときは、このページへのリンクを載せてください。
- Java版の影MOD（Complementary Shaders など）の雰囲気を参考にしていますが、各作者とは無関係の非公式パックです。コードや素材は流用していません。
- Minecraft 公式の製品ではありません。Mojang / Microsoft の承認を受けたものではなく、関係もありません。

---

# VYSE-Vibrant Visuals v{version} (English)

A resource pack that turns Minecraft Bedrock's official Vibrant Visuals into a filmic, shader-like look. Light, sky, air, water and colour are retuned from scratch and applied to every biome.

## Features

- **Filmic picture**: ACES tone mapping with firm shadows and skies and sunsets that roll smoothly into white.
- **Strong sunlight, blue shade**: clear white light at noon; shade stays blue-grey instead of black.
- **Orange sunsets**: in the evening the sky, ground and roads glow orange, with a big glow around the sun. Sunrise brings a red-orange band under an indigo sky.
- **Deep sky**: a natural gradient from a deep blue overhead to a pale horizon.
- **Soft clouds**: fair-weather clouds painted across the whole sky; orange at sunset, dim at night, grey and overcast in rain.
- **Small round sun and moon**: the moon has craters and phases.
- **Clear air and light shafts**: distant land fades to blue, haze settles in valleys and caves, and light shafts fall through leaves and cave openings.
- **Misty rain**: a soft blue-grey haze over the landscape.
- **Clear water**: see the bottom and plants through it; gentle ripples reflect the sky and shore.
- **Coloured block light (122 kinds)**: orange torches, cyan soul fire, red redstone, blue-white end rods. Light blocks give a fluorescent white.
- **Real nights**: blue moonlight in the evening, truly dark at midnight. Torch light is not dimmed, so it stands out in the dark.
- **Every biome**: warmer deserts, whiter snowfields, mistier swamps.

## Sky options and lite mode

Tap VYSE-Vibrant Visuals in the resource pack list, then the gear (⚙).

| Option | What it does |
|---|---|
| Sky: soft clouds (default) | Soft clouds across the sky; the game's blocky clouds are hidden |
| Sky: soft clouds, fewer | Fewer clouds, more blue sky |
| Sky: soft clouds, more | More clouds |
| Sky: soft clouds + the game's clouds | Both |
| Sky: no clouds | No painted clouds |
| Lite: the game's clouds, faster | Lite mode: no sky images, lighter water waves |

If it runs slowly, use lite mode and, in Video Settings, turn upscaling on, turn point light shadows off and set volumetric fog to low or medium.

## Downloads

| File | What it is |
|---|---|
| **VYSE-Vibrant-Visuals-v{version}.mcpack** | **The pack.** All you need; as a resource pack it **keeps achievements working** |
| VYSE-Weather-Sync-v{bp_version}.mcpack | **Optional** behavior pack (see below). A world with it cannot earn achievements |

## VYSE Weather Sync (optional)

The game has a bug of its own: reopen a world while it rains and the sky stays clear, with rain falling, until the weather next changes (VYSE does not cause it, and it goes away when the weather changes). A resource pack cannot touch the weather, so this separate behavior pack is there for those who want it fixed: 3 seconds after you join, if it is raining, it stops the rain for a moment and starts it again, which brings the rainy sky back.

In Minecraft, **a world with any behavior pack you imported cannot earn achievements**, whatever the pack does. Leave it out of worlds where you want achievements and use the resource pack alone.

## Requirements

- Minecraft Bedrock Edition 1.26.0 or later
- A device that can run Vibrant Visuals (Settings > Video)

## Installation

1. Open the pack's `.mcpack`; the game imports it.
2. Settings > Video: turn on Vibrant Visuals.
3. World settings > Resource Packs: activate "VYSE-Vibrant Visuals".
4. Optional: open the Weather Sync `.mcpack` too, then World settings > Behavior Packs: activate "VYSE Weather Sync" (that world can no longer earn achievements).

## Notes

- Nothing changes while Vibrant Visuals is off.
- The painted clouds are an image fixed in the sky; they do not move.
- Effects that need new shaders (waving grass, moving clouds, depth of field) are not possible in a resource pack.
- The look can differ a little between devices and game versions.

## About the PBR add-on

A "VYSE-Vibrant Visuals PBR" add-on (block relief, gloss and glow, mobs wet in rain) also exists. It contains Mojang's textures, so it is not offered as a file: a dedicated page **builds it on your own device**, reading the images straight from Mojang's official bedrock-samples. The result is for your own use and may not be redistributed.

## Terms of use and credits

- By aorin-ars
- You may use it in your own game and publish screenshots and videos.
- **Modifying, redistributing (re-uploading) and selling it are not allowed.** To share it, link to this page.
- Inspired by the look of Java shader packs such as Complementary Shaders; unofficial and not affiliated with their authors. No code or assets are taken from them.
- NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.
