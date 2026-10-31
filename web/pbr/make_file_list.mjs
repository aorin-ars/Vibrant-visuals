// Writes the list of file paths of a vanilla resource_pack, for
// githubSource({ tag, fileList }): with it the page makes no GitHub API call
// (whose unauthenticated limit is 60 an hour per visitor's IP). It holds
// only file names, none of Mojang's content.
//
//   node web/pbr/make_file_list.mjs --vanilla <bedrock-samples>/resource_pack --tag v1.26.60.5 > vanilla-files.json
//
// The tag must be the one the folder was checked out at.

import { readdir } from "node:fs/promises";
import { join, relative, sep } from "node:path";

const arg = (n) => { const i = process.argv.indexOf(n); return i >= 0 ? process.argv[i + 1] : undefined; };
const vanilla = arg("--vanilla"), tag = arg("--tag");
if (!vanilla || !tag) {
  console.error("usage: node web/pbr/make_file_list.mjs --vanilla <resource_pack> --tag <release tag>");
  process.exit(2);
}
const WANTED = /^(textures\/|entity\/[^/]+\.json$|render_controllers\/[^/]+\.json$)/;
const out = [];
async function walk(dir) {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) await walk(p);
    else {
      const rel = relative(vanilla, p).split(sep).join("/");
      if (WANTED.test(rel)) out.push(rel);
    }
  }
}
await walk(vanilla);
process.stdout.write(JSON.stringify({ tag, files: out.sort() }) + "\n");
