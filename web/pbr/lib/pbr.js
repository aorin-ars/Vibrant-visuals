// The PBR add-on - relief, glow, shine and wet entities - built from the
// vanilla textures, in the browser (or Node). A port of tools/build_pbr.py
// and tools/wet_entities.py: the same tables, the same arithmetic, the same
// output files. Keep the two in step: web/pbr/check_against_python.mjs
// builds both and compares them.
//
// The output contains Mojang's textures (a texture set may only reference
// images in its own pack), so it is never shipped: each player builds it on
// their own device from Mojang's own files. See web/pbr/README.md.
//
// A source is { files: Set<string>, read(path): Promise<Uint8Array> } with
// paths relative to the vanilla resource_pack folder, e.g.
// "textures/blocks/stone.png". See sources.js.

import { decodeImage, encodePNG, encodeTGA } from "./image.js";

// ------------------------------------------------------------------ tables
// Copied from tools/build_pbr.py; see the comments there.

const RELIEF_BY_MATERIAL = [
  ["fire_*", 0.0], ["soul_fire_*", 0.0], ["portal*", 0.0], ["*bubble_column*", 0.0],
  ["water_*", 0.0], ["cauldron_water*", 0.0], ["end_gateway*", 0.0],
  ["*glass*", 0.3], ["iron_bars", 0.6], ["*door*", 1.0], ["*trapdoor*", 1.0],
  ["ladder", 1.0], ["rail*", 0.8],
  ["*glazed_terracotta*", 0.25], ["concrete_powder*", 0.6], ["concrete_*", 0.25],
  ["ice*", 0.2], ["blue_ice", 0.2],
  ["wool_*", 0.5], ["hardened_clay*", 0.5], ["quartz*", 0.5], ["*smooth*", 0.5],
  ["polished_*", 0.6], ["*_block", 0.7], ["cut_copper*", 0.7], ["*copper_block", 0.7],
  ["snow", 0.6], ["clay", 0.6], ["mud", 0.8], ["sand", 0.8], ["red_sand", 0.8],
  ["*_ore", 1.6], ["deepslate/*_ore", 1.6], ["cobblestone*", 1.7], ["*cobbled*", 1.7],
  ["bedrock", 1.7], ["stone", 1.4], ["netherrack", 1.5], ["end_stone", 1.4],
  ["blackstone*", 1.4], ["basalt*", 1.4], ["tuff*", 1.3], ["dripstone*", 1.4],
  ["gravel", 1.3], ["*brick*", 1.5], ["deepslate*", 1.4], ["stone_*", 1.2],
  ["log_*", 1.4], ["stripped_*", 1.0], ["*planks*", 1.1], ["dirt*", 1.1], ["coarse_dirt", 1.2],
];
const DEFAULT_RELIEF = 1.0;
const CUTOUT_RELIEF = 0.7;
const TRANSLUCENT_RELIEF = 0.3;

const ENTITY_BLOCKS = [
  ["chest/*", 0.5], ["bed/*", 0.35], ["shulker/*", 0.4], ["bell/*", 0.35],
  ["skulls/*", 0.4], ["sign*", 0.5], ["*_sign", 0.5], ["enchanting_table_book", 0.3],
];
const NORMAL_SLOPE = 3.0;
const INVERTED = new Set(["brick"]);

const EMISSION_TARGET = [
  ["glowstone", 170], ["sea_lantern", 160], ["shroomlight", 150], ["*froglight*", 150],
  ["magma", 110], ["crying_obsidian", 120], ["redstone_block", 70], ["sea_pickle", 140],
  ["glow_lichen", 120], ["cave_vines_*berries", 170], ["end_rod", 180], ["beacon", 190],
  ["respawn_anchor_*", 150], ["sculk*", 60], ["*copper_bulb_lit*", 200],
];

// key -> [host texture, emission, gem]
const GLOWING_ORES = {
  "diamond_ore": ["stone", 80, true], "emerald_ore": ["stone", 80, true],
  "lapis_ore": ["stone", 60, true], "redstone_ore": ["stone", 110, false],
  "gold_ore": ["stone", 55, false], "iron_ore": ["stone", 40, false],
  "copper_ore": ["stone", 40, false],
  "deepslate/deepslate_diamond_ore": ["deepslate/deepslate", 80, true],
  "deepslate/deepslate_emerald_ore": ["deepslate/deepslate", 80, true],
  "deepslate/deepslate_lapis_ore": ["deepslate/deepslate", 60, true],
  "deepslate/deepslate_redstone_ore": ["deepslate/deepslate", 110, false],
  "deepslate/deepslate_gold_ore": ["deepslate/deepslate", 55, false],
  "deepslate/deepslate_iron_ore": ["deepslate/deepslate", 40, false],
  "deepslate/deepslate_copper_ore": ["deepslate/deepslate", 40, false],
  "nether_gold_ore": ["netherrack", 60, false], "quartz_ore": ["netherrack", 45, true],
  "gilded_blackstone": ["blackstone", 50, false],
};
const ORE_RAISE = 0.18;

