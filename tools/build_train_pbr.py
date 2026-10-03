#!/usr/bin/env python3
"""Build a Vibrant Visuals PBR pack for an MTC train add-on.

    tools/build_train_pbr.py <add-on .mcaddon/.mcpack/.zip or folder>
                             [--out build/train_pbr] [--preview <dir>] [--patch N]

Vibrant Visuals gives an entity texture its material - metal, gloss, glow -
through a texture set next to the texture. Train add-ons rarely ship one, so
every part of a car, from the stainless body to the seat moquette, renders
as the same flat material. This tool works out what each pixel of the
train's texture is and writes the texture set for it:

1. Match the model to the texture. Every cube face of every geometry drawn
   with the texture has a UV rectangle; painting them all onto the texture
   says which bones - which parts of the train - use each pixel. Parts that
   share a pixel are settled by priority, the specific part winning over
   the car body.
2. Name the parts. MTC trains (and the TBTK template they are often built
   from) use romanised Japanese bone names - tsurikawa (straps), nidana
   (luggage racks), sodesikiri (seat-end partitions), yukasita (underfloor),
   maku (destination signs), lcd, mascon (master controller), panta... -
   which PARTS maps to materials. The car body splits by face direction and
   by the texture's alpha, which MTC trains use as a code: 255 for the
   outside, 127 for the inside (half self-lit by the add-on's material),
   lower for light fittings, 0 for open window cut-outs.
3. Refine by colour: grey on the outside is stainless steel, saturated
   colour is a livery stripe, black is a gasket or a glossy front window,
   and so on (material()).

The look aimed for is a clean, RTX-style render: soft diffuse shading, a
subtle sheen, glossy glass and screens, lit displays and light fittings,
no exaggerated reflections and no bump mapping (models are hard surfaces).

The result is a separate resource pack to place ABOVE the add-on; the add-on
itself is not modified. It carries a copy of each colour texture, since a
texture set must sit in the same pack as its images - so it is for personal
use, like the add-on it is made from. The copy has the same colours; only
the add-on's alpha-coded self-lighting of the interior is taken out, since
it washes the cabin flat white in Vibrant Visuals (--keep-glow keeps it).
Textures that already have a texture set in the add-on are left alone.
"""

from __future__ import annotations

import argparse
import fnmatch
import io
import json
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Parts: bone name patterns -> part, most specific first. A face belongs to
# the first part any bone on its path (the bone itself, then its parents)
# matches.
# --------------------------------------------------------------------------

PARTS = [
    # Lights and screens
    (["headlight*", "light", "nolight", "hi[0-9]*", "exp*", "tail*"], "headlight"),
    (["doorlamp*", "sokuto*"], "lamp"),
    (["thxbdg*", "kyuteisya*", "kou[0-9]*", "lcd_*"], "screen"),
    (["notch", "n", "b[0-9]", "p[0-9]", "mater*", "master*"], "screen"),
    (["maku", "sy*", "retsu*", "[rlf][0-9]*"], "sign"),
    (["hari*"], "needle"),
    (["display*"], "cab_panel"),
    # Interior fittings
    (["turikawa*"], "strap"),
    (["tsurikawa", "nidana*", "sodesikiri*", "tesuri*", "handrail*"], "fitting"),
    (["bottom17", "seat*", "zaseki*"], "seat"),
    (["lcd"], "lcd_frame"),
    (["mascon", "body", "botan*", "tohei*", "totte*", "rev*", "mascon*"], "cab_control"),
    (["jyoumuin", "lclose", "lopen", "ropen", "rclose"], "cab_control"),
    (["bottom14"], "interior"),
    # Outside
    (["wiper*"], "wiper"),
    (["panta*", "bou*", "suriita*", "daiza*"], "pantograph"),
    (["mtc_dh*", "mtc_db*", "daisya*", "bogie*"], "bogie"),
    (["renketsuki*", "denren*", "douuke*", "coupler*"], "coupler"),
    (["skirt*", "sasae*"], "skirt"),
    (["madowaku*"], "window_frame"),
    (["rogo*", "logo*"], "sticker"),
    (["kao*", "*face"], "front"),
    (["yukasita*", "bottom4", "bottom6", "bottom10"], "equipment"),
    (["door", "left", "right"], "door"),
]
# Names that say nothing about the part (Blockbench defaults, rig roots):
# skipped, so the part comes from the parent - a door leaf named "bone3"
# is a door because its parent is "right".
GENERIC = ["bone", "bone[0-9]*", "group", "group[0-9]*", "root", "main", "mtc_body", "proto_*"]
# Faces no rule claims are the car body; which part of it depends on the
# face direction and the alpha code.
BODY = "body"

