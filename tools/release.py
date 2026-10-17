#!/usr/bin/env python3
"""Put together the files to publish, in build/release/.

    tools/release.py [--vanilla <bedrock-samples>/resource_pack]

Builds the packs with tools/package.sh - never the PBR add-on, which holds
Mojang's textures and is for personal use only - and lays them out as

    build/release/VYSE-Vibrant-Visuals-v<ver>/
        VYSE-Vibrant-Visuals-v<ver>.mcaddon  the resource pack and the Weather
                                             Sync behavior pack, imported together
        VYSE-Vibrant-Visuals-v<ver>.mcpack   the resource pack alone
        VYSE-Weather-Sync-v<ver>.mcpack      the behavior pack alone
        README.txt                           install notes (docs/release_readme.txt)
        LICENSE.txt
    build/release/VYSE-Vibrant-Visuals-v<ver>.zip   all of the above, to upload

The working tree must be clean, so a release is exactly one commit. With
--vanilla, every image shipped is also checked against the vanilla pack:
none may be a copy of Mojang's.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/release"
IMAGE_EXTS = (".png", ".tga", ".jpg", ".jpeg")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()


def manifest(pack: Path) -> dict:
    with zipfile.ZipFile(pack) as z:
        return json.loads(z.read("manifest.json"))


def version(m: dict) -> str:
    return ".".join(map(str, m["header"]["version"]))


def write_mcaddon(dest: Path, packs: dict[str, Path]) -> None:
    """A .mcaddon is a zip with one folder per pack, each with its manifest."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as out:
        for folder, pack in packs.items():
            with zipfile.ZipFile(pack) as z:
                for info in z.infolist():
                    if not info.is_dir():
                        out.writestr(f"{folder}/{info.filename}", z.read(info))


def shipped_images(archive, label: str):
    """(name, bytes) of every image in an archive, looking into nested packs."""
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.filename.lower().endswith(IMAGE_EXTS):
                yield f"{label}:{info.filename}", z.read(info)
            elif info.filename.endswith((".mcpack", ".mcaddon")):
                yield from shipped_images(io.BytesIO(z.read(info)), f"{label}:{info.filename}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vanilla", type=Path,
                        help="vanilla resource_pack, to check that no Mojang image is shipped")
    args = parser.parse_args()

    if git("status", "--porcelain"):
        print("the working tree has changes: commit them first, so the release is one commit")
        return 1
    subprocess.run(["bash", "tools/package.sh"], cwd=ROOT, check=True)

    describe = git("describe", "--tags", "--always", "--dirty")
    rp = ROOT / f"build/VYSE-Vibrant-Visuals-{describe}.mcpack"
    bp = ROOT / f"build/VYSE-Weather-Sync-{describe}.mcpack"
    rp_manifest, bp_manifest = manifest(rp), manifest(bp)
    ver = version(rp_manifest)
    if version(bp_manifest) != ver:
        print(f"version mismatch: resource pack {ver}, behavior pack {version(bp_manifest)}")
        return 1

    name = f"VYSE-Vibrant-Visuals-v{ver}"
    folder = OUT / name
    if OUT.exists():
        shutil.rmtree(OUT)
    folder.mkdir(parents=True)

    write_mcaddon(folder / f"{name}.mcaddon",
                  {"VYSE-Vibrant-Visuals": rp, "VYSE-Weather-Sync": bp})
    shutil.copy2(rp, folder / f"{name}.mcpack")
    shutil.copy2(bp, folder / f"VYSE-Weather-Sync-v{ver}.mcpack")
    readme = (ROOT / "docs/release_readme.txt").read_text(encoding="utf-8")
    (folder / "README.txt").write_text(readme.replace("{version}", ver), encoding="utf-8-sig")
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")

    archive = OUT / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.iterdir()):
            z.write(path, f"{name}/{path.name}")

    if args.vanilla:
        vanilla = {hashlib.sha256(p.read_bytes()).hexdigest(): p
                   for p in args.vanilla.rglob("*") if p.suffix.lower() in IMAGE_EXTS}
        copies = [(n, vanilla[h]) for n, d in shipped_images(archive, archive.name)
                  if (h := hashlib.sha256(d).hexdigest()) in vanilla]
        if copies:
            for shipped, original in copies:
                print(f"{shipped} is a copy of {original}")
            shutil.rmtree(OUT)
            return 1
        print(f"no image is a copy of one in {args.vanilla}")

    for path in sorted(folder.iterdir()):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1e6:.1f} MB")
    print(f"{archive.relative_to(ROOT)}  {archive.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