const SMOOTHER = [
  ["ice", 0.3], ["ice_packed", 0.35], ["blue_ice", 0.3],
  ["iron_block", 0.55], ["gold_block", 0.55], ["netherite_block", 0.6], ["copper_block", 0.75],
  ["cut_copper", 0.75], ["diamond_block", 0.5], ["emerald_block", 0.5], ["lapis_block", 0.7],
  ["obsidian", 0.55], ["crying_obsidian", 0.6], ["glazed_terracotta_*", 0.6],
  ["polished_*", 0.8], ["*smooth*", 0.85], ["quartz_block*", 0.8], ["amethyst_block", 0.7],
  ["bell/*", 0.5], ["chest/copper_*", 0.8],
];
const CREVICE_ROUGHNESS = 70;
const RELIEF_GAIN = 1.4;
const LIT_THROUGH = [
  ["glass_black", 0], ["glass_pane_top_black", 0], ["glass_pane_top", 0], ["glass_*", 0.75],
];
const FLAT_STEP = 0.004;

// The main pack's own texture sets (its water): never overridden.
const MAIN_PACK_OWN = new Set(["water_flow_grey", "water_still_grey"]);

const IMAGE_EXTS = [".tga", ".png", ".jpg", ".jpeg"];     // the engine's priority order

// Fixed identifiers: rebuilding upgrades the installed add-on in place, and it
// is the same pack tools/build_pbr.py makes.
export const PACK = {
  headerUuid: "5a1f3c2e-8d47-4b6a-9e21-7c0b4d9f6a13",
  moduleUuid: "b2e87d45-1c9a-4f36-8a5d-3e6f0c7b9d28",
  version: [2, 0],
  name: "VYSE-Vibrant Visuals PBR",
  description: "Add-on for VYSE-Vibrant Visuals: relief on nearly every block, glowing light "
    + "blocks and ores, glossy ice, metal and polished stone, mobs wet and glossy in "
    + "rain. Built from the vanilla textures - for personal use only.",
  minEngine: [1, 21, 120],
};

// ------------------------------------------------------------------ helpers

const patternCache = new Map();
// fnmatch.fnmatchcase: * matches anything (slashes too), ? one character.
function fnmatch(name, pattern) {
  let re = patternCache.get(pattern);
  if (!re) {
    re = new RegExp("^" + pattern.replace(/[.+^${}()|\\]/g, "\\$&")
      .replace(/\*/g, ".*").replace(/\?/g, ".") + "$", "s");
    patternCache.set(pattern, re);
  }
  return re.test(name);
}

// First value whose pattern matches (a list of [pattern, value] pairs).
function match(name, table) {
  for (const [pattern, value] of table) if (fnmatch(name, pattern)) return value;
  return null;
}

// numpy's round: half to even.
function roundHalfEven(x) {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}
const clip = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
const W = [0.2126, 0.7152, 0.0722];

const decoder = new TextDecoder();
function parseJson(bytes, { comments = false } = {}) {
  let text = decoder.decode(bytes).replace(/^﻿/, "");
  if (comments) text = text.replace(/^\s*\/\/.*$/gm, "");
  return JSON.parse(text);
}
const json = (obj) => new TextEncoder().encode(JSON.stringify(obj, null, 2) + "\n");

const dirname = (p) => (p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "");
const basename = (p) => p.slice(p.lastIndexOf("/") + 1);
const join = (dir, name) => (dir ? `${dir}/${name}` : name);

// ------------------------------------------------------------- Pillow blur
// ImageFilter.GaussianBlur(0.6) on an 8-bit image, exactly as Pillow computes
// it: three passes of an extended box blur each way (BoxBlur.c), in C float
// and 32-bit integer arithmetic.

const f32 = Math.fround;

function gaussianBlurRadius(radius, passes) {
  const sigma2 = f32(f32(radius * radius) / passes);
  const L = f32(Math.sqrt(12.0 * sigma2 + 1.0));
  const l = f32(Math.floor((L - 1.0) / 2.0));
  let a = f32((2 * l + 1) * (l * (l + 1) - 3 * sigma2));
  a = f32(a / (6 * (sigma2 - (l + 1) * (l + 1))));
  return f32(l + a);
}