# Priority when parts share a pixel: later wins.
PRIORITY = [BODY, "equipment", "interior", "door", "front", "skirt", "window_frame",
            "coupler", "bogie", "pantograph", "wiper", "cab_control", "lcd_frame", "seat",
            "fitting", "strap", "sticker", "cab_panel", "needle", "sign", "screen", "lamp",
            "headlight"]

# --------------------------------------------------------------------------
# Materials: (metalness, emissive, roughness) in 0..1
# --------------------------------------------------------------------------

# Kept soft. Fully metallic stainless (first version) has no diffuse light
# at all, so by day the body only mirrored the ground and sky and turned
# grey, and polished seat-end partitions glittered. Train bodies, fittings
# and frames are mostly diffuse here with a metallic sheen on top, and
# nothing is smoother than about 0.4 except glass and screens.
STAINLESS = (0.12, 0.0, 0.48)       # brushed stainless body and doors
POLISHED = (0.15, 0.0, 0.42)        # poles, racks, partitions (they share one swatch)
SATIN_METAL = (0.30, 0.0, 0.50)     # aluminium window frames, rack mesh, pantograph
FILM = (0.0, 0.0, 0.45)             # livery stripes: printed film on the body
GASKET = (0.0, 0.0, 0.65)           # black rubber
GLOSS_BLACK = (0.0, 0.0, 0.18)      # front window glass and black front mask
PAINT = (0.0, 0.0, 0.50)            # painted FRP, painted panels
DARK_PAINT = (0.0, 0.0, 0.65)       # underfloor boxes, bogie frames
LAMINATE = (0.0, 0.0, 0.50)         # interior walls: melamine laminate
CEILING = (0.0, 0.0, 0.60)
FLOOR = (0.0, 0.0, 0.75)            # rubber / vinyl flooring
ROOF = (0.0, 0.0, 0.80)             # roof coating
MOQUETTE = (0.0, 0.0, 0.92)         # seat fabric
PLASTIC = (0.0, 0.0, 0.40)          # straps
CONSOLE = (0.0, 0.0, 0.60)          # cab desk, switches
STICKER = (0.0, 0.0, 0.45)
SCREEN = 0.15                       # roughness of LCDs, signs, lamp lenses

# Self-light. The add-on half self-lights every surface inside the car (its
# material reads alpha 127 as glow), which in Vibrant Visuals washes the
# cabin flat white. The copy of the texture in this pack is made opaque
# there (see opaque_copy()), so only the map below glows: a faint fill,
# which still reads as a lit car at night but leaves the shading to the
# light, and the light fittings themselves - like real fluorescent tubes.
FILL = 0.07
FLOOR_FILL = 0.05
LIGHT_GLOW = 0.90
SCREEN_GLOW = 0.62
SIGN_GLOW = 0.70
LAMP_GLOW = 0.85


def opaque_copy(data: bytes, fmt: str) -> bytes:
    """The colour texture with MTC's glow code taken out of its alpha:
    alpha 30-254 (interior 127, light fittings 83, glowing signs) becomes
    255. Alpha 0 - window cut-outs - and the faint 1-29 halo pixels are
    kept. Colours are untouched."""
    img = Image.open(io.BytesIO(data))
    rgba = np.array(img.convert("RGBA"))
    a = rgba[..., 3]
    a[(a >= 30) & (a < 255)] = 255
    out = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(out, format=fmt)
    return out.getvalue()


