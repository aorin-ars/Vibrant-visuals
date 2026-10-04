#!/usr/bin/env python3
"""Build the optional PBR add-on - relief, glow and shine - from the vanilla block textures.

    tools/build_pbr.py --vanilla <bedrock-samples>/resource_pack [--out build/pbr] [--patch N]

Vibrant Visuals renders every block with a texture set: its colour, plus a
metalness/emissive/roughness/subsurface (MERS) map, plus optionally a height
or normal map. Vanilla's are plain: almost no block has relief, light blocks
glow faintly (glowstone at 41 of 255), and nearly everything is equally
rough, ice and polished metal included. This builds Complementary-style
texture sets on top of them:

  relief   a normal map for every block texture, derived from its own
           colour - brighter reads as raised - scaled by material: strong for
           cobblestone, ores and bricks, medium for wood, almost flat for
           wool and concrete, gentler for foliage and glass
           (RELIEF_BY_MATERIAL); cut-outs are measured on their visible
           pixels only, animated textures frame by frame, and the slopes
           wrap round the texture so block edges meet cleanly (height maps,
           used at first, drew a seam line along every block edge; nearly
           flat textures such as concrete get no relief map at all). Blocks
           drawn as entities - chests, beds, shulker boxes, bells, mob
           heads, signs - get normal maps too (ENTITY_BLOCKS)
  glow     light blocks glow like light blocks (EMISSION_TARGET), and ores
           glow faintly in their minerals, like Complementary's "glowing
           ores" (GLOWING_ORES)
  wet      mobs, boats, minecarts... turn darker and glossy while rain falls
           on them or they are in water (tools/wet_entities.py)
  through  stained glass lets light through and glows in its own colour when
           the sun is behind it (LIT_THROUGH)
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

Left without relief on purpose: water (the main pack's own texture sets
win), lava (vanilla already gives it a normal map), fire, portals and
bubble columns.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import wet_entities

ROOT = Path(__file__).resolve().parent.parent

# Fixed so that re-importing a rebuilt pack upgrades it in place (it replaces
# the earlier relief-only add-on). The patch number is stamped by
# tools/package.sh, since the game will not re-import an unchanged version.
HEADER_UUID = "5a1f3c2e-8d47-4b6a-9e21-7c0b4d9f6a13"
MODULE_UUID = "b2e87d45-1c9a-4f36-8a5d-3e6f0c7b9d28"
VERSION = [2, 0]
NAME = "VYSE-Vibrant Visuals PBR"
DESCRIPTION = ("Add-on for VYSE-Vibrant Visuals: relief on nearly every block, glowing light "
               "blocks and ores, glossy ice, metal and polished stone, mobs wet and glossy in "
               "rain. Built from the vanilla textures - for personal use only.")

IMAGE_EXTS = (".tga", ".png", ".jpg", ".jpeg")   # the engine's own priority order

# --------------------------------------------------------------------------
# Relief
# --------------------------------------------------------------------------

# Height = 0.5 + strength * (luminance - mean), clipped to 0.1..0.9.
# Deliberately not normalised per texture: a texture with little contrast
# (sand, wool, concrete) comes out nearly flat instead of having its faint
# noise stretched into bumps. First matching pattern wins; strength 0 means
# no relief at all.
RELIEF_BY_MATERIAL = [
    # Light and liquids that are not surfaces. Water is the main pack's.
    ("fire_*", 0.0), ("soul_fire_*", 0.0), ("portal*", 0.0), ("*bubble_column*", 0.0),
    ("water_*", 0.0), ("cauldron_water*", 0.0), ("end_gateway*", 0.0),
    ("*glass*", 0.3), ("iron_bars", 0.6), ("*door*", 1.0), ("*trapdoor*", 1.0),
    ("ladder", 1.0), ("rail*", 0.8),
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
# Textures with transparency not named above: cut-outs are mostly foliage
# and thin things (leaves, flowers, crops, vines), a little gentler;
# see-through ones (partly transparent pixels) gentler still.
CUTOUT_RELIEF = 0.7
TRANSLUCENT_RELIEF = 0.3

# Blocks drawn as entities: chests, beds, shulker boxes, bells, mob heads,
# signs, the enchanting table's book. Their textures are unwrapped models,
# which cannot take height maps, so they get normal maps instead. Patterns
# are paths under textures/entity; the value is the relief strength. Half
# of what the blocks get: these are smooth, made objects - planed wood,
# lacquered shells, cast metal - and read best as clean hard surfaces with
# a hint of their grain, not bumpy ones.
ENTITY_BLOCKS = [
    ("chest/*", 0.5), ("bed/*", 0.35), ("shulker/*", 0.4), ("bell/*", 0.35),
    ("skulls/*", 0.4), ("sign*", 0.5), ("*_sign", 0.5), ("enchanting_table_book", 0.3),
]
# Slope of the normal per unit of luminance difference between neighbouring
# pixels: 0.1 of luminance across a pixel tilts the surface ~17 degrees.
NORMAL_SLOPE = 3.0

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
    "bell/*": 0.5, "chest/copper_*": 0.8,
}
CREVICE_ROUGHNESS = 50    # extra roughness (0-255) at the lowest point of the relief

# Light through: stained glass passes light (subsurface), so a pane glows in
# its own colour when the sun shines through it from behind - stained glass
# in a sunlit window or roof. Vanilla gives glass no transmission at all.
# Vibrant Visuals cannot tint the sunlight that reaches the floor behind the
# glass (its shadows have no colour), so this is as close as it gets. Clear
# and black glass are left as they are.
LIT_THROUGH = [
    ("glass_black", 0), ("glass_pane_top_black", 0), ("glass_pane_top", 0),
    ("glass_*", 0.75),
]


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


def smoothed_luminance(color: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """Luminance with a touch of blur - so single noisy pixels do not become
    spikes while the texture's shapes stay sharp - and the opacity mask."""
    rgba = np.asarray(color.convert("RGBA"), dtype=np.float64) / 255.0
    lum = rgba[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    blurred = np.asarray(Image.fromarray(np.uint8(np.round(lum * 255))).filter(
        ImageFilter.GaussianBlur(0.6)), dtype=np.float64) / 255.0
    return 0.6 * lum + 0.4 * blurred, rgba[..., 3] > 0.5


def frames(shape: tuple[int, int]) -> list[slice]:
    """Row ranges of the frames of a vertical flipbook strip (one frame if
    the image is square or not a strip of squares)."""
    rows, cols = shape
    if rows > cols and rows % cols == 0:
        return [slice(r, r + cols) for r in range(0, rows, cols)]
    return [slice(0, rows)]


def height_map(color: Image.Image, strength: float, invert: bool, raise_mask=None) -> np.ndarray:
    """0..1 height. Each animation frame is measured on its own, and only
    visible pixels count; transparent ones stay flat (0.5)."""
    lum, opaque = smoothed_luminance(color)
    height = np.full(lum.shape, 0.5)
    for rows in frames(lum.shape):
        seen = opaque[rows]
        if not seen.any():
            continue
        relief = strength * (lum[rows] - float(lum[rows][seen].mean()))
        height[rows] = np.where(seen, 0.5 + (-relief if invert else relief), 0.5)
    if raise_mask is not None:
        height += ORE_RAISE * raise_mask
    return np.clip(height, 0.1, 0.9)


def normal_map(color: Image.Image, strength: float) -> np.ndarray:
    """RGB normal map for an entity texture, in the convention vanilla's own
    normal maps use (DirectX: green points down the image). Transparent
    pixels, and edges between a model's unwrapped faces, stay flat."""
    lum, opaque = smoothed_luminance(color)
    h = strength * NORMAL_SLOPE * lum
    gy, gx = np.gradient(h)
    # Differences across a transparent gap are not a slope.
    both_x = opaque & np.roll(opaque, 1, 1) & np.roll(opaque, -1, 1)
    both_y = opaque & np.roll(opaque, 1, 0) & np.roll(opaque, -1, 0)
    gx = np.where(both_x, gx, 0.0)
    gy = np.where(both_y, gy, 0.0)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.uint8(np.round((n * 0.5 + 0.5) * 255))


# Block relief is shipped as normal maps computed here, not as height maps.
# Vibrant Visuals compares a height map's border pixels with what lies beyond
# the texture, so every block with one got a thin seam line along its edges -
# plainest on smooth blocks like concrete. Here the slopes wrap around the
# texture (block textures tile), so the edges match their neighbours.
BLOCK_NORMAL_SLOPE = 2.0   # surface tilt per unit of height step between pixels
FLAT_LIMIT = 0.03          # below this steepest tilt (~2 degrees) a texture gets no relief map


def block_normal_map(height: np.ndarray, opaque: np.ndarray) -> np.ndarray | None:
    """RGB normal map (vanilla's DirectX convention) from a 0..1 height
    field, slopes wrapping within each animation frame; None if flat."""
    gx = np.zeros_like(height)
    gy = np.zeros_like(height)
    for rows in frames(height.shape):
        h, seen = height[rows], opaque[rows]
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
        # A difference across a transparent gap is not a slope.
        both_x = seen & np.roll(seen, 1, 1) & np.roll(seen, -1, 1)
        both_y = seen & np.roll(seen, 1, 0) & np.roll(seen, -1, 0)
        gx[rows] = np.where(both_x, dx, 0.0) * BLOCK_NORMAL_SLOPE
        gy[rows] = np.where(both_y, dy, 0.0) * BLOCK_NORMAL_SLOPE
    if max(np.abs(gx).max(), np.abs(gy).max()) < FLAT_LIMIT:
        return None
    n = np.dstack([-gx, -gy, np.ones_like(height)])
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.uint8(np.round((n * 0.5 + 0.5) * 255))


def relief_strength(key: str, color: Image.Image) -> float:
    strength = match(key, RELIEF_BY_MATERIAL)
    if strength is not None:
        return strength
    alpha = np.asarray(color.convert("RGBA"))[..., 3]
    if ((alpha > 10) & (alpha < 245)).mean() > 0.05:
        return TRANSLUCENT_RELIEF
    if (alpha < 128).any():
        return CUTOUT_RELIEF
    return DEFAULT_RELIEF


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vanilla", type=Path, required=True,
                        help="Mojang bedrock-samples resource_pack directory")
    parser.add_argument("--out", type=Path, default=ROOT / "build/pbr")
    parser.add_argument("--patch", type=int, default=0, help="patch number of the pack version")
    args = parser.parse_args()
    vanilla: Path = args.vanilla
    blocks = vanilla / "textures/blocks"
    entities = vanilla / "textures/entity"
    if not blocks.is_dir() or not any(blocks.glob("*.png")):
        print(f"{blocks} has no block textures. With a sparse clone of bedrock-samples, run:\n"
              "  git sparse-checkout add /resource_pack/textures/blocks/")
        return 1
    if not any(entities.glob("chest/*.png")):
        print(f"{entities} has no chest, bed or sign textures. With a sparse clone, run:\n"
              "  git sparse-checkout add /resource_pack/textures/entity/chest/ "
              "/resource_pack/textures/entity/bed/ /resource_pack/textures/entity/shulker/ "
              "/resource_pack/textures/entity/bell/ /resource_pack/textures/entity/skulls/ "
              "'/resource_pack/textures/entity/*.png' '/resource_pack/textures/entity/*.tga'")
        return 1

    # Textures the main pack gives texture sets of its own (its water):
    # never override them.
    own = {json.loads(p.read_text())["minecraft:texture_set"]["color"]
           for p in (ROOT / "bedrock/textures/blocks").glob("*.texture_set.json")}

    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    counts = {"relief": 0, "entity relief": 0, "glow": 0, "glowing ores": 0, "shine": 0,
              "light through": 0}
    skipped: dict[str, int] = {}

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    jobs = [(p, blocks, "block") for p in sorted(blocks.rglob("*.texture_set.json"))]
    for p in sorted(entities.rglob("*.texture_set.json")):
        key = (p.parent.relative_to(entities) / p.name.removesuffix(".texture_set.json")).as_posix()
        if match(key, ENTITY_BLOCKS) is not None:
            jobs.append((p, entities, "entity"))

    for ts_path, root, kind in jobs:
        texture_set = json.loads(ts_path.read_text())["minecraft:texture_set"]
        folder = ts_path.parent
        name = texture_set.get("color")
        if not isinstance(name, str):
            skip("uniform colour")
            continue
        if kind == "block" and name in own:
            skip("the main pack's own texture set")
            continue
        color_path = find_image(folder, name)
        mers_name = texture_set.get("metalness_emissive_roughness_subsurface")
        mers_path = find_image(folder, mers_name) if isinstance(mers_name, str) else None
        if not color_path:
            skip("colour image missing")
            continue
        key = (folder.relative_to(root) / name).as_posix()      # e.g. deepslate/deepslate_iron_ore
        color = Image.open(color_path)
        mers = None
        if mers_path:
            try:
                mers = np.asarray(Image.open(mers_path).convert("RGBA"), dtype=np.float64)
            except OSError:
                skip("MERS image unreadable: copied unchanged")
        mers_orig = None if mers is None else mers.copy()
        same_size = mers is not None and mers.shape[:2] == (color.size[1], color.size[0])

        # Relief
        height = normal = block_normal = None
        has_bump = "normal" in texture_set or "heightmap" in texture_set
        ore = GLOWING_ORES.get(key) if kind == "block" else None
        minerals = None
        if ore:
            host_path = find_image(blocks, ore[0])
            if host_path:
                minerals = mineral_mask(color, Image.open(host_path))
        if kind == "entity" and not has_bump:
            normal = normal_map(color, match(key, ENTITY_BLOCKS))
        elif not has_bump:
            strength = relief_strength(key, color)
            if strength > 0:
                height = height_map(color, strength, name in INVERTED, minerals)
                block_normal = block_normal_map(height, smoothed_luminance(color)[1])
                if block_normal is None:
                    skip("no relief: flat texture (concrete, plain wool...)")
                if same_size:
                    # Crevices hold dust and shade: a little rougher than the tops.
                    mers[..., 2] += CREVICE_ROUGHNESS * np.clip(0.5 - height, 0.0, 0.4) / 0.4
            else:
                skip("no relief: not a surface (fire, portals, liquids)")
        else:
            skip("no relief: vanilla already has bump data")

        if mers is not None:
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
            through = match(key, LIT_THROUGH)
            if through:
                mers[..., 3] = np.maximum(mers[..., 3], 255 * through)
                counts["light through"] += 1

        changed_mers = mers is not None and not np.array_equal(
            np.round(np.clip(mers, 0, 255)), mers_orig)
        if block_normal is None and normal is None and not changed_mers:
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
        elif mers_path:
            new_set["metalness_emissive_roughness_subsurface"] = mers_name
            shutil.copy2(mers_path, dest / mers_path.name)
        if "normal" in texture_set:
            normal_path = find_image(folder, texture_set["normal"])
            if normal_path:
                shutil.copy2(normal_path, dest / normal_path.name)
                new_set["normal"] = texture_set["normal"]
        if block_normal is not None:
            new_set["normal"] = f"{name}_vu_normal"
            Image.fromarray(block_normal, "RGB").save(dest / f"{name}_vu_normal.png")
            counts["relief"] += 1
        if normal is not None:
            new_set["normal"] = f"{name}_vu_normal"
            Image.fromarray(normal, "RGB").save(dest / f"{name}_vu_normal.png")
            counts["entity relief"] += 1
        (dest / ts_path.name).write_text(json.dumps({
            "format_version": "1.21.30", "minecraft:texture_set": new_set}, indent=2) + "\n")

    # Wet entities: glossy in rain (see tools/wet_entities.py).
    wet = None
    if (vanilla / "entity").is_dir() and (vanilla / "render_controllers").is_dir():
        wet = wet_entities.build(vanilla, out)
    else:
        print("no vanilla entity/ or render_controllers/ - wet entities skipped. With a sparse "
              "clone, run:\n  git sparse-checkout add /resource_pack/entity/ "
              "/resource_pack/render_controllers/")

    version = VERSION + [args.patch]
    manifest = {
        "format_version": 2,
        "header": {
            "name": NAME,
            "description": DESCRIPTION,
            "uuid": HEADER_UUID,
            "version": version,
            "min_engine_version": [1, 21, 120],
        },
        "modules": [{"type": "resources", "description": DESCRIPTION,
                     "uuid": MODULE_UUID, "version": version}],
        "capabilities": ["pbr"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy2(ROOT / "branding/pbr_pack_icon.png", out / "pack_icon.png")

    print(f"{out}: {counts['relief']} block textures with relief, {counts['entity relief']} "
          f"chest/bed/sign/... textures with relief, {counts['glow']} brighter light blocks, "
          f"{counts['glowing ores']} glowing ores, {counts['shine']} smoother surfaces, "
          f"{counts['light through']} stained glass textures that let light through")
    if wet:
        print(f"  wet in rain: {wet['entities']} entities, {wet['textures']} wet textures, "
              f"{wet['controllers']} render controllers")
    for reason, count in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f"  {count:4d}  {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