function boxBlurLine(out, line, lastx, radius, edgeA, edgeB, ww, fw) {
  const U = 4294967296;
  let acc = line[0] * (radius + 1);
  for (let x = 0; x < edgeA - 1; x++) acc += line[x];
  acc += line[lastx] * (radius - edgeA + 1);
  const save = (x, bulk) => { out[x] = Math.floor(((bulk % U) + (1 << 23)) % U / 16777216) & 0xff; };
  const step = (x, sub, add, left, right) => {
    acc += line[add] - line[sub];
    save(x, acc * ww + (line[left] + line[right]) * fw);
  };
  if (edgeA <= edgeB) {
    for (let x = 0; x < edgeA; x++) step(x, 0, x + radius, 0, x + radius + 1);
    for (let x = edgeA; x < edgeB; x++) step(x, x - radius - 1, x + radius, x - radius - 1, x + radius + 1);
    for (let x = edgeB; x <= lastx; x++) step(x, x - radius - 1, lastx, x - radius - 1, lastx);
  } else {
    for (let x = 0; x < edgeB; x++) step(x, 0, x + radius, 0, x + radius + 1);
    for (let x = edgeB; x < edgeA; x++) step(x, 0, lastx, 0, lastx);
    for (let x = edgeA; x <= lastx; x++) step(x, x - radius - 1, lastx, x - radius - 1, lastx);
  }
}

function horizontalBoxBlur(img, w, h, floatRadius) {
  const radius = Math.trunc(floatRadius);
  const ww = Math.trunc(f32(16777216 / f32(f32(floatRadius * 2) + 1)));
  const fw = Math.floor((16777216 - (radius * 2 + 1) * ww) / 2);
  const edgeA = Math.min(radius + 1, w), edgeB = Math.max(w - radius - 1, 0);
  const line = new Uint8Array(w), out = new Uint8Array(w);
  for (let y = 0; y < h; y++) {
    line.set(img.subarray(y * w, (y + 1) * w));
    boxBlurLine(out, line, w - 1, radius, edgeA, edgeB, ww, fw);
    img.set(out, y * w);
  }
}

function transpose(img, w, h) {
  const t = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) t[x * h + y] = img[y * w + x];
  return t;
}

export function pillowGaussianBlur(gray, w, h, radius = 0.6, passes = 3) {
  const r = gaussianBlurRadius(radius, passes);
  let img = Uint8Array.from(gray);
  if (r !== 0) {
    for (let i = 0; i < passes; i++) horizontalBoxBlur(img, w, h, r);
    let t = transpose(img, w, h);
    for (let i = 0; i < passes; i++) horizontalBoxBlur(t, h, w, r);
    img = transpose(t, h, w);
  }
  return img;
}

// ------------------------------------------------------------- the maps

function luminanceOf(data, i) {
  return (data[i] / 255) * W[0] + (data[i + 1] / 255) * W[1] + (data[i + 2] / 255) * W[2];
}

// Luminance with a touch of blur, and the opacity mask (alpha > 0.5).
function smoothedLuminance(img) {
  const n = img.width * img.height;
  const lum = new Float64Array(n), opaque = new Uint8Array(n), q = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    lum[i] = luminanceOf(img.data, i * 4);
    opaque[i] = img.data[i * 4 + 3] / 255 > 0.5 ? 1 : 0;
    q[i] = roundHalfEven(lum[i] * 255);
  }
  const blurred = pillowGaussianBlur(q, img.width, img.height);
  for (let i = 0; i < n; i++) lum[i] = 0.6 * lum[i] + 0.4 * (blurred[i] / 255);
  return [lum, opaque];
}

// Row ranges [start, end) of the frames of a vertical flipbook strip.
function frames(rows, cols) {
  if (rows > cols && rows % cols === 0) {
    const out = [];
    for (let r = 0; r < rows; r += cols) out.push([r, r + cols]);
    return out;
  }
  return [[0, rows]];
}

// numpy's mean (pairwise summation), so the result matches to the last bit.
function pairwiseSum(a, lo, hi) {
  const n = hi - lo;
  if (n < 8) { let s = 0; for (let i = lo; i < hi; i++) s += a[i]; return s; }
  if (n <= 128) {
    const r = [a[lo], a[lo + 1], a[lo + 2], a[lo + 3], a[lo + 4], a[lo + 5], a[lo + 6], a[lo + 7]];
    let i = lo + 8;
    for (; i < lo + n - (n % 8); i += 8) for (let k = 0; k < 8; k++) r[k] += a[i + k];
    let s = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]));
    for (; i < hi; i++) s += a[i];
    return s;
  }
  let half = Math.floor(n / 2);
  half -= half % 8;
  return pairwiseSum(a, lo, lo + half) + pairwiseSum(a, lo + half, hi);
}

function heightMap(img, strength, invert, raiseMask) {
  const [lum, opaque] = smoothedLuminance(img);
  const w = img.width;
  const height = new Float64Array(lum.length).fill(0.5);
  for (const [r0, r1] of frames(img.height, w)) {
    const seen = [];
    for (let i = r0 * w; i < r1 * w; i++) if (opaque[i]) seen.push(lum[i]);
    if (!seen.length) continue;
    const mean = pairwiseSum(seen, 0, seen.length) / seen.length;
    for (let i = r0 * w; i < r1 * w; i++) {
      const relief = strength * (lum[i] - mean);
      height[i] = opaque[i] ? 0.5 + (invert ? -relief : relief) : 0.5;
    }
  }
  for (let i = 0; i < height.length; i++) {
    if (raiseMask) height[i] += ORE_RAISE * raiseMask[i];
    height[i] = clip(height[i], 0.1, 0.9);
  }
  return [height, opaque];
}