def classify(name_path: tuple[str, ...]) -> str:
    for name in name_path:
        low = name.lower()
        if any(fnmatch.fnmatchcase(low, g) for g in GENERIC):
            continue
        for patterns, part in PARTS:
            if any(fnmatch.fnmatchcase(low, p) for p in patterns):
                return part
    return BODY


# --------------------------------------------------------------------------
# Reading the add-on
# --------------------------------------------------------------------------

def load_json(data: bytes):
    text = data.decode("utf-8-sig")
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return json.loads(text)


class Source:
    """The add-on, zipped or unpacked."""

    def __init__(self, path: Path):
        self.files: dict[str, bytes] = {}
        if path.is_dir():
            for p in path.rglob("*"):
                if p.is_file():
                    self.files[p.relative_to(path).as_posix()] = p.read_bytes()
        else:
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    if not info.is_dir():
                        self.files[info.filename] = z.read(info)

    def resource_packs(self) -> list[str]:
        roots = []
        for name, data in self.files.items():
            if name.endswith("manifest.json"):
                try:
                    manifest = load_json(data)
                except ValueError:
                    continue
                if any(m.get("type") == "resources" for m in manifest.get("modules", [])):
                    roots.append(name[: -len("manifest.json")])
        return roots


def geometries(src: Source, root: str) -> dict[str, dict]:
    out = {}
    for name, data in src.files.items():
        if not (name.startswith(root) and name.endswith(".json") and "/models/" in name):
            continue
        try:
            doc = load_json(data)
        except ValueError:
            continue
        for geo in doc.get("minecraft:geometry", []):
            out[geo["description"]["identifier"]] = geo
        for key, geo in doc.items():                      # legacy format
            if key.startswith("geometry.") and isinstance(geo, dict):
                desc = {"identifier": key.split(":")[0],
                        "texture_width": geo.get("texturewidth", 64),
                        "texture_height": geo.get("textureheight", 64)}
                out[desc["identifier"]] = {"description": desc, "bones": geo.get("bones", [])}
    return out


def texture_geometries(src: Source, root: str) -> dict[str, set[str]]:
    """Texture path -> geometry identifiers drawn with it."""
    pairs: dict[str, set[str]] = {}
    for name, data in src.files.items():
        if not (name.startswith(root) and "/entity/" in name and name.endswith(".json")):
            continue
        try:
            desc = load_json(data)["minecraft:client_entity"]["description"]
        except (ValueError, KeyError, TypeError):
            continue
        textures, geos = desc.get("textures", {}), desc.get("geometry", {})
        for key, tex in textures.items():
            match = [geos[key]] if key in geos else list(geos.values())
            pairs.setdefault(tex, set()).update(match)
    return pairs


def faces(geo: dict, width: int, height: int):
    """(bone path leaf first, face direction, x0, y0, x1, y1) in image pixels."""
    desc = geo["description"]
    sx = width / desc.get("texture_width", width)
    sy = height / desc.get("texture_height", height)
    bones = {b["name"]: b for b in geo.get("bones", [])}

    def path(name):
        out = []
        while name and name not in out:
            out.append(name)
            name = bones.get(name, {}).get("parent")
        return tuple(out)

    for bone in geo.get("bones", []):
        bpath = path(bone["name"])
        for cube in bone.get("cubes", []):
            uv = cube.get("uv")
            if isinstance(uv, list):                      # box UV
                w, h, d = (abs(v) for v in cube.get("size", (0, 0, 0)))
                u, v = uv
                rects = {"east": (u, v + d, d, h), "north": (u + d, v + d, w, h),
                         "west": (u + d + w, v + d, d, h), "south": (u + 2 * d + w, v + d, w, h),
                         "up": (u + d, v, w, d), "down": (u + d + w, v, w, d)}
            elif isinstance(uv, dict):
                rects = {k: (*f["uv"], *f["uv_size"]) for k, f in uv.items()
                         if isinstance(f, dict) and "uv" in f and "uv_size" in f}
            else:
                continue
            for direction, (u, v, w, h) in rects.items():
                x0, x1 = sorted((u * sx, (u + w) * sx))
                y0, y1 = sorted((v * sy, (v + h) * sy))
                X0, X1 = int(np.floor(x0)), max(int(np.ceil(x1)), int(np.floor(x0)) + 1)
                Y0, Y1 = int(np.floor(y0)), max(int(np.ceil(y1)), int(np.floor(y0)) + 1)
                X0, Y0 = max(X0, 0), max(Y0, 0)
                X1, Y1 = min(X1, width), min(Y1, height)
                if X1 > X0 and Y1 > Y0:
                    yield bpath, direction, X0, Y0, X1, Y1


