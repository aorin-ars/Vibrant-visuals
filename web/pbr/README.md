# VYSE-Vibrant Visuals PBR — ブラウザで作るための部品

PBR 追加パック（ブロックの凹凸・光るブロックと鉱石・氷や金属の艶・雨で濡れるエンティティ）を、
**プレイヤー自身の端末のブラウザの中で**組み立てるための JavaScript です。aorin.net のページに
組み込んで使う前提で、ページ（UI）はここには含めていません。

## なぜブラウザで作るのか

テクスチャセットは同じパックの中の画像しか参照できないため、PBR パックには Mojang のブロック画像が
入ります。これは配布できません。そこで、

- サイトが配るのは **組み立てる道具（このフォルダの JS）だけ**。Mojang の画像は 1 枚も含まない
- 画像は、プレイヤーの端末が **Mojang 公式の [bedrock-samples](https://github.com/Mojang/bedrock-samples)** から直接取得する
- パックは端末の中で組み立てて、そのままダウンロードする（サーバーには何も送らない）

という形にしています。できたパックは自分用です。ページには「再配布しないでください」と書いてください。

## 中身

| ファイル | 役割 |
|---|---|
| `lib/index.js` | 入口。`buildPbrMcpack` / `buildFullMcpack` / `githubSource` / `folderSource` |
| `lib/pbr.js` | 組み立ての本体。`tools/build_pbr.py` と `tools/wet_entities.py` の移植 |
| `lib/sources.js` | バニラのファイルの読み先（GitHub / 端末のフォルダ） |
| `lib/image.js` | PNG・TGA の読み書き（ライブラリなし） |
| `lib/zip.js` | .mcpack（zip）の読み書き（ライブラリなし） |
| `pbr_pack_icon.png` | パックのアイコン（`branding/pbr_pack_icon.png` と同じ） |
| `check_against_python.mjs` | Python 版と出力を突き合わせる検証（開発用、Node） |
| `make_file_list.mjs` | バニラのファイル一覧 JSON を作る（任意、Node） |

外部ライブラリは使っていません。ES モジュールなので、そのまま `<script type="module">` で読めます。
`lib/` を丸ごとサイトに置いてください（相対パスで互いを読み込みます）。

## 使い方（最小）

```html
<button id="go">PBR パックを作る</button>
<progress id="bar" max="1" value="0"></progress>
<p id="msg"></p>
<script type="module">
import { githubSource, buildPbrMcpack } from "./lib/index.js";

document.getElementById("go").onclick = async () => {
  const msg = document.getElementById("msg"), bar = document.getElementById("bar");
  try {
    msg.textContent = "バニラのファイル一覧を取得中…";
    const source = await githubSource();            // 最新リリースのバニラ
    const icon = new Uint8Array(await (await fetch("./pbr_pack_icon.png")).arrayBuffer());
    const result = await buildPbrMcpack({
      source, icon,
      onProgress: ({ stage, done, total }) => {
        msg.textContent = { textures: "ブロックを処理中", "wet entities": "エンティティを処理中", zip: "まとめています" }[stage]
          + ` ${done}/${total}`;
        bar.value = done / total;
      },
    });
    const url = URL.createObjectURL(new Blob([result.bytes], { type: "application/octet-stream" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: result.filename });
    a.textContent = `${result.filename} をダウンロード`;
    msg.replaceChildren(a);
  } catch (e) {
    msg.textContent = "失敗しました: " + e.message;
  }
};
</script>
```

### Full パック（本体＋PBR を 1 つに）

本体の `.mcpack`（配布しているもの）を読み込ませると、`tools/release.py` と同じ統合版も作れます。
本体はサイトに置いたものを `fetch` しても、プレイヤーに選ばせても構いません。

```js
import { buildFullMcpack } from "./lib/index.js";
const mainPack = new Uint8Array(await (await fetch("./VYSE-Vibrant-Visuals-v3.3.52.mcpack")).arrayBuffer());
const full = await buildFullMcpack({ mainPack, pbrFiles: result.files });   // result は buildPbrMcpack の戻り値
// full.bytes / full.filename
```

### 端末のフォルダから読む（ネットを使わない）

bedrock-samples をダウンロード済みの人向けです。

```html
<input type="file" id="dir" webkitdirectory>
<script type="module">
import { folderSource, buildPbrMcpack } from "./lib/index.js";
document.getElementById("dir").onchange = async (e) => {
  const source = folderSource(e.target.files);   // resource_pack かその上のフォルダ
  const result = await buildPbrMcpack({ source });
};
</script>
```

## 知っておくこと

- **対応ブラウザ**: `CompressionStream("deflate-raw")` が必要です。Chrome / Edge 103 以降、
  Firefox 113 以降、Safari 16.4 以降（iPhone は iOS 16.4 以降）。
- **時間と通信量**: 実測で約 80 秒、ダウンロード約 22 MB、できるパックは約 6 MB
  （v1.26.60.5、回線による）。モバイル回線ではその旨を表示してください。
- **GitHub API の制限**: `githubSource()` はファイル一覧の取得に GitHub API を 3 回呼びます。
  未ログインの API は 1 時間に 60 回（IP ごと）までです。気になる場合は、ファイル一覧の JSON を
  サイトに置き、API を使わないようにできます（中身はファイル名だけで、Mojang の画像は含みません）。

  ```bash
  node web/pbr/make_file_list.mjs --vanilla bedrock-samples/resource_pack --tag v1.26.60.5 > vanilla-files.json
  ```

  ```js
  const { tag, files } = await (await fetch("./vanilla-files.json")).json();
  const source = await githubSource({ tag, fileList: files });
  ```

  画像本体は raw.githubusercontent.com から取得します。こちらはどのサイトからでも読めます（CORS 許可済み）。
- **バージョン番号**: パックのバージョンの 3 番目は、作った時刻（2026-01-01 からの分）です。
  統合版は同じ番号のパックを入れ直さないため、作るたびに上がるようにしています。
- **識別子（UUID）**: Python 版と同じです。どちらで作ったものでも、同じパックの新しい版として上書きされます。

## Python 版との対応

`lib/pbr.js` は `tools/build_pbr.py` と `tools/wet_entities.py` の移植です。Pillow のぼかしや
numpy の丸め方まで合わせてあり、v1.26.60.5 のバニラで 7448 ファイルすべてが同じになりました。
ただし、法線マップ 1 枚の 2 つの値だけが 1 ずれます（浮動小数点の端数の差で、見た目では分かりません）。
画像は画素で、JSON は内容で比べています。

Python 側の数値（凹凸の強さ・光り方など）を変えたら、`lib/pbr.js` の同じ表も変えてから確かめてください。

```bash
python3 tools/build_pbr.py --vanilla $V --out build/pbr
node web/pbr/check_against_python.mjs --vanilla $V --python build/pbr
```
