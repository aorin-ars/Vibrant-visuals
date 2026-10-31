// Where the vanilla files come from. A source is
//   { files: Set<string>, read(path): Promise<Uint8Array>, label: string }
// with paths relative to the vanilla resource_pack folder.

const REPO = "Mojang/bedrock-samples";
const API = `https://api.github.com/repos/${REPO}`;

// Only these are ever read; listing everything else would only cost time.
const WANTED = /^(textures\/|entity\/[^/]+\.json$|render_controllers\/[^/]+\.json$)/;

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (res.status === 403 || res.status === 429) {
    throw new Error("GitHub の API 制限に達しました。1 時間ほど待ってからもう一度試してください "
      + "(GitHub API rate limit reached; try again in an hour).");
  }
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

async function fetchWithRetry(url, tries = 4) {
  for (let i = 0; ; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return new Uint8Array(await res.arrayBuffer());
      if (res.status === 404 || i >= tries - 1) throw new Error(`${url}: HTTP ${res.status}`);
    } catch (e) {
      if (i >= tries - 1) throw e;
    }
    await new Promise((r) => setTimeout(r, 500 * 2 ** i));
  }
}

// The latest release tag of Mojang/bedrock-samples (e.g. "v1.26.60.5"):
// the files of the current, non-preview game.
export async function latestVanillaTag() {
  return (await getJson(`${API}/releases/latest`)).tag_name;
}

/**
 * Mojang's own vanilla resource pack, read straight from GitHub on the
 * player's device. Three API calls list the files (the unauthenticated limit
 * is 60 an hour); the files come from raw.githubusercontent.com, which
 * allows cross-origin reads. About 7,000 files and 50 MB are read.
 *
 *   tag       a release tag of Mojang/bedrock-samples; default: the latest release
 *   fileList  optional: the paths under resource_pack/ at that tag (an array
 *             of strings, e.g. a JSON file the site hosts - just names, no
 *             Mojang content). Given with `tag`, no GitHub API call is made.
 */
export async function githubSource({ tag, fileList } = {}) {
  let files;
  if (fileList) {
    if (!tag) throw new Error("githubSource: a fileList needs its tag");
    files = new Set(fileList.filter((p) => WANTED.test(p)));
  } else {
    tag = tag || await latestVanillaTag();
    const root = await getJson(`${API}/contents?ref=${encodeURIComponent(tag)}`);
    const rp = root.find((e) => e.name === "resource_pack" && e.type === "dir");
    if (!rp) throw new Error(`${REPO}@${tag} has no resource_pack folder`);
    const tree = await getJson(`${API}/git/trees/${rp.sha}?recursive=1`);
    if (tree.truncated) throw new Error("GitHub returned a truncated file list");
    files = new Set(tree.tree.filter((e) => e.type === "blob" && WANTED.test(e.path)).map((e) => e.path));
  }

  const base = `https://raw.githubusercontent.com/${REPO}/${encodeURIComponent(tag)}/resource_pack/`;
  const cache = new Map();
  return {
    label: `${REPO}@${tag}`,
    tag,
    files,
    read(path) {
      if (!cache.has(path)) {
        cache.set(path, fetchWithRetry(base + path.split("/").map(encodeURIComponent).join("/")));
      }
      return cache.get(path);
    },
  };
}

/**
 * A vanilla resource_pack folder the player picked on their own device, from
 * <input type="file" webkitdirectory> (a FileList or an array of File). The
 * folder may be resource_pack itself or anything containing it (a whole
 * bedrock-samples download).
 */
export function folderSource(fileList) {
  const byPath = new Map();
  let prefix = null;
  for (const f of fileList) {
    const p = (f.webkitRelativePath || f.name).replace(/\\/g, "/");
    if (prefix === null) {
      const i = p.indexOf("resource_pack/");
      if (i >= 0) prefix = p.slice(0, i + "resource_pack/".length);
    }
    byPath.set(p, f);
  }
  if (prefix === null) {
    // The folder picked is resource_pack itself: drop its own name.
    const first = byPath.keys().next().value || "";
    prefix = first.includes("/") ? first.slice(0, first.indexOf("/") + 1) : "";
  }
  const files = new Map();
  for (const [p, f] of byPath) {
    if (!p.startsWith(prefix)) continue;
    const rel = p.slice(prefix.length);
    if (WANTED.test(rel)) files.set(rel, f);
  }
  if (![...files.keys()].some((p) => p.startsWith("textures/blocks/"))) {
    throw new Error("このフォルダにはバニラのブロックテクスチャがありません "
      + "(no textures/blocks in the folder picked: choose the vanilla resource_pack folder).");
  }
  return {
    label: "local folder",
    files: new Set(files.keys()),
    async read(path) {
      const f = files.get(path);
      if (!f) throw new Error(`${path}: not in the folder`);
      return new Uint8Array(await f.arrayBuffer());
    },
  };
}
