// Builds the PBR add-on with the web version (web/pbr/lib) in Node and
// compares it file by file with tools/build_pbr.py's output.
//
//   python3 tools/build_pbr.py --vanilla $V --out build/pbr --patch 0
//   node web/pbr/check_against_python.mjs --vanilla $V --python build/pbr
//
// Images are compared by their pixels (the two encoders write different
// bytes), JSON by its parsed content, everything else byte for byte.

import { readFile, readdir } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { buildPbr } from "./lib/pbr.js";
import { decodeImage } from "./lib/image.js";

function arg(name) {
  const i = process.argv.indexOf(name);
  if (i < 0 || !process.argv[i + 1]) {
    console.error("usage: node web/pbr/check_against_python.mjs --vanilla <resource_pack> --python <build/pbr>");
    process.exit(2);
  }
  return process.argv[i + 1];
}

async function walk(dir, root = dir, out = []) {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) await walk(p, root, out);
    else out.push(relative(root, p).split(sep).join("/"));
  }
  return out;
}

const vanilla = arg("--vanilla"), pythonOut = arg("--python");
const WANTED = /^(textures\/|entity\/[^/]+\.json$|render_controllers\/[^/]+\.json$)/;
const source = {
  files: new Set((await walk(vanilla)).filter((p) => WANTED.test(p))),
  read: async (p) => new Uint8Array(await readFile(join(vanilla, p))),
};

const pyFiles = new Set(await walk(pythonOut));
const pyManifest = JSON.parse(await readFile(join(pythonOut, "manifest.json"), "utf8"));
const icon = pyFiles.has("pack_icon.png") ? new Uint8Array(await readFile(join(pythonOut, "pack_icon.png"))) : null;

const t0 = Date.now();
const { files: js, stats } = await buildPbr(source, { patch: pyManifest.header.version[2], icon });
console.log(`web build: ${js.size} files in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
console.log(JSON.stringify(stats));

const onlyPy = [...pyFiles].filter((p) => !js.has(p)).sort();
const onlyJs = [...js.keys()].filter((p) => !pyFiles.has(p)).sort();
let differ = 0, pixelDiffs = 0, worst = 0;
const problems = [];
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x)
  ? Object.fromEntries(Object.entries(x).sort(([a], [b]) => (a < b ? -1 : 1))) : x));

for (const p of [...js.keys()].filter((p) => pyFiles.has(p)).sort()) {
  const a = js.get(p), b = new Uint8Array(await readFile(join(pythonOut, p)));
  if (p.endsWith(".json")) {
    const pa = JSON.parse(new TextDecoder().decode(a)), pb = JSON.parse(new TextDecoder().decode(b).replace(/^﻿/, ""));
    if (canon(pa) !== canon(pb)) { differ++; problems.push(`${p}: JSON differs`); }
  } else if (/\.(png|tga)$/i.test(p) && !Buffer.from(a).equals(Buffer.from(b))) {
    const ia = await decodeImage(p, a), ib = await decodeImage(p, b);
    if (ia.width !== ib.width || ia.height !== ib.height) { differ++; problems.push(`${p}: size differs`); continue; }
    let n = 0, max = 0;
    for (let i = 0; i < ia.data.length; i++) {
      const d = Math.abs(ia.data[i] - ib.data[i]);
      if (d) { n++; max = Math.max(max, d); }
    }
    if (n) { differ++; pixelDiffs += n; worst = Math.max(worst, max); problems.push(`${p}: ${n} values differ, by up to ${max}`); }
  } else if (!Buffer.from(a).equals(Buffer.from(b))) {
    differ++; problems.push(`${p}: bytes differ`);
  }
}

console.log(`python: ${pyFiles.size} files, web: ${js.size} files`);
console.log(`only in python: ${onlyPy.length}${onlyPy.length ? " e.g. " + onlyPy.slice(0, 5).join(", ") : ""}`);
console.log(`only in web:    ${onlyJs.length}${onlyJs.length ? " e.g. " + onlyJs.slice(0, 5).join(", ") : ""}`);
console.log(`differing:      ${differ}${pixelDiffs ? ` (${pixelDiffs} channel values, worst by ${worst})` : ""}`);
for (const line of problems.slice(0, 20)) console.log("  " + line);
process.exit(onlyPy.length || onlyJs.length || differ ? 1 : 0);
