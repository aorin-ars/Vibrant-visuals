"""Wet entities for the PBR add-on: mobs (and boats, minecarts, armor
stands...) turn darker and glossy while rain falls on them or they are in
water, and dry as soon as they are out of it.

Weather cannot change any material setting in Vibrant Visuals, but an
entity's render controller can pick its textures with Molang, and
query.is_in_water_or_rain is true exactly while the entity is wet. So for
every vanilla client entity:

  - each of its textures gets a wet copy next to it, <name>_wet: the colour
    a little darker (wet surfaces absorb more light) and a texture set whose
    roughness is about half of the dry one (a film of water on top)
  - the entity gets a <key>_wet texture for every <key> it has
  - its render controllers are replaced by copies, <name>.vyse_wet, whose
    every texture expression E becomes
        query.is_in_water_or_rain ? (E with every texture/array renamed _wet) : (E)
    and whose texture arrays get _wet twins

The vanilla render controllers themselves are not changed - add-ons use them
too (MTC trains use controller.render.phantom) and have no _wet textures.
The player is left alone (its texture is the player's skin).

The entity files here are copies of vanilla's, so they match the vanilla
version they were built from: rebuild the add-on after a game update.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

WET_DARKEN = 0.88          # colour of a wet surface relative to the dry one
WET_ROUGHNESS = 0.45       # roughness of a wet surface relative to the dry one
# Entities without a texture set use the main pack's actor default (190).
DRY_DEFAULT_MERS = (0, 0, 190, 0)
SKIP = {"minecraft:player"}
SUFFIX = "_wet"
CONTROLLER_SUFFIX = ".vyse_wet"
WET = "query.is_in_water_or_rain"
IMAGE_EXTS = (".tga", ".png", ".jpg", ".jpeg")

_REF = re.compile(r"\b(texture|array)\.([A-Za-z0-9_]+)", re.IGNORECASE)


def load_json(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return json.loads(text)


def wet_expression(expr: str) -> str:
    return _REF.sub(lambda m: f"{m.group(1)}.{m.group(2)}{SUFFIX}", expr)


def texture_refs(expr: str) -> set[str]:
    return {m.group(2).lower() for m in _REF.finditer(expr) if m.group(1).lower() == "texture"}


def wet_controller(ctrl: dict) -> dict | None:
    """The controller with wet switching, or None if it has no texture to switch."""
    textures = ctrl.get("textures")
    if not isinstance(textures, list) or not any(_REF.search(t) for t in textures if isinstance(t, str)):
        return None
    new = copy.deepcopy(ctrl)
    new["textures"] = [f"{WET} ? ({wet_expression(t)}) : ({t})"
                       if isinstance(t, str) and _REF.search(t) else t for t in textures]
    arrays = new.get("arrays", {}).get("textures")
    if isinstance(arrays, dict):
        for name, entries in list(arrays.items()):
            arrays[name + SUFFIX] = [wet_expression(e) if isinstance(e, str) else e for e in entries]
    return new


def required_textures(ctrl: dict) -> set[str]:
    refs = set()
    for t in ctrl.get("textures", []):
        if isinstance(t, str):
            refs |= texture_refs(t)
    for entries in ctrl.get("arrays", {}).get("textures", {}).values():
        for e in entries:
            if isinstance(e, str):
                refs |= texture_refs(e)
    return refs


def find_image(base: Path) -> Path | None:
    for ext in IMAGE_EXTS:
        if base.with_name(base.name + ext).is_file():
            return base.with_name(base.name + ext)
    return None


def scale_roughness(value, factor):
    """Uniform MERS value (list or hex string) with its roughness scaled."""
    if isinstance(value, str):
        v = value.lstrip("#")
        vals = [int(v[i:i + 2], 16) for i in range(0, len(v), 2)]
    else:
        vals = list(value)
    if len(vals) >= 3:
        vals[2] = int(round(vals[2] * WET_ROUGHNESS))
    return vals


class WetTextures:
    """Makes (once each) the wet copy of a vanilla texture and its set."""

    def __init__(self, vanilla: Path, out: Path):
        self.vanilla, self.out = vanilla, out
        self.done: dict[str, bool] = {}

    def make(self, path: str) -> bool:
        if path in self.done:
            return self.done[path]
        ok = self._make(path)
        self.done[path] = ok
        return ok

    def _make(self, path: str) -> bool:
        src = find_image(self.vanilla / path)
        if src is None:
            return False
        name = Path(path).name
        dest_dir = self.out / Path(path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        wet_name = name + SUFFIX

        img = Image.open(src).convert("RGBA")
        rgba = np.array(img)
        rgba[..., :3] = np.round(rgba[..., :3] * WET_DARKEN).astype(np.uint8)
        fmt = "TGA" if src.suffix == ".tga" else "PNG"
        Image.fromarray(rgba, "RGBA").save(dest_dir / (wet_name + src.suffix), format=fmt)

        new_set: dict = {"color": wet_name}
        ts_path = src.with_name(name + ".texture_set.json")
        dry = None
        if ts_path.is_file():
            dry = load_json(ts_path).get("minecraft:texture_set", {})
        mers_key = None
        if dry:
            mers_key = next((k for k in ("metalness_emissive_roughness_subsurface",
                                         "metalness_emissive_roughness") if k in dry), None)
        if dry and mers_key:
            value = dry[mers_key]
            if isinstance(value, str) and not value.startswith("#"):
                mers_src = find_image(src.parent / value)
                if mers_src is not None:
                    mers = np.array(Image.open(mers_src).convert("RGBA")).astype(np.float64)
                    if mers.shape[:2] != rgba.shape[:2]:
                        mers = np.array(Image.open(mers_src).convert("RGBA").resize(
                            (rgba.shape[1], rgba.shape[0]), Image.NEAREST)).astype(np.float64)
                    if mers_key == "metalness_emissive_roughness":
                        mers[..., 3] = 0
                    mers[..., 2] *= WET_ROUGHNESS
                    Image.fromarray(np.uint8(np.round(mers)), "RGBA").save(
                        dest_dir / f"{wet_name}_mers.png")
                    new_set["metalness_emissive_roughness_subsurface"] = f"{wet_name}_mers"
            else:
                new_set[mers_key] = scale_roughness(value, WET_ROUGHNESS)
            for key in ("normal", "heightmap"):
                ref = dry.get(key)
                if isinstance(ref, str) and not ref.startswith("#"):
                    img_ref = find_image(src.parent / ref)
                    if img_ref is not None:
                        target = dest_dir / img_ref.name
                        if not target.exists():
                            target.write_bytes(img_ref.read_bytes())
                        new_set[key] = ref
        if "metalness_emissive_roughness_subsurface" not in new_set and \
                "metalness_emissive_roughness" not in new_set:
            new_set["metalness_emissive_roughness_subsurface"] = scale_roughness(
                DRY_DEFAULT_MERS, WET_ROUGHNESS)
        (dest_dir / f"{wet_name}.texture_set.json").write_text(json.dumps(
            {"format_version": "1.21.30", "minecraft:texture_set": new_set}, indent=2) + "\n")
        return True


def build(vanilla: Path, out: Path) -> dict[str, int]:
    """Writes entity/, render_controllers/ and the wet textures into out."""
    controllers: dict[str, tuple[dict, str]] = {}
    for p in sorted((vanilla / "render_controllers").glob("*.json")):
        doc = load_json(p)
        for name, ctrl in doc.get("render_controllers", {}).items():
            controllers[name] = (ctrl, doc.get("format_version", "1.8.0"))

    textures = WetTextures(vanilla, out)
    wet_ctrls: dict[str, tuple[dict, str]] = {}
    counts = {"entities": 0, "controllers": 0, "textures": 0, "skipped": 0}
    (out / "entity").mkdir(parents=True, exist_ok=True)

    for p in sorted((vanilla / "entity").glob("*.json")):
        doc = load_json(p)
        desc = doc.get("minecraft:client_entity", {}).get("description", {})
        tex_map = desc.get("textures")
        if desc.get("identifier") in SKIP or not isinstance(tex_map, dict) or not tex_map:
            counts["skipped"] += 1
            continue

        new_rcs, changed = [], False
        for entry in desc.get("render_controllers", []):
            name = entry if isinstance(entry, str) else next(iter(entry))
            found = controllers.get(name)
            wet = wet_controller(found[0]) if found else None
            if wet is None:
                new_rcs.append(entry)
                continue
            wet_ctrls.setdefault(name + CONTROLLER_SUFFIX, (wet, found[1]))
            new_rcs.append(name + CONTROLLER_SUFFIX if isinstance(entry, str)
                           else {name + CONTROLLER_SUFFIX: entry[name]})
            changed = True
        if not changed:
            counts["skipped"] += 1
            continue

        new_tex = dict(tex_map)
        for key, path in tex_map.items():
            if not isinstance(path, str):
                continue
            # A texture without an image here (generated, or the skin) stays
            # dry in the wet branch rather than going missing.
            new_tex[key + SUFFIX] = path + SUFFIX if textures.make(path) else path
        # Every texture the dry branch can name has a _wet twin now; a key the
        # entity never had is missing in both branches, exactly as before.
        for name in new_rcs:
            name = name if isinstance(name, str) else next(iter(name))
            if name in wet_ctrls:
                have = {k.lower() for k in new_tex}
                dry_keys = {r for r in required_textures(controllers[name[:-len(CONTROLLER_SUFFIX)]][0])
                            if r in have}
                missing = {r + SUFFIX for r in dry_keys} - have
                if missing:
                    raise SystemExit(f"{p.name}: {name} would miss {sorted(missing)}")
        new_doc = copy.deepcopy(doc)
        new_desc = new_doc["minecraft:client_entity"]["description"]
        new_desc["textures"] = new_tex
        new_desc["render_controllers"] = new_rcs
        (out / "entity" / p.name).write_text(json.dumps(new_doc, indent=2, ensure_ascii=False) + "\n",
                                             encoding="utf-8")
        counts["entities"] += 1

    by_format: dict[str, dict] = {}
    for name, (ctrl, fmt) in wet_ctrls.items():
        by_format.setdefault(fmt, {})[name] = ctrl
    (out / "render_controllers").mkdir(parents=True, exist_ok=True)
    for fmt, ctrls in by_format.items():
        (out / "render_controllers" / f"vyse_wet_{fmt.replace('.', '_')}.render_controllers.json").write_text(
            json.dumps({"format_version": fmt, "render_controllers": ctrls}, indent=2) + "\n")
    counts["controllers"] = len(wet_ctrls)
    counts["textures"] = sum(textures.done.values())
    return counts