# --------------------------------------------------------------------------
# Labels and materials
# --------------------------------------------------------------------------

LABELS = PRIORITY + ["body_up", "body_down"]


def label_map(geos: list[dict], width: int, height: int) -> np.ndarray:
    """Per pixel, the part using it (index into LABELS; -1 unused)."""
    rank = {p: i for i, p in enumerate(PRIORITY)}
    jobs = []
    for geo in geos:
        for bpath, direction, x0, y0, x1, y1 in faces(geo, width, height):
            part = classify(bpath)
            label = part
            if part == BODY and direction in ("up", "down"):
                label = f"body_{direction}"
            jobs.append((rank[part], LABELS.index(label), x0, y0, x1, y1))
    labels = np.full((height, width), -1, np.int16)
    for _, label, x0, y0, x1, y1 in sorted(jobs):
        labels[y0:y1, x0:x1] = label
    return labels


def material(labels: np.ndarray, rgba: np.ndarray) -> np.ndarray:
    """MERS image (0..255) for one texture."""
    rgb = rgba[..., :3].astype(np.float64) / 255.0
    alpha = rgba[..., 3]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    sat = (rgb.max(-1) - rgb.min(-1)) / np.maximum(rgb.max(-1), 1e-6)
    inside = (alpha > 100) & (alpha < 250)        # MTC: 127 = interior
    fitting = (alpha > 0) & (alpha <= 100)        # MTC: lower = light fittings
    grey = sat < 0.12
    dark = lum < 0.12

    m = np.zeros(labels.shape + (3,))
    m[:] = PAINT

    def put(mask, mat):
        m[mask] = mat

    def is_(name):
        return labels == LABELS.index(name)

    # Car body: by face direction, inside or outside, then colour.
    side = is_(BODY)
    put(side & ~inside, PAINT)
    put(side & ~inside & grey & (lum > 0.30), STAINLESS)
    put(side & ~inside & (sat > 0.25), FILM)
    put(side & ~inside & dark, GASKET)
    put(side & inside, LAMINATE)
    up, down = is_("body_up"), is_("body_down")
    put(up & ~inside, ROOF)
    put(up & inside, FLOOR)
    put(down & ~inside, DARK_PAINT)
    put(down & inside, CEILING)

    door = is_("door")
    put(door, STAINLESS)
    put(door & (sat > 0.25), FILM)                # door-edge warning line, stripes
    put(door & dark, GASKET)
    put(door & ~grey & (lum < 0.30), PAINT)

    front = is_("front")
    put(front, PAINT)
    put(front & grey & (lum > 0.30), STAINLESS)
    put(front & (lum < 0.18), GLOSS_BLACK)
    put(is_("window_frame"), SATIN_METAL)
    put(is_("skirt"), PAINT)
    put(is_("sticker"), STICKER)
    put(is_("wiper"), GASKET)
    put(is_("pantograph"), SATIN_METAL)
    put(is_("coupler"), DARK_PAINT)
    put(is_("bogie"), DARK_PAINT)
    eq = is_("equipment")
    put(eq, DARK_PAINT)
    put(eq & (lum > 0.45), PAINT)                 # roof air conditioners, light covers

    put(is_("interior"), LAMINATE)
    put(is_("lcd_frame"), LAMINATE)
    fit = is_("fitting")
    put(fit, POLISHED)
    put(fit & (lum < 0.70), SATIN_METAL)
    put(fit & (lum < 0.15), GASKET)
    put(fit & ~grey, PAINT)
    put(is_("strap"), PLASTIC)
    put(is_("seat"), MOQUETTE)
    put(is_("seat") & grey & (lum > 0.3), SATIN_METAL)   # seat frames
    put(is_("cab_control"), CONSOLE)
    put(is_("cab_panel"), CONSOLE)

    for name, glow in (("screen", SCREEN_GLOW), ("sign", SIGN_GLOW), ("needle", 0.35),
                       ("lamp", LAMP_GLOW), ("headlight", LAMP_GLOW)):
        mask = is_(name)
        put(mask, (0.0, glow, SCREEN))
    # Cab instruments: lamps and lit markings glow, the desk does not.
    panel = is_("cab_panel")
    lit = panel & (((sat > 0.35) & (lum > 0.25)) | (lum > 0.70))
    put(lit, (0.0, 0.55, 0.15))

    # Fill light inside the car, and the light fittings.
    surfaces = inside & (m[..., 1] == 0)
    m[surfaces, 1] = FILL
    m[surfaces & (up | is_("seat")), 1] = FLOOR_FILL
    m[fitting & (m[..., 1] < LIGHT_GLOW) & (labels >= 0), 1] = LIGHT_GLOW
    m[fitting & (labels >= 0), 2] = SCREEN

    out = np.zeros(labels.shape + (4,), np.uint8)
    out[..., :3] = np.uint8(np.round(np.clip(m, 0, 1) * 255))
    out[labels < 0] = (0, 0, 255, 0)              # unused pixels
    return out


