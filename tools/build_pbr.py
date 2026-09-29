#!/usr/bin/env python3
"""Build the optional PBR add-on - relief, glow and shine - from the vanilla block textures.

    tools/build_pbr.py --vanilla <bedrock-samples>/resource_pack [--out build/pbr] [--patch N]

Vibrant Visuals renders every block with a texture set: its colour, plus a
metalness/emissive/roughness/subsurface (MERS) map, plus optionally a height
or normal map. Vanilla's are plain: almost no block has relief, light blocks
glow faintly (glowstone at 41 of 255), and nearly everything is equally
rough, ice and polished metal included. This builds Complementary-style
texture sets on top of them:

  relief   a height map for every opaque block, derived from its own
           colour - brighter reads as raised - scaled by material: strong for
           cobblestone, ores and bricks, medium for wood, almost flat for
           wool and concrete (RELIEF_BY_MATERIAL)
  glow     light blocks glow like light blocks (EMISSION_TARGET), and ores
           glow faintly in their minerals, like Complementary's "glowing
           ores" (GLOWING_ORES)
  shine    ice, metal blocks, gems, obsidian, glazed terracotta and polished
           stone are smoother, so they catch reflections (SMOOTHER); in every
           block with relief the crevices are a little rougher than the tops

Vanilla's colour images are copied byte for byte; the height and MERS maps
are computed here from vanilla's.

The output contains Mojang's textures, because a texture set may only
reference images in its own pack. That is why it is built here from your copy
of the vanilla files instead of living in the repository, and why it is a
separate pack from the main one: it is for your own use, not for
redistribution.

Relief is skipped on purpose for anything with transparency (plants,
leaves, glass, doors - relief on a cut-out looks wrong), animated textures,
and the few blocks vanilla already gives a normal map; they can still get
glow and shine.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent

# Fixed so that re-importing a rebuilt pack upgrades it in place (it replaces
# the earlier relief-only add-on). The patch number is stamped by
# tools/package.sh, since the game will not re-import an unchanged version.
HEADER_UUID = "5a1f3c2e-8d47-4b6a-9e21-7c0b4d9f6a13"
MODULE_UUID = "b2e87d45-1c9a-4f36-8a5d-3e6f0c7b9d28"
VERSION = [2, 0]

IMAGE_EXTS = (".tga", ".png", ".jpg", ".jpeg")   # the engine's own priority order

# --------------------------------------------------------------------------
# Relief
# --------------------------------------------------------------------------

# Height = 0.5 + strength * (luminance - mean), clipped to 0.1..0.9.
# Deliberately not normalised per texture: a texture with little contrast
# (sand, wool, concrete) comes out nearly flat instead of having its faint
# noise stretched into bumps. First matching pattern wins.
RELIEF_BY_MATERIAL = [
    ("*glazed_terracotta*", 0.25), ("concrete_powder*", 0.6), ("concrete_*", 0.25),
    ("ice*", 0.2), ("blue_ice", 0.2),
    ("wool_*", 0.5), ("hardened_clay*", 0.5), ("quartz*", 0.5), ("*smooth*", 0.5),
    ("polished_*", 0.6), ("*_block", 0.7), ("cut_copper*", 0.7), ("*copper_block", 0.7),
    ("snow", 0.6), ("clay", 0.6), ("mud", 0.8), ("sand", 0.8), ("red_sand", 0.8),
    ("*_ore", 1.6), ("deepslate/*_ore", 1.6), ("cobblestone*", 1.7), ("*cobbled*", 1.7),
    ("bedrock", 1.7), ("stone", 1.4), ("netherrack", 1.5), ("end_stone", 1.4),
    ("blackstone*", 1.4), ("basalt*", 1.4), ("tuff*", 1.3), ("dripstone*", 1.4),
    ("gravel", 1.3), ("*brick*", 1.5), ("deepslate*", 1.4), ("stone_*", 1.2),
    ("log_*", 1.4), ("stripped_*", 1.0), ("*planks*", 1.1), ("dirt*", 1.1), ("coarse_dirt", 1.2),
]
DEFAULT_RELIEF = 1.0

# Luminance says bright = raised. In these the bright part is mortar, which
# sits *below* the bricks, so the map is flipped.
INVERTED = {"brick"}

# --------------------------------------------------------------------------
# Glow
# --------------------------------------------------------------------------

# Light blocks: vanilla's emissive map scaled so its brightest pixel reaches
# this (0-255). Vanilla keeps them very low, so glowstone or a froglight
# barely stands out from a sunlit wall.
EMISSION_TARGET = {
    "glowstone": 170, "sea_lantern": 160, "shroomlight": 150, "*froglight*": 150,
    "magma": 110, "crying_obsidian": 120, "redstone_block": 70, "sea_pickle": 140,
    "glow_lichen": 120, "cave_vines_*berries": 170, "end_rod": 180, "beacon": 190,
    "respawn_anchor_*": 150, "sculk*": 60, "*copper_bulb_lit*": 200,
}

# Ores: the mineral pixels (those that differ from the host stone and are
# colourful or brighter than it) glow faintly with this emission (0-255),
# and gems are smoother there. Coal does not glow.
GLOWING_ORES = {
    "diamond_ore": ("stone", 80, True), "emerald_ore": ("stone", 80, True),
    "lapis_ore": ("stone", 60, True), "redstone_ore": ("stone", 110, False),
    "gold_ore": ("stone", 55, False), "iron_ore": ("stone", 40, False),
    "copper_ore": ("stone", 40, False),
    "deepslate/deepslate_diamond_ore": ("deepslate/deepslate", 80, True),
    "deepslate/deepslate_emerald_ore": ("deepslate/deepslate", 80, True),
    "deepslate/deepslate_lapis_ore": ("deepslate/deepslate", 60, True),
    "deepslate/deepslate_redstone_ore": ("deepslate/deepslate", 110, False),
    "deepslate/deepslate_gold_ore": ("deepslate/deepslate", 55, False),
    "deepslate/deepslate_iron_ore": ("deepslate/deepslate", 40, False),
    "deepslate/deepslate_copper_ore": ("deepslate/deepslate", 40, False),
    "nether_gold_ore": ("netherrack", 60, False), "quartz_ore": ("netherrack", 45, True),
    "gilded_blackstone": ("blackstone", 50, False),
}
ORE_RAISE = 0.18          # minerals stand proud of the stone in the height map

# --------------------------------------------------------------------------
# Shine
# --------------------------------------------------------------------------

# Roughness multipliers (vanilla's roughness x this; lower is glossier).
SMOOTHER = {
    "ice": 0.3, "ice_packed": 0.35, "blue_ice": 0.3,
    "iron_block": 0.55, "gold_block": 0.55, "netherite_block": 0.6, "copper_block": 0.75,
    "cut_copper": 0.75, "diamond_block": 0.5, "emerald_block": 0.5, "lapis_block": 0.7,
    "obsidian": 0.55, "crying_obsidian": 0.6, "glazed_terracotta_*": 0.6,
    "polished_*": 0.8, "*smooth*": 0.85, "quartz_block*": 0.8, "amethyst_block": 0.7,
}
CREVICE_ROUGHNESS = 50    # extra roughness (0-255) at the lowest point of the relief


def match(name: str, table):
    """First value whose pattern matches the texture name (dict or pair list)."""
    items = table.items() if isinstance(table, dict) else table
    for pattern, value in items:
        if fnmatch.fnmatchcase(name, pattern):
            return value
    return None


def find_image(folder: Path, name: str) -> Path | None:
    for ext in IMAGE_EXTS:
        path = folder / (name + ext)
        if path.is_file():
            return path
    return None


def load_jsonc(path: Path):
    return json.loads(re.sub(r"^\s*//.*$", "", path.read_text(), flags=re.M))


def luminance(color: Image.Image) -> np.ndarray:
    rgb = np.asarray(color.convert("RGB"), dtype=np.float64) / 255.0
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def mineral_mask(ore: Image.Image, host: Image.Image) -> np.ndarray:
    """0..1 per pixel: how clearly the pixel is ore mineral, not host stone
    or the dark outline drawn round the minerals."""
    a = np.asarray(ore.convert("RGB"), dtype=np.float64) / 255.0
    b = np.asarray(host.convert("RGB"), dtype=np.float64) / 255.0
    if a.shape != b.shape:
        return np.zeros(a.shape[:2])
    differs = np.clip((np.abs(a - b).sum(-1) - 0.12) / 0.2, 0.0, 1.0)
    saturation = (a.max(-1) - a.min(-1)) / np.maximum(a.max(-1), 1e-6)
    brighter = (a @ np.array([0.2126, 0.7152, 0.0722])) - (b @ np.array([0.2126, 0.7152, 0.0722]))
    distinct = np.clip(np.maximum((saturation - 0.25) / 0.25, brighter / 0.15), 0.0, 1.0)
    return differs * distinct


def height_map(color: Image.Image, strength: float, invert: bool, raise_mask=None) -> np.ndarray:
    """0..1 height. A touch of blur keeps single noisy pixels from becoming
    spikes while the texture's shapes stay sharp."""
    lum = luminance(color)
    blurred = np.asarray(Image.fromarray(np.uint8(np.round(lum * 255))).filter(
        ImageFilter.GaussianBlur(0.6)), dtype=np.float64) / 255.0
    lum = 0.6 * lum + 0.4 * blurred
    relief = strength * (lum - float(lum.mean()))
    height = 0.5 + (-relief if invert else relief)
    if raise_mask is not None:
        height += ORE_RAISE * raise_mask
    return np.clip(height, 0.1, 0.9)


