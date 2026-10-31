VYSE-Vibrant Visuals v{version}
==============================

統合版（Bedrock）の Vibrant Visuals を、影MODのような映画風の映像にするリソースパックです。
English below.

■ 必要なもの
- Minecraft 統合版 1.26.0 以降
- Vibrant Visuals に対応した端末（設定 → ビデオで Vibrant Visuals を選べること）

■ 入っているファイル
- VYSE-Vibrant-Visuals-v{version}.mcaddon
    本体と Weather Sync をまとめて読み込みます（おすすめ）
- VYSE-Vibrant-Visuals-v{version}.mcpack
    本体（リソースパック）だけ
- VYSE-Weather-Sync-v{bp_version}.mcpack
    雨の空の修正（ビヘイビアーパック・任意）だけ
- LICENSE.txt
    利用規約

■ 導入
1. .mcaddon（または .mcpack）をタップ／ダブルクリックして開きます。自動で読み込まれます。
2. 設定 → ビデオで、Vibrant Visuals をオンにします。
3. ワールドの設定 → リソースパックで「VYSE-Vibrant Visuals」を有効にします。
4. （任意）ワールドの設定 → ビヘイビアーパックで「VYSE Weather Sync」を有効にします。
   雨のままワールドを開き直すと、空が晴れたまま雨が降るゲームの不具合を直します。
   ※ビヘイビアーパックを入れたワールドでは実績が解除されなくなります。
     実績が必要なワールドでは入れないでください（本体だけでも問題なく使えます）。

■ 空の種類・軽量化モード
リソースパックの一覧で VYSE-Vibrant Visuals をタップ → 歯車（⚙）から選べます。
- Sky: soft clouds（初期設定）
    空一面のふわふわの雲。ゲームの四角い雲は自動で消えます
- Sky: soft clouds, fewer
    雲が少なめ（青空が多い）
- Sky: soft clouds, more
    雲が多め（v3.2 までの量）
- Sky: soft clouds + the game's clouds
    描いた雲とゲームの雲の両方
- Sky: no clouds
    描いた雲なし
- Lite: the game's clouds, faster
    軽量化モード。描いた雲を使わず、水面の波の計算を軽くします
    さらに軽くしたいときは、ビデオ設定でアップスケーリングをオン、点光源の影をオフ、
    ボリュメトリックフォグを低〜中にするのが効果的です

■ 注意
- Vibrant Visuals がオフのときは何も変わりません。
- 描いた雲は空に固定された画像なので動きません。
- 見た目は端末やゲームのバージョンによって少し変わることがあります。

■ 利用規約
(c) 2026 aorin-ars. All rights reserved.
自分の Minecraft で使うこと、スクリーンショットや動画を公開することはできます。
改変・再配布（転載）・販売は禁止です。詳しくは LICENSE.txt を見てください。


------------------------------------------------------------
English
------------------------------------------------------------

A resource pack that gives Minecraft Bedrock's Vibrant Visuals a filmic,
shader-like look.

Requirements
- Minecraft Bedrock Edition 1.26.0 or later
- A device that can run Vibrant Visuals (Settings > Video)

Files
- VYSE-Vibrant-Visuals-v{version}.mcaddon   the pack and Weather Sync together (recommended)
- VYSE-Vibrant-Visuals-v{version}.mcpack    the resource pack alone
- VYSE-Weather-Sync-v{bp_version}.mcpack   the optional behavior pack alone
- LICENSE.txt                               terms of use

Install
1. Open the .mcaddon (or .mcpack); the game imports it.
2. Settings > Video: turn on Vibrant Visuals.
3. World settings > Resource Packs: activate "VYSE-Vibrant Visuals".
4. Optional: World settings > Behavior Packs: activate "VYSE Weather Sync".
   It fixes a game bug where reopening a world while it rains shows a clear
   sky with rain falling. Note: a world with a behavior pack cannot earn
   achievements; the resource pack works fine on its own.

Sky options and lite mode: tap VYSE-Vibrant Visuals in the resource pack
list, then the gear.
- Sky: soft clouds (default)              soft clouds across the sky; the game's
                                          blocky clouds are hidden
- Sky: soft clouds, fewer                 fewer clouds, more blue sky
- Sky: soft clouds, more                  more clouds (the amount up to v3.2)
- Sky: soft clouds + the game's clouds    both
- Sky: no clouds                          no painted clouds
- Lite: the game's clouds, faster         lite mode: no sky images, lighter water

Notes
- Nothing changes while Vibrant Visuals is off.
- The painted clouds are an image fixed in the sky; they do not move.
- The look can differ a little between devices and game versions.

Terms of use: (c) 2026 aorin-ars. All rights reserved. You may use it in your
own game and publish screenshots and videos; modifying, redistributing
(re-uploading) and selling it are not allowed. See LICENSE.txt.