# --------------------------------------------------------------------------
# Preview: the texture tinted by material, for checking the guesses
# --------------------------------------------------------------------------

PART_COLOURS = {
    BODY: (70, 130, 255), "body_up": (150, 150, 60), "body_down": (255, 140, 200),
    "door": (40, 200, 255), "front": (0, 120, 180), "window_frame": (170, 200, 255),
    "skirt": (90, 90, 160), "sticker": (255, 255, 255), "wiper": (60, 60, 60),
    "pantograph": (200, 220, 240), "coupler": (150, 90, 40), "bogie": (120, 70, 30),
    "equipment": (180, 120, 60), "interior": (140, 230, 140), "lcd_frame": (90, 200, 120),
    "fitting": (230, 230, 230), "strap": (190, 80, 255), "seat": (0, 190, 170),
    "cab_control": (120, 160, 120), "cab_panel": (60, 140, 90), "needle": (255, 200, 120),
    "sign": (255, 140, 0), "screen": (255, 220, 0), "lamp": (255, 60, 40),
    "headlight": (255, 255, 120),
}


def with_legend(image: np.ndarray, entries: list[tuple[str, tuple[int, int, int]]]) -> Image.Image:
    from PIL import ImageDraw, ImageFont
    font = ImageFont.load_default(size=max(14, image.shape[1] // 160))
    line = font.size + 12
    cols = 6
    rows = -(-len(entries) // cols)
    out = Image.new("RGB", (image.shape[1], image.shape[0] + line * rows + 12), (16, 16, 16))
    out.paste(Image.fromarray(image), (0, 0))
    draw = ImageDraw.Draw(out)
    step = image.shape[1] // cols
    for i, (text, colour) in enumerate(entries):
        x, y = (i % cols) * step + 12, image.shape[0] + 10 + (i // cols) * line
        draw.rectangle([x, y, x + font.size, y + font.size], fill=colour)
        draw.text((x + font.size + 10, y), text, fill=(235, 235, 235), font=font)
    return out


def parts_preview(rgba: np.ndarray, labels: np.ndarray) -> Image.Image:
    """The texture tinted by the part each pixel was matched to."""
    base = rgba[..., :3].astype(np.float64)
    out = base * 0.25
    present = []
    for i, name in enumerate(LABELS):
        mask = labels == i
        if mask.any():
            colour = PART_COLOURS[name]
            out[mask] = 0.35 * base[mask] + 0.65 * np.array(colour)
            present.append((name, colour))
    return with_legend(np.uint8(np.clip(out, 0, 255)), present)


def material_preview(rgba: np.ndarray, mers: np.ndarray) -> Image.Image:
    """Red = glow, green = smoothness, blue = metal."""
    base = rgba[..., :3].astype(np.float64)
    tint = np.zeros_like(base)
    metal, glow, rough = (mers[..., i] / 255.0 for i in range(3))
    tint[..., 0] = 255 * glow
    tint[..., 1] = 255 * (1 - rough)
    tint[..., 2] = 255 * metal
    out = 0.35 * base + 0.65 * tint
    out[rgba[..., 3] == 0] *= 0.25
    return with_legend(np.uint8(np.clip(out, 0, 255)),
                       [("glow", (255, 0, 0)), ("smooth", (0, 255, 0)), ("metal", (0, 0, 255))])


# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("addon", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "build/train_pbr")
    parser.add_argument("--preview", type=Path, help="also write material previews here")
    parser.add_argument("--patch", type=int, default=0, help="patch number of the pack version")
    parser.add_argument("--keep-glow", action="store_true",
                        help="copy the colour textures unchanged, keeping the add-on's own "
                             "alpha-coded self-lighting of the interior")
    args = parser.parse_args()

    src = Source(args.addon)
    roots = src.resource_packs()
    if not roots:
        print(f"{args.addon}: no resource pack found")
        return 1
    if args.out.exists():
        shutil.rmtree(args.out)
    (args.out / "textures").mkdir(parents=True)

    names = []
    for root in roots:
        manifest = load_json(src.files[root + "manifest.json"])
        names.append(manifest["header"].get("name", "add-on"))
        geos = geometries(src, root)
        for tex, geo_ids in sorted(texture_geometries(src, root).items()):
            image_name = next((root + tex + ext for ext in (".png", ".tga")
                               if root + tex + ext in src.files), None)
            if image_name is None:
                continue
            if root + tex + ".texture_set.json" in src.files:
                print(f"{tex}: the add-on has its own texture set - left alone")
                continue
            used = [geos[g] for g in sorted(geo_ids) if g in geos]
            if not used:
                continue
            img = Image.open(io.BytesIO(src.files[image_name])).convert("RGBA")
            rgba = np.asarray(img)
            labels = label_map(used, img.width, img.height)
            mers = material(labels, rgba)

            dest = args.out / Path(tex).parent
            dest.mkdir(parents=True, exist_ok=True)
            stem = Path(tex).name
            colour = src.files[image_name]
            if not args.keep_glow:
                colour = opaque_copy(colour, "TGA" if image_name.endswith(".tga") else "PNG")
            (dest / Path(image_name).name).write_bytes(colour)
            Image.fromarray(mers, "RGBA").save(dest / f"{stem}_vu_mers.png", optimize=True)
            (dest / f"{stem}.texture_set.json").write_text(json.dumps({
                "format_version": "1.21.30",
                "minecraft:texture_set": {
                    "color": stem,
                    "metalness_emissive_roughness_subsurface": f"{stem}_vu_mers",
                }}, indent=2) + "\n")
            counts = {LABELS[i]: int((labels == i).sum()) for i in range(len(LABELS))}
            top = ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
                            if v)
            print(f"{tex}: {len(used)} geometries; pixels by part: {top}")
            if args.preview:
                args.preview.mkdir(parents=True, exist_ok=True)
                material_preview(rgba, mers).save(args.preview / f"{stem}_materials.png")
                parts_preview(rgba, labels).save(args.preview / f"{stem}_parts.png")

    name = " / ".join(names)
    seed = uuid.uuid5(uuid.NAMESPACE_URL, "vyse-train-pbr:" + name)
    version = [1, 0, args.patch]
    manifest = {
        "format_version": 2,
        "header": {
            "name": f"VYSE PBR - {name}",
            "description": "Vibrant Visuals materials for this train: stainless body, glossy "
                           "front, lit screens, signs and light fittings, satin interior. "
                           "Place above the train add-on. Personal use only.",
            "uuid": str(uuid.uuid5(seed, "header")),
            "version": version,
            "min_engine_version": [1, 21, 120],
        },
        "modules": [{"type": "resources", "uuid": str(uuid.uuid5(seed, "module")),
                     "version": version}],
        "capabilities": ["pbr"],
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)
                                            + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "branding/pbr_pack_icon.png", args.out / "pack_icon.png")
    print(f"{args.out}: {manifest['header']['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