// np.gradient along one axis: central differences inside, one-sided at the ends.
function gradient(h, w, rows, axis) {
  const g = new Float64Array(h.length);
  const n = axis === 0 ? rows : w;
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x, k = axis === 0 ? y : x, s = axis === 0 ? w : 1;
      if (n < 2) g[i] = 0;
      else if (k === 0) g[i] = h[i + s] - h[i];
      else if (k === n - 1) g[i] = h[i] - h[i - s];
      else g[i] = (h[i + s] - h[i - s]) / 2;
    }
  }
  return g;
}

// RGB normal map for an entity texture (DirectX convention, like vanilla's).
function normalMap(img, strength) {
  const [lum, opaque] = smoothedLuminance(img);
  const w = img.width, rows = img.height, n = lum.length;
  const k = strength * NORMAL_SLOPE;
  const h = new Float64Array(n);
  for (let i = 0; i < n; i++) h[i] = k * lum[i];
  const gy = gradient(h, w, rows, 0), gx = gradient(h, w, rows, 1);
  const out = new Uint8Array(n * 3);
  const at = (y, x) => opaque[((y + rows) % rows) * w + ((x + w) % w)];   // np.roll wraps
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const bothX = opaque[i] && at(y, x - 1) && at(y, x + 1);
      const bothY = opaque[i] && at(y - 1, x) && at(y + 1, x);
      const nx = -(bothX ? gx[i] : 0), ny = -(bothY ? gy[i] : 0), nz = 1;
      const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
      out[i * 3] = roundHalfEven(((nx / len) * 0.5 + 0.5) * 255);
      out[i * 3 + 1] = roundHalfEven(((ny / len) * 0.5 + 0.5) * 255);
      out[i * 3 + 2] = roundHalfEven(((nz / len) * 0.5 + 0.5) * 255);
    }
  }
  return out;
}

// True if no visible pixel's height differs from its neighbour's by more than FLAT_STEP.
function isFlat(height, opaque, w, rows) {
  const limit = FLAT_STEP * RELIEF_GAIN;
  for (const [r0, r1] of frames(rows, w)) {
    for (let y = r0; y < r1; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (y + 1 < r1 && opaque[i] && opaque[i + w] && Math.abs(height[i + w] - height[i]) > limit) return false;
        if (x + 1 < w && opaque[i] && opaque[i + 1] && Math.abs(height[i + 1] - height[i]) > limit) return false;
      }
    }
  }
  return true;
}

// 0..1 per pixel: how clearly the pixel is ore mineral, not host stone.
function mineralMask(ore, host) {
  const n = ore.width * ore.height;
  const out = new Float64Array(n);
  if (ore.width !== host.width || ore.height !== host.height) return out;
  for (let i = 0; i < n; i++) {
    const a = [ore.data[i * 4] / 255, ore.data[i * 4 + 1] / 255, ore.data[i * 4 + 2] / 255];
    const b = [host.data[i * 4] / 255, host.data[i * 4 + 1] / 255, host.data[i * 4 + 2] / 255];
    const diff = Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]);
    const differs = clip((diff - 0.12) / 0.2, 0, 1);
    const mx = Math.max(...a), mn = Math.min(...a);
    const saturation = (mx - mn) / Math.max(mx, 1e-6);
    const brighter = (a[0] * W[0] + a[1] * W[1] + a[2] * W[2]) - (b[0] * W[0] + b[1] * W[1] + b[2] * W[2]);
    const distinct = clip(Math.max((saturation - 0.25) / 0.25, brighter / 0.15), 0, 1);
    out[i] = differs * distinct;
  }
  return out;
}

function reliefStrength(key, img) {
  const s = match(key, RELIEF_BY_MATERIAL);
  if (s !== null) return s;
  const n = img.width * img.height;
  let partial = 0, cut = false;
  for (let i = 0; i < n; i++) {
    const a = img.data[i * 4 + 3];
    if (a > 10 && a < 245) partial++;
    if (a < 128) cut = true;
  }
  if (partial / n > 0.05) return TRANSLUCENT_RELIEF;
  if (cut) return CUTOUT_RELIEF;
  return DEFAULT_RELIEF;
}

// --------------------------------------------------------------- build

function findImage(files, base) {
  for (const ext of IMAGE_EXTS) if (files.has(base + ext)) return base + ext;
  return null;
}

async function pool(items, limit, fn) {
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      await fn(items[i], i);
    }
  });
  await Promise.all(workers);
}

