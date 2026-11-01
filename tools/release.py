#!/usr/bin/env python3
"""Put together the files to publish, in build/release/.

    tools/release.py [--vanilla <bedrock-samples>/resource_pack]

Builds the packs with tools/package.sh and lays them out as

    build/release/VYSE-Vibrant-Visuals-v<ver>/
        VYSE-Vibrant-Visuals-v<ver>.mcaddon  the resource pack and the Weather
                                             Sync behavior pack, imported together
        VYSE-Vibrant-Visuals-v<ver>.mcpack   the resource pack alone
        VYSE-Weather-Sync-v<bp ver>.mcpack   the behavior pack alone
        README.txt                           install notes (docs/release_readme.txt)
        LICENSE.txt
    build/release/VYSE-Vibrant-Visuals-v<ver>.zip   all of the above, to upload
    build/release/distribution_page.md               text for the download page
                                                     (docs/distribution_page.md)

With --vanilla, every image in the zip is also checked against the vanilla
pack - none may be a copy of Mojang's - and the PBR add-on is built too, on
its own, outside the zip:

    build/release/personal_use_only/VYSE-Vibrant-Visuals-PBR-v<ver>.mcpack
    build/release/personal_use_only/VYSE-Vibrant-Visuals-Full-v<ver>.mcpack
                                         the main pack and the PBR add-on in one

They have to hold Mojang's block textures (a texture set may only use images
from its own pack), so it is for the owner's own use and never uploaded.

The working tree must be clean, so a release is exactly one commit.
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


# The combined pack (main pack + PBR add-on in one) has identifiers of its
# own, so the game never mistakes it for either of the separate packs and
# both can stay installed next to it. Fixed, so a rebuilt one upgrades in place.
FULL_HEADER_UUID = "0778aec2-50cb-4ff8-b389-143b67019688"
FULL_MODULE_UUID = "6910e298-efd5-45ca-aada-01f1be698d98"


def write_full_pack(dest: Path, rp: Path, pbr: Path) -> str:
    """The main pack and the PBR add-on merged into one pack, for one's own use.

    The two share no file but manifest.json and pack_icon.png: the add-on is
    block and entity texture sets, entity files and their images, the main
    pack light, sky, fog, clouds and water. Everything of the main pack is
    kept as it is (subpacks included); the add-on's files are added beside
    it. The manifest is the main pack's with its own name and identifiers and
    the higher of the two minimum game versions. Returns the version."""
    m = manifest(rp)
    pbr_m = manifest(pbr)
    header = m["header"]
    header["name"] = "VYSE-Vibrant Visuals Full"
    header["description"] = (
        "VYSE-Vibrant Visuals and its PBR add-on in one pack: the full look plus block relief, "
        "glowing light blocks and ores, glossy ice and metal, mobs wet in rain. Contains "
        "Mojang's block textures - for personal use only. Use it instead of the two separate "
        "packs, not with them.")
    header["uuid"] = FULL_HEADER_UUID
    header["min_engine_version"] = max(header["min_engine_version"],
                                       pbr_m["header"]["min_engine_version"])
    (module,) = m["modules"]
    module["description"] = header["description"]
    module["uuid"] = FULL_MODULE_UUID
    m["metadata"]["license"] = "All rights reserved (personal use only; contains Mojang textures)"

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr("manifest.json", json.dumps(m, indent=2, ensure_ascii=False) + "\n")
        written = {"manifest.json"}
        for pack in (rp, pbr):
            with zipfile.ZipFile(pack) as z:
                for info in z.infolist():
                    if info.is_dir() or info.filename in written:
                        continue
                    out.writestr(info.filename, z.read(info))
                    written.add(info.filename)
    return version(m)


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
    vanilla_args = ["--vanilla", str(args.vanilla)] if args.vanilla else []
    subprocess.run(["bash", "tools/package.sh", *vanilla_args], cwd=ROOT, check=True)

    describe = git("describe", "--tags", "--always", "--dirty")
    rp = ROOT / f"build/VYSE-Vibrant-Visuals-{describe}.mcpack"
    bp = ROOT / f"build/VYSE-Weather-Sync-{describe}.mcpack"
    # The release takes the resource pack's version; the behavior pack keeps
    # its own (both carry the same commit count as their patch number).
    ver, bp_ver = version(manifest(rp)), version(manifest(bp))

    name = f"VYSE-Vibrant-Visuals-v{ver}"
    folder = OUT / name
    if OUT.exists():
        shutil.rmtree(OUT)
    folder.mkdir(parents=True)

    write_mcaddon(folder / f"{name}.mcaddon",
                  {"VYSE-Vibrant-Visuals": rp, "VYSE-Weather-Sync": bp})
    shutil.copy2(rp, folder / f"{name}.mcpack")
    shutil.copy2(bp, folder / f"VYSE-Weather-Sync-v{bp_ver}.mcpack")
    readme = (ROOT / "docs/release_readme.txt").read_text(encoding="utf-8")
    readme = readme.replace("{version}", ver).replace("{bp_version}", bp_ver)
    (folder / "README.txt").write_text(readme, encoding="utf-8-sig")
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")
    page = (ROOT / "docs/distribution_page.md").read_text(encoding="utf-8")
    (OUT / "distribution_page.md").write_text(
        page.replace("{version}", ver).replace("{bp_version}", bp_ver), encoding="utf-8")

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

        pbr = ROOT / f"build/VYSE-Vibrant-Visuals-PBR-{describe}.mcpack"
        personal = OUT / "personal_use_only"
        personal.mkdir()
        shutil.copy2(pbr, personal / f"VYSE-Vibrant-Visuals-PBR-v{version(manifest(pbr))}.mcpack")
        full_tmp = OUT / "full.mcpack"
        full_ver = write_full_pack(full_tmp, rp, pbr)
        full_tmp.rename(personal / f"VYSE-Vibrant-Visuals-Full-v{full_ver}.mcpack")
        (personal / "README.txt").write_text(
            "VYSE-Vibrant Visuals PBR / VYSE-Vibrant Visuals Full\n\n"
            "Mojang のブロックのテクスチャを含むため、自分で使う分だけにしてください。\n"
            "配布ページなどにはアップロードしないでください。\n\n"
            "どちらか一方を使います。\n"
            "- PBR: VYSE-Vibrant Visuals の上に置いて、一緒に有効にします。\n"
            "- Full: 本体と PBR を 1 つにまとめたパックです。これだけを有効にします\n"
            "  （本体や PBR と一緒に有効にしないでください）。空の種類は歯車から選べます。\n\n"
            "Contains Mojang's block textures: for your own use only, never upload it.\n"
            "Use one of the two:\n"
            "- PBR: place it above VYSE-Vibrant Visuals and activate both.\n"
            "- Full: the main pack and PBR in one; activate it alone, not with the\n"
            "  other two. Pick the sky with the gear as usual.\n", encoding="utf-8-sig")

    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