def eligible_for_relief(color: Image.Image, texture_set: dict, animated: bool) -> str | None:
    """Returns why a texture gets no height map, or None if it does."""
    if animated:
        return "animated"
    if "normal" in texture_set or "heightmap" in texture_set:
        return "already has bump data"
    width, height = color.size
    if height != width:
        return "animated"
    alpha = np.asarray(color.convert("RGBA"))[..., 3]
    if (alpha < 250).any():
        return "transparent"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vanilla", type=Path, required=True,
                        help="Mojang bedrock-samples resource_pack directory")
    parser.add_argument("--out", type=Path, default=ROOT / "build/pbr")
    parser.add_argument("--patch", type=int, default=0, help="patch number of the pack version")
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
    counts = {"relief": 0, "glow": 0, "glowing ores": 0, "shine": 0}
    skipped: dict[str, int] = {}

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    for ts_path in sorted(blocks.rglob("*.texture_set.json")):
        texture_set = json.loads(ts_path.read_text())["minecraft:texture_set"]
        folder = ts_path.parent
        name = texture_set.get("color")
        if not isinstance(name, str):
            skip("uniform colour")
            continue
        color_path = find_image(folder, name)
        mers_name = texture_set.get("metalness_emissive_roughness_subsurface")
        mers_path = find_image(folder, mers_name) if isinstance(mers_name, str) else None
        if not color_path or not mers_path:
            skip("colour or MERS image missing")
            continue
        key = (folder.relative_to(blocks) / name).as_posix()      # e.g. deepslate/deepslate_iron_ore
        rel_color = color_path.relative_to(vanilla).with_suffix("").as_posix()
        color = Image.open(color_path)
        try:
            mers = np.asarray(Image.open(mers_path).convert("RGBA"), dtype=np.float64)
        except OSError:
            skip("MERS image unreadable")
            continue
        mers_orig = mers.copy()

        # Relief
        height = None
        why_not = eligible_for_relief(color, texture_set, rel_color in flipbooks)
        ore = GLOWING_ORES.get(key)
        minerals = None
        if ore:
            host_path = find_image(blocks, ore[0])
            if host_path:
                minerals = mineral_mask(color, Image.open(host_path))
        if why_not is None and mers.shape[:2] == (color.size[1], color.size[0]):
            strength = match(key, RELIEF_BY_MATERIAL)
            strength = DEFAULT_RELIEF if strength is None else strength
            height = height_map(color, strength, name in INVERTED, minerals)
            # Crevices hold dust and shade: a little rougher than the tops.
            mers[..., 2] += CREVICE_ROUGHNESS * np.clip(0.5 - height, 0.0, 0.4) / 0.4
        elif why_not:
            skip(f"no relief: {why_not}")

        # Glow
        target = match(key, EMISSION_TARGET)
        peak = mers[..., 1].max()
        if target and 0 < peak < target:
            mers[..., 1] *= target / peak
            counts["glow"] += 1
        if ore and minerals is not None and minerals.shape == mers.shape[:2]:
            _, glow, gem = ore
            mers[..., 1] = np.maximum(mers[..., 1], glow * minerals)
            if gem:
                mers[..., 2] = mers[..., 2] * (1 - 0.6 * minerals)
            counts["glowing ores"] += 1

        # Shine
        factor = match(key, SMOOTHER)
        if factor:
            mers[..., 2] *= factor
            counts["shine"] += 1

        changed_mers = not np.array_equal(np.round(np.clip(mers, 0, 255)), mers_orig)
        if height is None and not changed_mers:
            continue

        dest = out / folder.relative_to(vanilla)
        dest.mkdir(parents=True, exist_ok=True)
        # The colour image is copied byte for byte.
        shutil.copy2(color_path, dest / color_path.name)
        new_set = {"color": name}
        if changed_mers:
            # A name of our own, so the engine never picks vanilla's image
            # (it looks for .tga before .png) instead of this one.
            new_set["metalness_emissive_roughness_subsurface"] = f"{name}_vu_mers"
            Image.fromarray(np.uint8(np.round(np.clip(mers, 0, 255))), "RGBA").save(
                dest / f"{name}_vu_mers.png")
        else:
            new_set["metalness_emissive_roughness_subsurface"] = mers_name
            shutil.copy2(mers_path, dest / mers_path.name)
        if "normal" in texture_set:
            normal_path = find_image(folder, texture_set["normal"])
            if normal_path:
                shutil.copy2(normal_path, dest / normal_path.name)
                new_set["normal"] = texture_set["normal"]
        if height is not None:
            new_set["heightmap"] = f"{name}_height"
            Image.fromarray(np.uint8(np.round(height * 255)), "L").save(dest / f"{name}_height.png")
            counts["relief"] += 1
        (dest / ts_path.name).write_text(json.dumps({
            "format_version": "1.21.30", "minecraft:texture_set": new_set}, indent=2) + "\n")

    version = VERSION + [args.patch]
    manifest = {
        "format_version": 2,
        "header": {
            "name": "pack.name",
            "description": "pack.description",
            "uuid": HEADER_UUID,
            "version": version,
            "min_engine_version": [1, 21, 120],
        },
        "modules": [{"type": "resources", "description": "pack.description",
                     "uuid": MODULE_UUID, "version": version}],
        "capabilities": ["pbr"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy2(ROOT / "bedrock/pack_icon.png", out / "pack_icon.png")
    texts = out / "texts"
    texts.mkdir()
    (texts / "en_US.lang").write_text(
        "pack.name=Vibrant Unbound - PBR\n"
        "pack.description=Optional add-on: block relief, glowing light blocks and ores, "
        "glossy ice and metal. Built from the vanilla textures; use together with Vibrant "
        "Unbound. Personal use only.\n")
    (texts / "ja_JP.lang").write_text(
        "pack.name=Vibrant Unbound - PBR\n"
        "pack.description=追加パック：ブロックの凹凸、光るブロックと鉱石の発光、氷や金属のつや。"
        "バニラのテクスチャから作ります。Vibrant Unbound と一緒に使ってください。個人利用のみ。\n",
        encoding="utf-8")

    print(f"{out}: {counts['relief']} blocks with relief, {counts['glow']} brighter light blocks, "
          f"{counts['glowing ores']} glowing ores, {counts['shine']} smoother surfaces")
    for reason, count in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f"  {count:4d}  {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