/**
 * Builds the PBR add-on from a vanilla resource pack.
 *
 *   source       { files: Set<string>, read(path) } - see sources.js
 *   options.patch      third number of the pack version (default 0). Bedrock
 *                      will not re-import a pack whose version it already has.
 *   options.icon       pack_icon.png bytes (optional)
 *   options.concurrency  files processed at once (default 16)
 *   options.onProgress({ stage, done, total })
 *
 * Returns { files: Map<path, Uint8Array>, stats }.
 */
export async function buildPbr(source, options = {}) {
  const { patch = 0, icon = null, concurrency = 16, onProgress = () => {} } = options;
  const files = source.files;
  const out = new Map();
  const counts = { relief: 0, entityRelief: 0, glow: 0, glowingOres: 0, shine: 0, lightThrough: 0 };
  const skipped = {};
  const skip = (reason) => { skipped[reason] = (skipped[reason] || 0) + 1; };

  const imageCache = new Map();
  const loadImage = (path) => {
    if (!imageCache.has(path)) {
      imageCache.set(path, source.read(path).then((b) => decodeImage(path, b)));
    }
    return imageCache.get(path);
  };

  const BLOCKS = "textures/blocks", ENTITIES = "textures/entity";
  const all = [...files].sort();
  const jobs = [];
  for (const p of all) {
    if (!p.endsWith(".texture_set.json")) continue;
    if (p.startsWith(BLOCKS + "/")) jobs.push([p, BLOCKS, "block"]);
  }
  for (const p of all) {
    if (!p.endsWith(".texture_set.json") || !p.startsWith(ENTITIES + "/")) continue;
    const key = p.slice(ENTITIES.length + 1).replace(/\.texture_set\.json$/, "");
    if (match(key, ENTITY_BLOCKS) !== null) jobs.push([p, ENTITIES, "entity"]);
  }

  let done = 0;
  await pool(jobs, concurrency, async ([tsPath, root, kind]) => {
    try {
      await buildOne(tsPath, root, kind);
    } finally {
      onProgress({ stage: "textures", done: ++done, total: jobs.length });
    }
  });

  async function buildOne(tsPath, root, kind) {
    const textureSet = parseJson(await source.read(tsPath))["minecraft:texture_set"];
    const folder = dirname(tsPath);
    const name = textureSet.color;
    if (typeof name !== "string") return skip("uniform colour");
    if (kind === "block" && MAIN_PACK_OWN.has(name)) return skip("the main pack's own texture set");
    const colorPath = findImage(files, join(folder, name));
    const mersName = textureSet.metalness_emissive_roughness_subsurface;
    const mersPath = typeof mersName === "string" ? findImage(files, join(folder, mersName)) : null;
    if (!colorPath) return skip("colour image missing");
    const key = join(folder.slice(root.length + 1), name);      // e.g. deepslate/deepslate_iron_ore
    const color = await loadImage(colorPath);
    const npx = color.width * color.height;

    let mers = null;
    if (mersPath) {
      try {
        const m = await loadImage(mersPath);
        mers = { width: m.width, height: m.height, data: Float64Array.from(m.data) };
      } catch {
        skip("MERS image unreadable: copied unchanged");
      }
    }
    const mersOrig = mers ? Float64Array.from(mers.data) : null;
    const sameSize = mers && mers.width === color.width && mers.height === color.height;

    // Relief
    let height = null, normal = null;
    const hasBump = "normal" in textureSet || "heightmap" in textureSet;
    const ore = kind === "block" ? GLOWING_ORES[key] : undefined;
    let minerals = null;
    if (ore) {
      const hostPath = findImage(files, join(BLOCKS, ore[0]));
      if (hostPath) minerals = mineralMask(color, await loadImage(hostPath));
    }
    if (kind === "entity" && !hasBump) {
      normal = normalMap(color, match(key, ENTITY_BLOCKS));
    } else if (!hasBump) {
      const strength = reliefStrength(key, color);
      if (strength > 0) {
        const [h, opaque] = heightMap(color, strength * RELIEF_GAIN, INVERTED.has(name), minerals);
        if (isFlat(h, opaque, color.width, color.height)) {
          skip("no relief: flat texture (concrete...) - avoids seam lines");
        } else {
          height = h;
          if (sameSize) {
            for (let i = 0; i < npx; i++) {
              mers.data[i * 4 + 2] += CREVICE_ROUGHNESS * clip(0.5 - height[i], 0.0, 0.4) / 0.4;
            }
          }
        }
      } else skip("no relief: not a surface (fire, portals, liquids)");
    } else skip("no relief: vanilla already has bump data");

    if (mers) {
      const mn = mers.width * mers.height, d = mers.data;
      const target = match(key, EMISSION_TARGET);
      let peak = -Infinity;
      for (let i = 0; i < mn; i++) peak = Math.max(peak, d[i * 4 + 1]);
      if (target && peak > 0 && peak < target) {
        for (let i = 0; i < mn; i++) d[i * 4 + 1] *= target / peak;
        counts.glow++;
      }
      if (ore && minerals && minerals.length === mn) {
        const [, glow, gem] = ore;
        for (let i = 0; i < mn; i++) {
          d[i * 4 + 1] = Math.max(d[i * 4 + 1], glow * minerals[i]);
          if (gem) d[i * 4 + 2] = d[i * 4 + 2] * (1 - 0.6 * minerals[i]);
        }
        counts.glowingOres++;
      }
      const factor = match(key, SMOOTHER);
      if (factor) {
        for (let i = 0; i < mn; i++) d[i * 4 + 2] *= factor;
        counts.shine++;
      }
      const through = match(key, LIT_THROUGH);
      if (through) {
        for (let i = 0; i < mn; i++) d[i * 4 + 3] = Math.max(d[i * 4 + 3], 255 * through);
        counts.lightThrough++;
      }
    }

    let changedMers = false;
    let mers8 = null;
    if (mers) {
      mers8 = new Uint8Array(mers.data.length);
      for (let i = 0; i < mers.data.length; i++) {
        mers8[i] = roundHalfEven(clip(mers.data[i], 0, 255));
        if (mers8[i] !== mersOrig[i]) changedMers = true;
      }
    }
    if (!height && !normal && !changedMers) return;

    // The colour image is copied byte for byte.
    out.set(colorPath, await source.read(colorPath));
    const newSet = { color: name };
    if (changedMers) {
      // A name of our own, so the engine never picks vanilla's image instead.
      newSet.metalness_emissive_roughness_subsurface = `${name}_vu_mers`;
      out.set(join(folder, `${name}_vu_mers.png`), await encodePNG(mers.width, mers.height, mers8, 4));
    } else if (mersPath) {
      newSet.metalness_emissive_roughness_subsurface = mersName;
      out.set(mersPath, await source.read(mersPath));
    }
    if ("normal" in textureSet) {
      const normalPath = typeof textureSet.normal === "string"
        ? findImage(files, join(folder, textureSet.normal)) : null;
      if (normalPath) {
        out.set(normalPath, await source.read(normalPath));
        newSet.normal = textureSet.normal;
      }
    }
    if (height) {
      newSet.heightmap = `${name}_height`;
      const h8 = new Uint8Array(npx);
      for (let i = 0; i < npx; i++) h8[i] = roundHalfEven(height[i] * 255);
      out.set(join(folder, `${name}_height.png`), await encodePNG(color.width, color.height, h8, 1));
      counts.relief++;
    }
    if (normal) {
      newSet.normal = `${name}_vu_normal`;
      out.set(join(folder, `${name}_vu_normal.png`), await encodePNG(color.width, color.height, normal, 3));
      counts.entityRelief++;
    }
    out.set(tsPath, json({ format_version: "1.21.30", "minecraft:texture_set": newSet }));
  }

  // Wet entities
  let wet = null;
  if ([...files].some((p) => p.startsWith("entity/")) && [...files].some((p) => p.startsWith("render_controllers/"))) {
    wet = await buildWet(source, out, { concurrency, onProgress, loadImage });
  } else skip("no entity/ or render_controllers/: wet entities skipped");

  const version = [...PACK.version, patch];
  out.set("manifest.json", json({
    format_version: 2,
    header: {
      name: PACK.name, description: PACK.description, uuid: PACK.headerUuid,
      version, min_engine_version: PACK.minEngine,
    },
    modules: [{ type: "resources", description: PACK.description, uuid: PACK.moduleUuid, version }],
    capabilities: ["pbr"],
  }));
  if (icon) out.set("pack_icon.png", icon);

  return { files: out, version, stats: { ...counts, wet, skipped } };
}

