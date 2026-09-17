# Vibrant Visuals

**日本語** | [English](README.en.md)

Minecraft の見た目を、影mod のような画に寄せるパックです。**統合版（Bedrock）**と
**Java版**の両方が入っています。

| | 中身 | 導入先 |
|---|---|---|
| [`bedrock/`](bedrock/) | Vibrant Visuals（遅延レンダリング）用リソースパック | `.mcpack` を開く |
| [`java/`](java/) | Iris / OptiFine 用シェーダーパック | `.minecraft/shaderpacks/` |

> **統合版と Java版でパックの形式はまったく別物です。** Java版のシェーダーパックを
> 統合版に入れても、一覧にすら出てきません（逆も同じ）。

---

# 統合版（Bedrock）

## 必要なもの

- Minecraft 統合版 **1.21.80 以降**
- ビデオ設定で **Vibrant Visuals が有効**になっていること

## 導入

1. `VibrantVisuals-*.mcpack` をタップ／ダブルクリックして開く（自動でインポートされます）
2. **設定 → ビデオ → Vibrant Visuals** を **オン**にする
3. ワールドの **設定 → リソースパック** でこのパックを有効にする

手動で入れる場合は、zip を展開して `com.mojang/resource_packs/` に置いてください。

## エンティティの影について

**エンティティが自分の形の影を落とすこと自体は、Vibrant Visuals 本体の機能です。**
ビデオ設定でオンにすれば、列車も船も Mob も形どおりの影を落とします。

その上で、**影の品質はリソースパックから設定できます**（`shadows/global.json`）。

| 項目 | このパック | 意味 |
|---|---|---|
| `shadow_style` | `soft_shadows` | 影の輪郭を柔らかくする |
| `texel_size` | 2048 | シャドウマップの解像度。上げるほど細部（窓枠・手すり・台車）が影に出ます |

`texel_size` が効きすぎて重い場合は 1024 に下げてください。

リソースパックで変えられる範囲は次のとおりです。

| 変えられる | 変えられない |
|---|---|
| 影の柔らかさ・シャドウマップ解像度 | どのエンティティが影を落とすか |
| 太陽・月の明るさと色 | 影のバイアス（縞模様の調整） |
| 環境光と空の光の強さ | シェーダーコードそのもの |
| 大気の散乱（空の色、霞、太陽のグレア） | |
| 色調（コントラスト・彩度・色温度） | |
| 水（波・コースティクス・濁り） | |
| PBR（金属感・粗さ・発光）のブロック／エンティティ既定値 | |

**影を「濃く・はっきり」見せるもう一つの方法は、太陽を強くして環境光を下げることです。**

| 項目 | バニラ | このパック | 狙い |
|---|---|---|---|
| 太陽の照度（正午） | 100 | 132 | 直射光を強め、影との差を広げる |
| 環境光 | 0.02 / 白 | 0.014 / 青白 (`#BFD4FF`) | 影を「黒く潰す」のではなく「空の青で満たす」 |
| 空の強さ | 1.0 | 1.30 | 同上。影の中に青が回り込む |
| Rayleigh 散乱 | 10 | 14 | 天頂の青を深く |
| 太陽の Mie 散乱（昼） | 0.0 | 0.22 | 昼間も太陽まわりが光る |
| コントラスト / 彩度 | 1.15 / 1.05 | 1.22 / 1.14 | 写真的な締まり |
| 水の波 | 無効 | 有効 | 水面が動く |
| エンティティの粗さ | 255 | 205 | 車体や生き物に少し艶を出す |

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
粗さを下げるほど艶が出ます。

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

> 画像を用意せず数値だけで指定する書き方もあります（`pbr/global.json` と同じ
> `[金属度, 発光, 粗さ, 表面下散乱]` の配列）。こちらは実在の Vibrant Visuals
> パックで使われているのを確認しています。

## 効き目が弱い／強すぎるとき

`bedrock/` の JSON を直接編集してください。数字を書き換えるだけです。

| やりたいこと | 触る場所 |
|---|---|
| 影をもっと濃く | `lighting/global.json` の `ambient.illuminance` を下げる |
| 影の青みを強く | 同 `ambient.color` をより青く |
| 日差しをもっと強く | 同 `sun.illuminance` の各値を上げる |
| 空をもっと青く | `atmospherics/atmospherics.json` の `rayleigh_strength` |
| 色を落ち着かせる | `color_grading/color_grading.json` の `saturation` / `contrast` |
| 水の波を止める | `water/water.json` の `waves.enabled` を `false` |
| 影をシャープに | `shadows/global.json` の `texel_size` を上げる（重くなります） |
| エンティティの艶を強く | `pbr/global.json` の `actors` の3番目（粗さ）を下げる |

編集後は検証できます。

```bash
python3 tools/check_bedrock.py
```

キー名を打ち間違えても Minecraft は何も言わずに無視するので、このチェックを通して
から入れてください。

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

```bash
python3 tools/check_bedrock.py        # 統合版パックの検証（キー名のタイポも検出）
python3 tools/validate_shaders.py     # Java版 GLSL を全52ステージ×4構成でコンパイル
python3 tools/check_options.py        # Java版の設定項目の整合性
tools/package.sh                      # 両方の配布ファイルを生成
```

`glslangValidator` が PATH に無い場合は `--glslang <path>` を渡してください
（[ビルド済みバイナリ](https://github.com/KhronosGroup/glslang/releases)）。

## ライセンス

MIT License — [LICENSE](LICENSE) を参照してください。
