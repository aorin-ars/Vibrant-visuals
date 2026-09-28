# Vibrant Visuals

**日本語** | [English](README.en.md)

Minecraft の見た目を、影mod のような画に寄せるパックです。**統合版（Bedrock）**と
**Java版**の両方が入っています。

| | 中身 | 導入先 |
|---|---|---|
| [`bedrock/`](bedrock/) | **Vibrant Unbound** — Complementary Unbound 風の Vibrant Visuals 用リソースパック | `.mcpack` を開く |
| [`java/`](java/) | Iris / OptiFine 用シェーダーパック | `.minecraft/shaderpacks/` |

> **統合版と Java版でパックの形式はまったく別物です。** Java版のシェーダーパックを
> 統合版に入れても、一覧にすら出てきません（逆も同じ）。

---

# 統合版（Bedrock）: Vibrant Unbound

Java版の影mod **Complementary Shaders（Unbound スタイル）** の画作りを、統合版の
Vibrant Visuals で再現するリソースパックです。

## 必要なもの

- Minecraft 統合版 **1.26.0 以降**
- ビデオ設定で **Vibrant Visuals が有効**になっていること

## 導入

1. `VibrantUnbound-*.mcpack` をタップ／ダブルクリックして開く（自動でインポートされます）
2. **設定 → ビデオ → Vibrant Visuals** を **オン**にする
3. ワールドの **設定 → リソースパック** でこのパックを有効にする

