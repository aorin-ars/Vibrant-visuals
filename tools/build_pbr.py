#!/usr/bin/env python3
"""Build the optional surface-relief add-on from the vanilla block textures.

    tools/build_pbr.py --vanilla <bedrock-samples>/resource_pack [--out build/pbr]

Complementary's "generated normals" give every block a little relief: the
light catches the raised stones in cobblestone and the grain of planks. Vibrant
Visuals can do the same with a height map in each block's texture set, but
vanilla ships none (only colour and metalness/emissive/roughness/subsurface).

This derives a height map from each block's own colour - brighter reads as
raised - and writes a texture set that keeps vanilla's colour and MERS layers
unchanged and adds the height map.

The output contains Mojang's textures, because a texture set may only
reference images in its own pack. That is why it is built here from your copy
of the vanilla files instead of living in the repository, and why it is a
separate pack from the main one: it is for your own use, not for
redistribution.

Skipped on purpose: anything with transparency (plants, leaves, glass,
doors - relief on a cut-out looks wrong), animated textures, and the few
blocks vanilla already gives a normal map.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# Fixed so that re-importing a rebuilt pack upgrades it in place.
HEADER_UUID = "5a1f3c2e-8d47-4b6a-9e21-7c0b4d9f6a13"
MODULE_UUID = "b2e87d45-1c9a-4f36-8a5d-3e6f0c7b9d28"
VERSION = [1, 0, 0]

# Height = 0.5 + RELIEF * (luminance - mean), clipped. Deliberately not
# normalised per texture: a texture with little contrast (sand, wool,
# concrete) should come out nearly flat, not have its faint noise stretched
# into bumps, while cobblestone and ores get strong relief.
RELIEF = 1.2

# Luminance says bright = raised. In these the bright part is mortar, which
# sits *below* the bricks, so the map is flipped.
INVERTED = {"brick"}

IMAGE_EXTS = (".tga", ".png", ".jpg", ".jpeg")   # the engine's own priority order


def find_image(folder: Path, name: str) -> Path | None:
    for ext in IMAGE_EXTS:
        path = folder / (name + ext)
        if path.is_file():
            return path
    return None


def load_jsonc(path: Path):
    return json.loads(re.sub(r"^\s*//.*$", "", path.read_text(), flags=re.M))


def height_map(color: Image.Image, invert: bool = False) -> Image.Image:
    rgb = np.asarray(color.convert("RGB"), dtype=np.float64) / 255.0
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    relief = RELIEF * (lum - float(lum.mean()))
    height = 0.5 + (-relief if invert else relief)
    return Image.fromarray(np.round(np.clip(height, 0.15, 0.85) * 255).astype(np.uint8), "L")


def eligible(color: Image.Image, texture_set: dict, mers: Path | None,
             animated: bool) -> str | None:
    """Returns why a texture set is skipped, or None if it gets a height map."""
    if animated:
        return "animated"
    if "normal" in texture_set or "heightmap" in texture_set:
        return "already has bump data"
    if not isinstance(texture_set.get("metalness_emissive_roughness_subsurface"), str) or not mers:
        return "no MERS image"
    width, height = color.size
    if height != width:
        return "animated"
    if Image.open(mers).size != color.size:
        return "MERS size differs"
    alpha = np.asarray(color.convert("RGBA"))[..., 3]
    if (alpha < 250).any():
        return "transparent"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vanilla", type=Path, required=True,
                        help="Mojang bedrock-samples resource_pack directory")
    parser.add_argument("--out", type=Path, default=ROOT / "build/pbr")
    args = parser.parse_args()
    vanilla: Path = args.vanilla
    blocks = vanilla / "textures/blocks"
    if not blocks.is_dir() or not any(blocks.glob("*.png")):
        print(f"{blocks} has no block textures. With a sparse clone of bedrock-samples, run:\n"
              "  git sparse-checkout add /resource_pack/textures/blocks/")
        return 1

    flipbooks = {e["flipbook_texture"] for e in load_jsonc(vanilla / "textures/flipbook_textures.json")}

    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    skipped: dict[str, int] = {}
    built = 0

    for ts_path in sorted(blocks.rglob("*.texture_set.json")):
        texture_set = json.loads(ts_path.read_text())["minecraft:texture_set"]
        folder = ts_path.parent
        if not isinstance(texture_set.get("color"), str):
            skipped["uniform colour"] = skipped.get("uniform colour", 0) + 1
            continue
        color_path = find_image(folder, texture_set["color"])
        mers_name = texture_set.get("metalness_emissive_roughness_subsurface")
        mers_path = find_image(folder, mers_name) if isinstance(mers_name, str) else None
        if not color_path:
            skipped["colour image missing"] = skipped.get("colour image missing", 0) + 1
            continue

        rel_color = color_path.relative_to(vanilla).with_suffix("").as_posix()
        color = Image.open(color_path)
        reason = eligible(color, texture_set, mers_path, rel_color in flipbooks)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue

        dest = out / folder.relative_to(vanilla)
        dest.mkdir(parents=True, exist_ok=True)
        # Colour and MERS are copied byte for byte; only the height map is new.
        shutil.copy2(color_path, dest / color_path.name)
        shutil.copy2(mers_path, dest / mers_path.name)
        height_name = f"{texture_set['color']}_height"
        height_map(color, texture_set["color"] in INVERTED).save(dest / f"{height_name}.png")
        (dest / ts_path.name).write_text(json.dumps({
            "format_version": "1.21.30",
            "minecraft:texture_set": {
                "color": texture_set["color"],
                "metalness_emissive_roughness_subsurface": mers_name,
                "heightmap": height_name,
            },
        }, indent=2) + "\n")
        built += 1

    manifest = {
        "format_version": 2,
        "header": {
            "name": "pack.name",
            "description": "pack.description",
            "uuid": HEADER_UUID,
            "version": VERSION,
            "min_engine_version": [1, 21, 120],
        },
        "modules": [{"type": "resources", "description": "pack.description",
                     "uuid": MODULE_UUID, "version": VERSION}],
        "capabilities": ["pbr"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy2(ROOT / "bedrock/pack_icon.png", out / "pack_icon.png")
    texts = out / "texts"
    texts.mkdir()
    (texts / "en_US.lang").write_text(
        "pack.name=Vibrant Unbound - Block Relief\n"
        "pack.description=Optional add-on: height maps for opaque blocks, derived from the "
        "vanilla textures. Use together with Vibrant Unbound. Personal use only.\n")
    (texts / "ja_JP.lang").write_text(
        "pack.name=Vibrant Unbound - ブロックの凹凸\n"
        "pack.description=追加パック：不透明ブロックに凹凸（ハイトマップ）を付けます。"
        "Vibrant Unbound と一緒に使ってください。個人利用のみ。\n", encoding="utf-8")

    print(f"{out}: {built} blocks with height maps")
    for reason, count in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f"  skipped {count:4d}  {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
