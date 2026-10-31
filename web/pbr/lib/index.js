// Entry points for a web page (aorin.net) that builds the PBR add-on on the
// player's own device. See web/pbr/README.md for how to wire it up.

import { buildPbr, PACK } from "./pbr.js";
import { readZip, writeZip } from "./zip.js";

export { githubSource, folderSource, latestVanillaTag } from "./sources.js";
export { PACK };

// The pack's version must rise with every build, or Bedrock keeps the copy it
// already has and silently ignores the new one. Minutes since 2026-01-01:
// always above the patch numbers tools/package.sh stamps (commit counts).
export function defaultPatch(now = Date.now()) {
  return Math.floor((now - Date.UTC(2026, 0, 1)) / 60000);
}

/**
 * Builds VYSE-Vibrant Visuals PBR as a .mcpack.
 *
 *   source      githubSource() or folderSource(files)
 *   icon        pack_icon.png bytes (web/pbr/pbr_pack_icon.png), optional
 *   patch       version patch number, default defaultPatch()
 *   onProgress  ({ stage, done, total }) => void
 *                 stage: "textures" | "wet entities" | "zip"
 *
 * Returns { bytes: Uint8Array, filename, version, files, stats }.
 */
export async function buildPbrMcpack({ source, icon = null, patch = defaultPatch(), onProgress = () => {} }) {
  const { files, version, stats } = await buildPbr(source, { icon, patch, onProgress });
  const bytes = await writeZip(sortedEntries(files), {
    onProgress: (done, total) => onProgress({ stage: "zip", done, total }),
  });
  return { bytes, filename: `VYSE-Vibrant-Visuals-PBR-v${version.join(".")}.mcpack`, version, files, stats };
}

// Same identifiers as tools/release.py's Full pack, so either upgrades the other.
const FULL_HEADER_UUID = "0778aec2-50cb-4ff8-b389-143b67019688";
const FULL_MODULE_UUID = "6910e298-efd5-45ca-aada-01f1be698d98";

/**
 * The main pack (a VYSE-Vibrant-Visuals-*.mcpack, as published) and the PBR
 * add-on merged into one pack - the same merge as tools/release.py's
 * write_full_pack. The main pack's files win; its subpacks are kept.
 *
 *   mainPack   bytes of the main .mcpack
 *   pbrFiles   the `files` map returned by buildPbrMcpack
 *   patch      version patch number of the result, default defaultPatch()
 *
 * Returns { bytes, filename, version }.
 */
export async function buildFullMcpack({ mainPack, pbrFiles, patch = defaultPatch(), onProgress = () => {} }) {
  const main = await readZip(mainPack);
  const m = JSON.parse(new TextDecoder().decode(main.get("manifest.json")).replace(/^﻿/, ""));
  const pbrManifest = JSON.parse(new TextDecoder().decode(pbrFiles.get("manifest.json")));
  const header = m.header;
  header.name = "VYSE-Vibrant Visuals Full";
  header.description = "VYSE-Vibrant Visuals and its PBR add-on in one pack: the full look plus "
    + "block relief, glowing light blocks and ores, glossy ice and metal, mobs wet in rain. "
    + "Contains Mojang's block textures - for personal use only. Use it instead of the two "
    + "separate packs, not with them.";
  header.uuid = FULL_HEADER_UUID;
  header.version = [header.version[0], header.version[1], patch];
  header.min_engine_version = maxVersion(header.min_engine_version, pbrManifest.header.min_engine_version);
  const [module] = m.modules;
  module.description = header.description;
  module.uuid = FULL_MODULE_UUID;
  module.version = header.version;
  m.metadata = { ...(m.metadata || {}), license: "All rights reserved (personal use only; contains Mojang textures)" };

  const merged = new Map([["manifest.json", new TextEncoder().encode(JSON.stringify(m, null, 2) + "\n")]]);
  for (const [p, b] of main) if (!merged.has(p)) merged.set(p, b);
  for (const [p, b] of pbrFiles) if (!merged.has(p)) merged.set(p, b);
  const bytes = await writeZip(sortedEntries(merged), {
    onProgress: (done, total) => onProgress({ stage: "zip", done, total }),
  });
  return { bytes, filename: `VYSE-Vibrant-Visuals-Full-v${header.version.join(".")}.mcpack`, version: header.version };
}

function maxVersion(a, b) {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0) ? a : b;
  }
  return a;
}

function sortedEntries(map) {
  // manifest.json first, as Bedrock's own packs have it; the rest in path order.
  return [...map.entries()].sort(([a], [b]) =>
    (a === "manifest.json" ? -1 : b === "manifest.json" ? 1 : a < b ? -1 : a > b ? 1 : 0));
}