// --------------------------------------------------------------- wet entities
// Port of tools/wet_entities.py: mobs, boats, minecarts... turn darker and
// glossy while query.is_in_water_or_rain, through copies of their render
// controllers that pick _wet textures.

const WET_DARKEN = 0.88;
const WET_ROUGHNESS = 0.45;
const DRY_DEFAULT_MERS = [0, 0, 190, 0];
const WET_SKIP = new Set(["minecraft:player"]);
const SUFFIX = "_wet";
const CONTROLLER_SUFFIX = ".vyse_wet";
const WET = "query.is_in_water_or_rain";
const REF = /\b(texture|array)\.([A-Za-z0-9_]+)/gi;

const hasRef = (s) => new RegExp(REF.source, "i").test(s);
const wetExpression = (expr) => expr.replace(REF, (_, kind, name) => `${kind}.${name}${SUFFIX}`);
function textureRefs(expr) {
  const refs = new Set();
  for (const m of expr.matchAll(REF)) if (m[1].toLowerCase() === "texture") refs.add(m[2].toLowerCase());
  return refs;
}

function wetController(ctrl) {
  const textures = ctrl.textures;
  if (!Array.isArray(textures) || !textures.some((t) => typeof t === "string" && hasRef(t))) return null;
  const copy = structuredClone(ctrl);
  copy.textures = textures.map((t) => (typeof t === "string" && hasRef(t)
    ? `${WET} ? (${wetExpression(t)}) : (${t})` : t));
  const arrays = copy.arrays?.textures;
  if (arrays && typeof arrays === "object" && !Array.isArray(arrays)) {
    for (const [name, entries] of Object.entries({ ...arrays })) {
      arrays[name + SUFFIX] = entries.map((e) => (typeof e === "string" ? wetExpression(e) : e));
    }
  }
  return copy;
}