**追加パック（任意）**: `VibrantUnbound-Relief-*.mcpack` を一緒に有効にすると、
石・木材・鉱石などのブロックに凹凸が付きます（Complementary の「Generated Normals」相当）。
バニラのテクスチャから作るため、リポジトリには入っていません（[作り方](#開発)）。
**個人利用のみ**で、再配布はしないでください。

手動で入れる場合は、zip を展開して `com.mojang/resource_packs/` に置いてください。

## 何が変わるか

| | バニラの Vibrant Visuals | Vibrant Unbound |
|---|---|---|
| 日差し | 白っぽく、夕方は早めに暗くなる | 正午は**強く澄んだ白**で 125（バニラ 100）。日向と日陰の差がはっきり出る。日が低くなると金色、地平線でオレンジから赤 |
| 時間帯の空 | 控えめ | 参考画像に合わせて、早朝（マゼンタからオレンジ金、上空は深い青）→ 朝（青空に暖かいクリーム色の地平線）→ 昼（深い青から淡い青）→ 夕方（金色からオレンジ）→ 日没（地平線は赤橙、上空は紫）→ 夜（紺色）→ 深夜（濃紺）。星の見える紺色の夜で、真っ黒にはしない |
| 空 | くすんだ青灰色 | 天頂は鮮やかな深い青、地平線も白くかすまない青。太陽は小さく、まわりの光はごく控えめ |
| 影 | 灰色 | 短くはっきりした影（正午の太陽は高さ 78°）。影の中は黒く潰れず、空の光で青みがかったグレーに。夜は月明かりで青く見える（月 0.7、バニラ 0.4） |
| 空気 | 一部のバイオームだけ一様な霧 | **澄んだ空気**。霞はごく薄く、遠景をわずかに和らげる程度（低い所ほど濃く、上空ほど薄い）。湿った森や沼だけ少し多め |
| 雨 | — | 雨の日は霞が濃くなる |
| 水 | 波なし・昔の水の模様 | **透明な水**。バニラの水の模様（白い筋）と凹凸マップを外し、小さなさざ波だけにしたので、空や岸がきれいに映る。バイオームの水の色がほんのり混ざる |
| 水中 | — | ゲーム標準のまま（以前入れていた水中の霧は、自分の影が黒い影として映り込むため外しました） |
| ブロックの光 | 一律の色 | **色付き**: 松明・炎は橙、魂の炎は水色、レッドストーンは赤、紫水晶・エンダー系は紫、シーランタンは水色がかった白 など 106 種 |
| 太陽・月 | 四角 | **丸い太陽**（やわらかい光冠付き）と**丸い月**（クレーター付き、8 つの満ち欠け） |
| 雲 | 四角い雲の板 | **空に描いた積雲と巻雲**（スカイボックス）。夕方は日の色に染まる。[下を参照](#空の雲スカイボックス) |
| 色調 | コントラスト 1.15 / 彩度 1.05 | コントラスト 1.24 / 彩度 1.28。標準の Vibrant Visuals とはっきり違う、鮮やかで締まった色。暗部はわずかに青く、明部はわずかに暖かく |

### すべてのバイオームに効かせている理由

統合版 1.21.90 以降、ジャングル・砂漠・タイガ・メサ・ネザー・エンドなど多くのバイオームは
**バイオーム専用の照明・大気・色調設定**を持っていて、それが `lighting/global.json` などの
全体設定より優先されます。全体設定だけを書き換えるパックは、平原や森でしか効きません。

このパックは、バニラのバイオームが参照している識別子（照明 15・大気 17・色調 14・水 1）を
**すべて同じ名前で上書き**しています。どのバイオームにいても同じ画作りになり、その上で
砂漠は少し暖かく、雪原は少し白く、といった差を付けています。

## 空の雲（スカイボックス）

統合版は、6 枚の画像（`textures/environment/overworld_cubemap/cubemap_0〜5.png`）で
オーバーワールドの空を描き替えられます。1.21.130 からは Vibrant Visuals でもその画像が
太陽や空の光で照らされるようになりました（`cubemaps/default_cubemap.json`）。

このパックはこの仕組みで、**背景が透明な雲の画像**を空に貼っています。雲以外の部分からは
いつもの Vibrant Visuals の空が見えるので、空の色・夕焼け・夜はそのまま時間で変わり、
雲だけが日の色（昼は白、夕方は金色からピンク）に照らされます。

雲は**パックの設定で選べます**。ワールドの設定 → リソースパック → 有効にした
Vibrant Unbound をタップ → 歯車（⚙）から切り替えてください。

| 選択肢 | 中身 | バニラの雲 |
|---|---|---|
| **空: Unbound の雲**（初期設定） | ふわっとした積雲と、高いところの薄い巻雲 | **自動で消えます**（四角い板の雲は表示されません） |
| 空: 高い雲だけ | 薄い巻雲だけ | オンのままでよい（影を落とすバニラの雲と組み合わせる用） |
| 空: 雲なし | 何も貼らない | お好みで |

知っておいてほしいこと:

- 描いた雲なので**動きません**（空に固定されています）
- 雲は地平線の近くまで広がります。遠くの雲は画像の中で淡い青に溶かしてあります（ゲームの霞をかけると低い雲が消えてしまったため）
- 効くのはオーバーワールドだけです（ネザーとエンドは変わりません）
- 雲の明るさの設定値は、実際にこの方式で雲を貼っている公開パックの値を参考にしたもので、
  このパック自体はまだ実機で確かめていません。昼・夕方・夜に雲がどう見えたか教えてもらえれば
  調整します

画像の並び（0〜3 が左から右へ並ぶ側面、4 が上、5 が下）は、実際に動いている
スカイボックス数個の画像の境目を突き合わせて確認しました。雲は、地球の丸みに沿って空に
かかる層に描いた模様（晴れた日の積雲のように、ひとつずつ離れたかたまり）を視線の方向から
投影しているので、真上では大きく、地平線に向かって小さく並び、画像の境目もつながります。

## Complementary との違い（リソースパックではできないこと）

Vibrant Visuals の見た目はエンジンのシェーダーが決めていて、リソースパックが変えられるのは
**数値の設定とテクスチャだけ**です。Complementary の次の機能は再現できません。

- 草や葉が風で揺れる
- **動く**立体的な雲・オーロラ・星雲（雲は上のとおり、空に描いた止まった雲なら可能）
- 雨の水たまり・濡れた地面の反射
- 被写界深度・モーションブラー・レンズフレア

時間帯で霞の濃さを変えることもできません（霧の設定はキーフレームに対応していないため）。

## エンティティの影について

**エンティティが自分の形の影を落とすこと自体は、Vibrant Visuals 本体の機能です。**
ビデオ設定でオンにすれば、列車も船も Mob も形どおりの影を落とします。
影の細かさはビデオ設定の影の品質で決まり、リソースパックからは変えられません。

リソースパックから変えられるのは影の**スタイル**だけです（`shadows/global.json`）。

| 項目 | このパック | 意味 |
|---|---|---|
| `shadow_style` | `soft_shadows` | 輪郭の柔らかい影。`blocky_shadows` にするとドット絵風の角ばった影になる |
| `texel_size` | 16 | `blocky_shadows` のとき、影をどの細かさのマス目にそろえるか。`soft_shadows` では使われない |

> 以前のこのパックでは `texel_size` を「シャドウマップの解像度」と説明していましたが、
> 誤りでした。影の細かさを上げる効果はありません。

## manifest の `capabilities`

```json
"capabilities": ["pbr"]
```

**この1行が無いと、`lighting` や `atmospherics` などのファイルはすべて無視されます。**
テクスチャの差し替えだけは効くので「パックは入っているのに見た目が変わらない」という
分かりにくい壊れ方をします。`tools/check_bedrock.py` はこれを検出します。

## 列車などのアドオンを金属っぽく見せる

Vibrant Visuals は PBR（金属感・粗さ・発光）に対応しています。アドオンのテクスチャに
**テクスチャセット**を足すと、塗装された車体らしい艶が出ます。

一番手軽なのは、パック全体のエンティティ既定値を変えることです
（`pbr/global.json` の `actors`）。数値は `[金属度, 発光, 粗さ, 表面下散乱]` で、
粗さを下げるほど艶が出ます（このパックは 215、バニラは 255）。

個別に作り込むなら、アドオンの `textures/entity/` にあるテクスチャ `my_train.png`
に対して、同じ場所に `my_train.texture_set.json` を置きます。

```json
{
  "format_version": "1.21.30",
  "minecraft:texture_set": {
    "color": "my_train",
    "metalness_emissive_roughness_subsurface": "my_train_mers"
  }
}
```

`my_train_mers.png` は色テクスチャと同じ大きさの画像で、各チャンネルが次を表します。

| チャンネル | 意味 | 車体の目安 |
|---|---|---|
| R | 金属度 | 塗装 0、無塗装ステンレス 255 |
| G | 発光 | 行先表示・前照灯 200〜255、他 0 |
| B | 粗さ | 磨かれた車体 40〜70、艶消し 180〜 |
| A | 表面下散乱 | 通常 0 |

テクスチャセットが参照する画像は、**テクスチャセットと同じパックの同じフォルダ**に
無いと無視されます（別のパックにある画像は使えません）。

## 調整したいとき

設定ファイルは `tools/generate_bedrock.py` から生成しています。数値はこのスクリプトの
先頭近くにまとまっているので、そこを変えて再生成するのが確実です
（JSON を直接編集しても動きますが、再生成すると上書きされます）。

| やりたいこと | `tools/generate_bedrock.py` の場所 |
|---|---|
| 日差しを強く／弱く | `SUN_ILLUMINANCE` |
| 夕焼けの色 | `SUN_COLOR`（光の色）と `sky_tables` の `golden` / `sunset` など（空の色） |
| 空をもっと青く | `DAY_ZENITH`（天頂の色）と `RAYLEIGH` |
| 影を暗く／明るく | `AMBIENT_ILLUMINANCE` |
| 夜を明るく | `MOON_ILLUMINANCE` |
| 霞を薄く／濃く | `HAZE` の `clear` などの最初の数値（濃さ） |
| 光芒を強く | `HAZE` の3番目の数値（前方散乱。1 に近いほど太陽方向に集中） |
| 色を落ち着かせる | `BASE_GRADE` の `saturation` / `contrast` |
| 水の波を止める | `WATER` の `waves.enabled` を `False` |
| 水の色をバイオームに寄せる | `WATER` の `biome_water_color_contribution`（0〜1） |
| ブロックの光の色 | `LIGHT_COLORS` |
| 雲の明るさ・夕焼けの染まり方 | `CLOUD_CUBEMAP` の `ambient_light_illuminance`（明るさ）と `directional_light_contribution`（日の色の強さ） |
| 雲の量 | `tools/draw_sky.py` の `CLOUD_VARIANTS` の `coverage`（空の何割を雲にするか） |
| 太陽の軌道の傾き | `ORBITAL_OFFSET`（度） |

```bash
python3 tools/generate_bedrock.py --vanilla <bedrock-samples>/resource_pack
python3 tools/check_bedrock.py --vanilla <bedrock-samples>/resource_pack
```

キー名を打ち間違えたり範囲外の値を入れたりしても Minecraft は何も言わずに無視するので、
このチェックを通してから入れてください。

---

# Java版

Iris / OptiFine 用の遅延レンダリングシェーダーパックです。**エンティティがモデル
そのものの形の影を落とす**ことを中心に組んであります（統合版と違い、影の仕組み自体を
シェーダー側で書いています）。

- 必要環境: **Iris 1.6 以降**（推奨）または **OptiFine H9 以降** / Minecraft 1.16.5 〜 1.21.x
- 導入: `VibrantVisuals-Java-*.zip` を `.minecraft/shaderpacks/` に置く
- 詳細: [docs/ENTITY_SHADOWS.md](docs/ENTITY_SHADOWS.md) / [docs/PIPELINE.md](docs/PIPELINE.md)

設定画面は日本語表示に対応しています。プロファイルは `最低` / `低` / `中` / `高` / `最高`。
列車のような長い編成では `高` を選んでから、`影の描画距離` と `エンティティの影範囲` を
上げてください。

---

## 開発

統合版の生成・検証には Mojang のバニラリソースパック
（[Mojang/bedrock-samples](https://github.com/Mojang/bedrock-samples) の `resource_pack`）と、
Python の Pillow / numpy が要ります。

```bash
git clone --depth 1 https://github.com/Mojang/bedrock-samples
pip install pillow numpy
V=bedrock-samples/resource_pack

python3 tools/generate_bedrock.py --vanilla $V   # 設定ファイルを生成（bedrock/ と diagnostic/）
python3 tools/draw_sky.py                        # 丸い太陽と月、雲のスカイボックスを描く（数分かかる）
python3 tools/draw_water.py                      # 模様のない水のテクスチャ
python3 tools/check_bedrock.py --vanilla $V      # 統合版パックの検証（キー名・値の範囲・全バイオーム網羅）
tools/package.sh --vanilla $V                    # 配布ファイルを生成（凹凸追加パックを含む）

python3 tools/validate_shaders.py     # Java版 GLSL を全52ステージ×4構成でコンパイル
python3 tools/check_options.py        # Java版の設定項目の整合性
```

`glslangValidator` が PATH に無い場合は `--glslang <path>` を渡してください
（[ビルド済みバイナリ](https://github.com/KhronosGroup/glslang/releases)）。

## ライセンス

MIT License — [LICENSE](LICENSE) を参照してください。
凹凸追加パック（`tools/build_pbr.py` の出力）は Mojang のテクスチャを含むため、
このライセンスの対象外で、個人利用に限ります。