function requiredTextures(ctrl) {
  const refs = new Set();
  for (const t of ctrl.textures || []) if (typeof t === "string") textureRefs(t).forEach((r) => refs.add(r));
  for (const entries of Object.values(ctrl.arrays?.textures || {})) {
    for (const e of entries) if (typeof e === "string") textureRefs(e).forEach((r) => refs.add(r));
  }
  return refs;
}

// Python's round(): half to even, like numpy's.
function scaleRoughness(value, factor) {
  let vals;
  if (typeof value === "string") {
    const v = value.replace(/^#/, "");
    vals = [];
    for (let i = 0; i < v.length; i += 2) vals.push(parseInt(v.slice(i, i + 2), 16));
  } else vals = [...value];
  if (vals.length >= 3) vals[2] = roundHalfEven(vals[2] * factor);
  return vals;
}

async function buildWet(source, out, { concurrency, onProgress, loadImage }) {
  const files = source.files;
  const controllers = new Map();
  for (const p of [...files].filter((f) => /^render_controllers\/[^/]+\.json$/.test(f)).sort()) {
    const doc = parseJson(await source.read(p), { comments: true });
    for (const [name, ctrl] of Object.entries(doc.render_controllers || {})) {
      controllers.set(name, [ctrl, doc.format_version || "1.8.0"]);
    }
  }

  const made = new Map();          // texture path -> Promise<boolean>
  const makeWet = (path) => {
    if (!made.has(path)) made.set(path, makeWetTexture(path));
    return made.get(path);
  };

  async function makeWetTexture(path) {
    const src = findImage(files, path);
    if (!src) return false;
    const name = basename(path), dir = dirname(path);
    const wetName = name + SUFFIX;
    const ext = src.slice(src.lastIndexOf("."));

    const img = await loadImage(src);
    const rgba = Uint8Array.from(img.data);
    for (let i = 0; i < rgba.length; i += 4) {
      for (let c = 0; c < 3; c++) rgba[i + c] = roundHalfEven(img.data[i + c] * WET_DARKEN);
    }
    out.set(join(dir, wetName + ext), ext === ".tga"
      ? encodeTGA(img.width, img.height, rgba)
      : await encodePNG(img.width, img.height, rgba, 4));

    const newSet = { color: wetName };
    const tsPath = join(dirname(src), name + ".texture_set.json");
    const dry = files.has(tsPath)
      ? (parseJson(await source.read(tsPath), { comments: true })["minecraft:texture_set"] || {}) : null;
    let mersKey = null;
    if (dry) {
      mersKey = ["metalness_emissive_roughness_subsurface", "metalness_emissive_roughness"]
        .find((k) => k in dry) || null;
    }
    if (dry && mersKey) {
      const value = dry[mersKey];
      if (typeof value === "string" && !value.startsWith("#")) {
        const mersSrc = findImage(files, join(dirname(src), value));
        if (mersSrc) {
          let m = await loadImage(mersSrc);
          if (m.width !== img.width || m.height !== img.height) m = resizeNearest(m, img.width, img.height);
          const d = new Float64Array(m.data);
          const res = new Uint8Array(d.length);
          for (let i = 0; i < d.length; i += 4) {
            if (mersKey === "metalness_emissive_roughness") d[i + 3] = 0;
            d[i + 2] *= WET_ROUGHNESS;
            for (let c = 0; c < 4; c++) res[i + c] = roundHalfEven(d[i + c]);
          }
          out.set(join(dir, `${wetName}_mers.png`), await encodePNG(img.width, img.height, res, 4));
          newSet.metalness_emissive_roughness_subsurface = `${wetName}_mers`;
        }
      } else {
        newSet[mersKey] = scaleRoughness(value, WET_ROUGHNESS);
      }
      for (const key of ["normal", "heightmap"]) {
        const ref = dry[key];
        if (typeof ref === "string" && !ref.startsWith("#")) {
          const refPath = findImage(files, join(dirname(src), ref));
          if (refPath) {
            const target = join(dir, basename(refPath));
            if (!out.has(target)) out.set(target, await source.read(refPath));
            newSet[key] = ref;
          }
        }
      }
    }
    if (!("metalness_emissive_roughness_subsurface" in newSet) && !("metalness_emissive_roughness" in newSet)) {
      newSet.metalness_emissive_roughness_subsurface = scaleRoughness(DRY_DEFAULT_MERS, WET_ROUGHNESS);
    }
    out.set(join(dir, `${wetName}.texture_set.json`),
      json({ format_version: "1.21.30", "minecraft:texture_set": newSet }));
    return true;
  }

  const wetCtrls = new Map();
  const counts = { entities: 0, controllers: 0, textures: 0, skipped: 0 };
  const entityFiles = [...files].filter((f) => /^entity\/[^/]+\.json$/.test(f)).sort();
  let done = 0;

  // First pass (in order, as the Python does): decide each entity's controllers.
  const plans = [];
  for (const p of entityFiles) {
    const doc = parseJson(await source.read(p), { comments: true });
    const desc = doc["minecraft:client_entity"]?.description || {};
    const texMap = desc.textures;
    if (WET_SKIP.has(desc.identifier) || !texMap || typeof texMap !== "object" || !Object.keys(texMap).length) {
      counts.skipped++;
      continue;
    }
    const newRcs = [];
    let changed = false;
    for (const entry of desc.render_controllers || []) {
      const name = typeof entry === "string" ? entry : Object.keys(entry)[0];
      const found = controllers.get(name);
      const wet = found ? wetController(found[0]) : null;
      if (!wet) { newRcs.push(entry); continue; }
      if (!wetCtrls.has(name + CONTROLLER_SUFFIX)) wetCtrls.set(name + CONTROLLER_SUFFIX, [wet, found[1]]);
      newRcs.push(typeof entry === "string" ? name + CONTROLLER_SUFFIX : { [name + CONTROLLER_SUFFIX]: entry[name] });
      changed = true;
    }
    if (!changed) { counts.skipped++; continue; }
    plans.push({ p, doc, texMap, newRcs });
  }

  // Second pass: the wet textures, in parallel.
  await pool(plans, concurrency, async (plan) => {
    const newTex = { ...plan.texMap };
    for (const [key, path] of Object.entries(plan.texMap)) {
      if (typeof path !== "string") continue;
      newTex[key + SUFFIX] = (await makeWet(path)) ? path + SUFFIX : path;
    }
    for (const entry of plan.newRcs) {
      const name = typeof entry === "string" ? entry : Object.keys(entry)[0];
      if (!wetCtrls.has(name)) continue;
      const have = new Set(Object.keys(newTex).map((k) => k.toLowerCase()));
      const dryKeys = [...requiredTextures(controllers.get(name.slice(0, -CONTROLLER_SUFFIX.length))[0])]
        .filter((r) => have.has(r));
      const missing = dryKeys.map((r) => r + SUFFIX).filter((r) => !have.has(r));
      if (missing.length) throw new Error(`${plan.p}: ${name} would miss ${missing.sort()}`);
    }
    const newDoc = structuredClone(plan.doc);
    const newDesc = newDoc["minecraft:client_entity"].description;
    newDesc.textures = newTex;
    newDesc.render_controllers = plan.newRcs;
    out.set(plan.p, json(newDoc));
    counts.entities++;
    onProgress({ stage: "wet entities", done: ++done, total: plans.length });
  });

  const byFormat = new Map();
  for (const [name, [ctrl, fmt]] of wetCtrls) {
    if (!byFormat.has(fmt)) byFormat.set(fmt, {});
    byFormat.get(fmt)[name] = ctrl;
  }
  for (const [fmt, ctrls] of byFormat) {
    out.set(`render_controllers/vyse_wet_${fmt.replaceAll(".", "_")}.render_controllers.json`,
      json({ format_version: fmt, render_controllers: ctrls }));
  }
  counts.controllers = wetCtrls.size;
  counts.textures = (await Promise.all(made.values())).filter(Boolean).length;
  return counts;
}

// Pillow's resize(..., NEAREST) (ImagingScaleAffine): the source position
// starts at half a step and is accumulated by repeated addition, then
// truncated - so where it lands exactly on a whole pixel the float sum can
// fall just short, and Pillow picks the pixel before. Reproduced as is.
function nearestTable(dst, src) {
  const a = src / dst, out = new Int32Array(dst);
  let xo = a * 0.5;
  for (let x = 0; x < dst; x++) {
    out[x] = Math.min(src - 1, Math.max(0, Math.trunc(xo)));
    xo += a;
  }
  return out;
}

function resizeNearest(img, w, h) {
  const data = new Uint8Array(w * h * 4);
  const xs = nearestTable(w, img.width), ys = nearestTable(h, img.height);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const s = (ys[y] * img.width + xs[x]) * 4;
      data.set(img.data.subarray(s, s + 4), (y * w + x) * 4);
    }
  }
  return { width: w, height: h, data };
}
