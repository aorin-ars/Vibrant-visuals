#!/usr/bin/env python3
"""Validate a Bedrock Vibrant Visuals resource pack.

    tools/check_bedrock.py [pack-directory] [--vanilla <bedrock-samples>/resource_pack]

    (default pack: bedrock)

Bedrock fails quietly: a mistyped key, a keyframe that is not a number, a
value out of range or a texture set pointing at a missing image produces no
error in game - that setting just stays vanilla, or the whole file is
dropped. This checks what the game will not tell you about.

Schemas and ranges are Mojang's (learn.microsoft.com/minecraft/creator,
Vibrant Visuals section, and the vanilla pack in github.com/Mojang/bedrock-samples).

With --vanilla it also checks that every lighting / atmosphere / colour
grading / water identifier the vanilla biomes use is overridden (since
1.21.90 those take precedence over the global files, so one left out is a
biome the pack silently does not reach), and that local_lighting only names
real block ids.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

from PIL import Image

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Top-level settings key per folder, and whether a description.identifier is
# expected. The global file names are reserved by the engine.
SETTINGS = {
    "lighting": ("minecraft:lighting_settings", True),
    "atmospherics": ("minecraft:atmosphere_settings", True),
    "color_grading": ("minecraft:color_grading_settings", True),
    "water": ("minecraft:water_settings", True),
    "fogs": ("minecraft:fog_settings", True),
    "cubemaps": ("minecraft:cubemap_settings", True),
    "local_lighting": ("minecraft:local_light_settings", False),
    "shadows": ("minecraft:shadow_settings", False),
    "pbr": ("minecraft:pbr_fallback_settings", False),
}
GLOBAL_FILES = {
    "lighting/global.json": "minecraft:default_lighting",
    "atmospherics/atmospherics.json": "minecraft:default_atmospherics",
    "color_grading/color_grading.json": "minecraft:default_color_grading",
    "water/water.json": "minecraft:default_water",
}

# Key names the engine reads. A key outside these is not an error to the
# game - it is silently ignored, which is exactly why a typo is worth
# catching. None means "free-form below here" (keyframe maps, colours, block
# ids); the values there are checked separately.
GRADE_BLOCK = {"contrast": None, "gain": None, "gamma": None, "offset": None, "saturation": None}
ALLOWED = {
    "lighting": {
        "description": {"identifier": None},
        "directional_lights": {
            "orbital": {
                "sun": {"illuminance": None, "color": None},
                "moon": {"illuminance": None, "color": None},
                "orbital_offset_degrees": None,
            },
            "flash": {"illuminance": None, "color": None},
            # Pre-1.21.80 layout, still used by some vanilla biome files.
            "sun": {"illuminance": None, "color": None},
            "moon": {"illuminance": None, "color": None},
        },
        "emissive": {"desaturation": None},
        "ambient": {"color": None, "illuminance": None},
        "sky": {"intensity": None},
    },
    "atmospherics": {
        "description": {"identifier": None},
        "horizon_blend_stops": {"min": None, "start": None, "mie_start": None, "max": None},
        "rayleigh_strength": None, "sun_mie_strength": None, "moon_mie_strength": None,
        "sun_glare_shape": None, "sky_zenith_color": None, "sky_horizon_color": None,
    },
    "color_grading": {
        "description": {"identifier": None},
        "color_grading": {
            "midtones": GRADE_BLOCK,
            "shadows": {"enabled": None, "shadowsMax": None, **GRADE_BLOCK},
            "highlights": {"enabled": None, "highlightsMin": None, **GRADE_BLOCK},
            "temperature": {"enabled": None, "temperature": None, "type": None},
        },
        "tone_mapping": {"operator": None},
    },
    "water": {
        "description": {"identifier": None},
        "particle_concentrations": {"chlorophyll": None, "suspended_sediment": None, "cdom": None},
        "caustics": {"enabled": None, "frame_length": None, "scale": None, "power": None,
                     "texture": None},
        "waves": {"enabled": None, "depth": None, "direction_increment": None, "frequency": None,
                  "frequency_scaling": None, "mix": None, "octaves": None, "pull": None,
                  "sampleWidth": None, "shape": None, "speed": None, "speed_scaling": None},
        "biome_water_color_contribution": None,
    },
    "fogs": {
        "description": {"identifier": None},
        "distance": None,
        "volumetric": {
            "density": {k: {"max_density": None, "uniform": None, "zero_density_height": None,
                            "max_density_height": None}
                        for k in ("air", "weather", "water", "lava", "lava_resistance")},
            "media_coefficients": {k: {"scattering": None, "absorption": None}
                                   for k in ("air", "water", "cloud")},
            "henyey_greenstein_g": {k: {"henyey_greenstein_g": None} for k in ("air", "water")},
        },
    },
    "cubemaps": {
        "description": {"identifier": None},
        "lighting": {"ambient_light_illuminance": None, "sky_light_contribution": None,
                     "directional_light_contribution": None,
                     "affected_by_atmospheric_scattering": None,
                     "affected_by_volumetric_scattering": None},
    },
    "local_lighting": None,
    "shadows": {"shadow_style": None, "texel_size": None},
    "pbr": {k: {"global_metalness_emissive_roughness_subsurface": None}
            for k in ("blocks", "actors", "items", "particles")},
}

TONE_MAPS = {"reinhard", "reinhard_luma", "reinhard_luminance", "hable", "aces", "generic"}
SHADOW_STYLES = {"soft_shadows", "blocky_shadows"}
LIGHT_TYPES = {"static_light", "point_light"}

# Textures the pack replaces, with the layout vanilla uses. The sun and moon
# quads map UVs to the whole image, so only the aspect ratio has to match.
ENVIRONMENT_TEXTURES = {
    "textures/environment/sun_vv.png": ("RGBA", 1.0),
    "textures/environment/sun.png": (None, 1.0),
    "textures/environment/moon_phases.png": (None, 2.0),
}


SKY_FACES = [f"textures/environment/overworld_cubemap/cubemap_{i}.png" for i in range(6)]


class Checker:
    """Checks one effective pack: the base pack, or the base pack with one
    subpack laid over it (a subpack's files replace the base's at the same
    path, which is how the game applies them)."""

    def __init__(self, pack: Path, subpack: str | None = None):
        self.pack = pack
        self.overlay = pack / "subpacks" / subpack if subpack else None
        self.problems: list[str] = []
        self.notes: list[str] = []
        self.min_engine: tuple[int, ...] = (0, 0, 0)

    def fail(self, msg: str) -> None:
        self.problems.append(msg)

    # -- file layering ----------------------------------------------------------

    def resolve(self, rel: str) -> Path | None:
        for base in ([self.overlay] if self.overlay else []) + [self.pack]:
            if (base / rel).is_file():
                return base / rel
        return None

    def layered(self, folder: str, pattern: str) -> list[Path]:
        found = {p.name: p for p in (self.pack / folder).glob(pattern)}
        if self.overlay:
            found.update({p.name: p for p in (self.overlay / folder).glob(pattern)})
        return sorted(found.values())

    def layered_rglob(self, pattern: str) -> list[Path]:
        subpacks = self.pack / "subpacks"
        found = {p.relative_to(self.pack).as_posix(): p for p in self.pack.rglob(pattern)
                 if subpacks not in p.parents}
        if self.overlay:
            found.update({p.relative_to(self.overlay).as_posix(): p
                          for p in self.overlay.rglob(pattern)})
        return sorted(found.values())

    # -- value helpers ----------------------------------------------------

    def color(self, where: str, value) -> None:
        if isinstance(value, str):
            if not HEX.match(value):
                self.fail(f"{where}: colour {value!r} is not #RRGGBB")
        elif isinstance(value, list) and len(value) == 3 and all(
                isinstance(c, (int, float)) and not isinstance(c, bool) for c in value):
            if not all(0 <= c <= 255 for c in value):
                self.fail(f"{where}: colour channel outside 0..255: {value}")
        else:
            self.fail(f"{where}: expected [r, g, b] or #RRGGBB, got {value!r}")

    def number(self, where: str, value, lo=None, hi=None) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            self.fail(f"{where}: expected a number, got {value!r}")
        elif (lo is not None and value < lo) or (hi is not None and value > hi):
            self.fail(f"{where}: {value} is outside {lo}..{hi}")

    def keyframed(self, where: str, value, kind: str, lo=None, hi=None,
                  keyframes_from: tuple[int, ...] = (0, 0, 0), fmt=(0, 0, 0)) -> None:
        """A value that may be given directly or as a {time: value} map."""
        if isinstance(value, dict):
            if fmt < keyframes_from:
                self.fail(f"{where}: keyframes here need format_version "
                          f"{'.'.join(map(str, keyframes_from))}")
            if len(value) < 2:
                self.fail(f"{where}: needs at least two keyframes, has {len(value)}")
            for key, v in value.items():
                try:
                    t = float(key)
                except ValueError:
                    self.fail(f"{where}: keyframe key {key!r} is not a number")
                    continue
                if not 0.0 <= t <= 1.0:
                    self.fail(f"{where}: keyframe {key} is outside 0..1")
                self._scalar(f"{where}[{key}]", v, kind, lo, hi)
        else:
            self._scalar(where, value, kind, lo, hi)

    def _scalar(self, where, value, kind, lo, hi):
        if kind == "color":
            self.color(where, value)
        else:
            self.number(where, value, lo, hi)

    def triple(self, where: str, value, lo: float, hi: float) -> None:
        if not (isinstance(value, list) and len(value) == 3):
            self.fail(f"{where}: expected three numbers, got {value!r}")
            return
        for i, v in enumerate(value):
            self.number(f"{where}[{i}]", v, lo, hi)

    def keys(self, data, spec, where: str) -> None:
        if spec is None or not isinstance(data, dict):
            return
        for key, value in data.items():
            if key not in spec:
                self.fail(f"{where}.{key}: not a key the engine reads "
                          f"(expected one of: {', '.join(sorted(spec))})")
                continue
            self.keys(value, spec[key], f"{where}.{key}")

    # -- manifest -----------------------------------------------------------

    def manifest(self) -> None:
        path = self.pack / "manifest.json"
        if not path.is_file():
            self.fail("manifest.json is missing")
            return
        manifest = json.loads(path.read_text())
        if manifest.get("format_version") != 2:
            self.fail("manifest format_version must be 2")
        header = manifest.get("header", {})
        modules = manifest.get("modules", [])

        seen: set[str] = set()
        for label, value in [("header", header.get("uuid"))] + [
                (f"module[{i}]", m.get("uuid")) for i, m in enumerate(modules)]:
            try:
                uuid.UUID(str(value))
            except (ValueError, TypeError):
                self.fail(f"{label} uuid is not a valid UUID: {value!r}")
                continue
            if value in seen:
                self.fail(f"{label} reuses uuid {value} - every uuid must be unique")
            seen.add(value)

        for field in ("name", "description", "version", "min_engine_version"):
            if field not in header:
                self.fail(f"manifest header is missing {field}")
        for field in ("version", "min_engine_version"):
            value = header.get(field)
            if not (isinstance(value, list) and len(value) == 3
                    and all(isinstance(n, int) for n in value)):
                self.fail(f"manifest header {field} must be three integers, got {value!r}")
            elif field == "min_engine_version":
                self.min_engine = tuple(value)
        if not any(m.get("type") == "resources" for m in modules):
            self.fail("manifest has no module of type 'resources'")

        # Without "pbr" the game treats the pack as an ordinary resource pack:
        # textures still apply and every Vibrant Visuals file is ignored.
        # Silent, which makes it the worst one to get wrong.
        if "pbr" not in manifest.get("capabilities", []) and (
                self.settings_files() or list(self.pack.rglob("*.texture_set.json"))):
            self.fail('manifest has no "capabilities": ["pbr"], so every Vibrant Visuals '
                      'file in the pack will be ignored')

        for field in ("name", "description"):
            key = header.get(field)
            if isinstance(key, str) and key.startswith("pack."):
                for lang in sorted((self.pack / "texts").glob("*.lang")):
                    if not any(line.startswith(key + "=")
                               for line in lang.read_text(encoding="utf-8").splitlines()):
                        self.fail(f"{lang.name} has no entry for {key}")

        # Subpacks: every listed folder has to exist (the game cannot apply a
        # missing one), and a folder nobody lists is dead weight in the pack.
        self.subpacks: list[str] = []
        folders = ({p.name for p in (self.pack / "subpacks").iterdir() if p.is_dir()}
                   if (self.pack / "subpacks").is_dir() else set())
        for i, entry in enumerate(manifest.get("subpacks", [])):
            name = entry.get("folder_name") if isinstance(entry, dict) else None
            if not isinstance(name, str) or not name:
                self.fail(f"subpacks[{i}]: folder_name is missing")
                continue
            if name in self.subpacks:
                self.fail(f"subpacks[{i}]: folder {name} is listed twice")
            self.subpacks.append(name)
            if name not in folders:
                self.fail(f"subpacks[{i}]: folder subpacks/{name} does not exist")
            if not isinstance(entry.get("name"), str) or not entry["name"].strip():
                self.fail(f"subpacks[{i}]: name, shown to the player, is missing")
            tier = entry.get("memory_tier", 0)
            if not isinstance(tier, int) or tier < 0:
                self.fail(f"subpacks[{i}]: memory_tier must be a non-negative integer")
        for name in sorted(folders - set(self.subpacks)):
            self.fail(f"subpacks/{name} is not listed in the manifest, so it can never be chosen")

    # -- settings files ---------------------------------------------------------

    def settings_files(self) -> list[Path]:
        return sorted(p for folder in SETTINGS for p in self.layered(folder, "*.json"))

    def settings(self) -> dict[str, dict[str, str]]:
        identifiers: dict[str, dict[str, str]] = {folder: {} for folder in SETTINGS}
        tone_maps: dict[str, str] = {}
        offsets: dict[str, float] = {}

        for path in self.settings_files():
            folder = path.parent.name
            rel = path.relative_to(self.pack).as_posix()
            top, has_id = SETTINGS[folder]
            data = json.loads(path.read_text())
            fmt_text = data.get("format_version")
            try:
                fmt = tuple(int(n) for n in str(fmt_text).split("."))
            except ValueError:
                self.fail(f"{rel}: format_version {fmt_text!r} is not x.y.z")
                continue
            if fmt > self.min_engine:
                # A game older than the file's schema cannot read it. For a
                # pack that declares a Vibrant Visuals era minimum that is a
                # mistake; a pack that deliberately loads on older games (the
                # check pack) only loses the file there.
                msg = (f"{rel}: format_version {fmt_text} is newer than min_engine_version "
                       f"{'.'.join(map(str, self.min_engine))}")
                (self.fail if self.min_engine >= (1, 21, 0) else self.notes.append)(msg)

            if set(data) - {"format_version", top}:
                self.fail(f"{rel}: unexpected top-level keys {sorted(set(data) - {'format_version', top})}")
            body = data.get(top)
            if not isinstance(body, dict):
                self.fail(f"{rel}: expected top-level key {top}")
                continue
            self.keys(body, ALLOWED[folder], f"{rel}:{top}")

            if has_id:
                ident = (body.get("description") or {}).get("identifier")
                if not (isinstance(ident, str) and ":" in ident):
                    self.fail(f"{rel}: identifier {ident!r} must be namespaced")
                elif ident in identifiers[folder]:
                    self.fail(f"{rel}: identifier {ident} also defined in "
                              f"{identifiers[folder][ident]}")
                else:
                    identifiers[folder][ident] = rel
                if rel in GLOBAL_FILES and ident != GLOBAL_FILES[rel]:
                    self.notes.append(f"{rel}: identifier is {ident}, vanilla biomes look for "
                                      f"{GLOBAL_FILES[rel]}")

            getattr(self, f"check_{folder}")(rel, body, fmt)
            if folder == "color_grading":
                tone_maps[rel] = (body.get("tone_mapping") or {}).get("operator")
            if folder == "lighting":
                offsets[rel] = ((body.get("directional_lights") or {}).get("orbital") or {}).get(
                    "orbital_offset_degrees", 0.0)

        # Mojang: neither of these can be blended between biomes.
        if len(set(tone_maps.values())) > 1:
            self.fail(f"colour grading files disagree on tone_mapping.operator: {tone_maps}")
        if len({json.dumps(v) for v in offsets.values()}) > 1:
            self.fail(f"lighting files disagree on orbital_offset_degrees: {offsets}")
        return identifiers

    def check_lighting(self, rel, body, fmt):
        dl = body.get("directional_lights") or {}
        orbital = dl.get("orbital", dl)
        for body_name in ("sun", "moon"):
            light = orbital.get(body_name)
            if light is None:
                continue
            self.keyframed(f"{rel}:{body_name}.illuminance", light.get("illuminance"), "number", 0)
            self.keyframed(f"{rel}:{body_name}.color", light.get("color"), "color")
        if "orbital_offset_degrees" in orbital:
            self.keyframed(f"{rel}:orbital_offset_degrees", orbital["orbital_offset_degrees"],
                           "number", -360, 360)
        if "flash" in dl:
            self.number(f"{rel}:flash.illuminance", dl["flash"].get("illuminance"), 0)
            self.color(f"{rel}:flash.color", dl["flash"].get("color"))
        if "emissive" in body:
            self.number(f"{rel}:emissive.desaturation", body["emissive"].get("desaturation"), 0, 1)
        # Keyframes for ambient and sky arrived in 1.26.0.
        if "ambient" in body:
            amb = body["ambient"]
            self.keyframed(f"{rel}:ambient.illuminance", amb.get("illuminance"), "number", 0, 5,
                           (1, 26, 0), fmt)
            self.keyframed(f"{rel}:ambient.color", amb.get("color"), "color", None, None,
                           (1, 26, 0), fmt)
        if "sky" in body:
            self.keyframed(f"{rel}:sky.intensity", body["sky"].get("intensity"), "number", 0.1, 1.0,
                           (1, 26, 0), fmt)

    def check_atmospherics(self, rel, body, fmt):
        for key in ("rayleigh_strength", "sun_mie_strength", "moon_mie_strength", "sun_glare_shape"):
            if key in body:
                self.keyframed(f"{rel}:{key}", body[key], "number", 0)
        for key in ("sky_zenith_color", "sky_horizon_color"):
            if key in body:
                self.keyframed(f"{rel}:{key}", body[key], "color")
            else:
                self.fail(f"{rel}: {key} is missing")
        for key, value in (body.get("horizon_blend_stops") or {}).items():
            self.keyframed(f"{rel}:horizon_blend_stops.{key}", value, "number", 0)

    def check_color_grading(self, rel, body, fmt):
        cg = body.get("color_grading") or {}
        ranges = {"contrast": (0, 4), "gain": (0, 10), "gamma": (0, 4), "offset": (-1, 1),
                  "saturation": (0, 10)}
        for section in ("midtones", "shadows", "highlights"):
            block = cg.get(section)
            if block is None:
                continue
            for key, (lo, hi) in ranges.items():
                if key in block:
                    self.triple(f"{rel}:{section}.{key}", block[key], lo, hi)
            if section != "midtones":
                # Mojang: a range only applies with enabled true *and* grading
                # values; the threshold on its own does nothing.
                if block.get("enabled") is not True:
                    self.notes.append(f"{rel}: {section} is not enabled, so it has no effect")
                if not set(block) & set(ranges):
                    self.fail(f"{rel}: {section} has no grading values, so it has no effect")
        if "shadows" in cg and "shadowsMax" in cg["shadows"]:
            self.number(f"{rel}:shadows.shadowsMax", cg["shadows"]["shadowsMax"], 0.1, 1.0)
        if "highlights" in cg and "highlightsMin" in cg["highlights"]:
            self.number(f"{rel}:highlights.highlightsMin", cg["highlights"]["highlightsMin"], 1.0, 4.0)
        temp = cg.get("temperature")
        if temp:
            if "temperature" in temp:
                self.number(f"{rel}:temperature", temp["temperature"], 1000, 15000)
            if temp.get("type", "white_balance") not in ("white_balance", "color_temperature"):
                self.fail(f"{rel}: temperature.type {temp.get('type')!r} is not valid")
        op = (body.get("tone_mapping") or {}).get("operator")
        if op is not None and op not in TONE_MAPS:
            self.fail(f"{rel}: tone mapping operator {op!r} is not one of {sorted(TONE_MAPS)}")

    def check_water(self, rel, body, fmt):
        limits = {
            "particle_concentrations": {"cdom": (0, 15), "chlorophyll": (0, 10),
                                        "suspended_sediment": (0, 300)},
            "waves": {"depth": (0, 3), "direction_increment": (0, 360), "frequency": (0.01, 3),
                      "frequency_scaling": (0, 2), "mix": (0, 1), "octaves": (1, 30),
                      "pull": (-1, 1), "sampleWidth": (0.01, 1), "shape": (1, 10),
                      "speed": (0.01, 10), "speed_scaling": (0, 2)},
            "caustics": {"frame_length": (0.01, 5), "power": (1, 6), "scale": (0.1, 5)},
        }
        for section, fields in limits.items():
            for key, (lo, hi) in fields.items():
                if key in (body.get(section) or {}):
                    self.number(f"{rel}:{section}.{key}", body[section][key], lo, hi)
        for section in ("waves", "caustics"):
            if "enabled" in (body.get(section) or {}) and not isinstance(body[section]["enabled"], bool):
                self.fail(f"{rel}: {section}.enabled must be true or false")
        for key in ("octaves", "power"):
            for section in ("waves", "caustics"):
                v = (body.get(section) or {}).get(key)
                if v is not None and not isinstance(v, int):
                    self.fail(f"{rel}: {section}.{key} must be an integer, got {v!r}")
        if "biome_water_color_contribution" in body:
            self.number(f"{rel}:biome_water_color_contribution",
                        body["biome_water_color_contribution"], 0, 1)
            if fmt < (1, 26, 0):
                self.fail(f"{rel}: biome_water_color_contribution needs format_version 1.26.0")

    def check_fogs(self, rel, body, fmt):
        vol = body.get("volumetric")
        if not vol:
            return
        for medium, d in (vol.get("density") or {}).items():
            where = f"{rel}:density.{medium}"
            self.number(f"{where}.max_density", d.get("max_density"), 0, 1)
            if d.get("uniform") and ({"zero_density_height", "max_density_height"} & set(d)):
                self.fail(f"{where}: heights can only be set when uniform is false")
            if not d.get("uniform"):
                lo, hi = d.get("max_density_height"), d.get("zero_density_height")
                if lo is None or hi is None:
                    self.fail(f"{where}: non-uniform fog needs max_density_height and "
                              f"zero_density_height")
                elif hi < lo:
                    self.fail(f"{where}: zero_density_height {hi} is below "
                              f"max_density_height {lo}")
        for medium, m in (vol.get("media_coefficients") or {}).items():
            for key in ("scattering", "absorption"):
                if key in m:
                    v = m[key]
                    if isinstance(v, str):
                        self.color(f"{rel}:media_coefficients.{medium}.{key}", v)
                    else:
                        self.triple(f"{rel}:media_coefficients.{medium}.{key}", v, 0, 1)
        if vol.get("henyey_greenstein_g") and fmt < (1, 21, 90):
            self.fail(f"{rel}: henyey_greenstein_g needs format_version 1.21.90")
        for medium, g in (vol.get("henyey_greenstein_g") or {}).items():
            self.number(f"{rel}:henyey_greenstein_g.{medium}", g.get("henyey_greenstein_g"), -1, 1)

    def check_cubemaps(self, rel, body, fmt):
        if fmt < (1, 21, 130):
            self.fail(f"{rel}: cubemap settings need format_version 1.21.130")
        light = body.get("lighting") or {}
        if "ambient_light_illuminance" in light:
            self.keyframed(f"{rel}:ambient_light_illuminance", light["ambient_light_illuminance"],
                           "number", 0, 100000)
        for key in ("sky_light_contribution", "directional_light_contribution"):
            if key in light:
                self.number(f"{rel}:{key}", light[key], 0, 1)
        for key in ("affected_by_atmospheric_scattering", "affected_by_volumetric_scattering"):
            if key in light and not isinstance(light[key], bool):
                self.fail(f"{rel}: {key} must be true or false")

    def check_local_lighting(self, rel, body, fmt):
        self.local_blocks = set(body)
        for block, entry in body.items():
            where = f"{rel}:{block}"
            if ":" not in block:
                self.fail(f"{where}: block id must be namespaced (minecraft:torch)")
            if not isinstance(entry, dict):
                self.fail(f"{where}: expected an object")
                continue
            extra = set(entry) - {"light_color", "light_type"}
            if extra:
                self.fail(f"{where}: unknown keys {sorted(extra)}")
            if "light_color" in entry:
                self.color(f"{where}.light_color", entry["light_color"])
            if entry.get("light_type") not in LIGHT_TYPES:
                self.fail(f"{where}: light_type must be one of {sorted(LIGHT_TYPES)}")

    def check_shadows(self, rel, body, fmt):
        if body.get("shadow_style") not in SHADOW_STYLES:
            self.fail(f"{rel}: shadow_style must be one of {sorted(SHADOW_STYLES)}")
        texels = body.get("texel_size")
        if texels is not None and (not isinstance(texels, int) or texels <= 0):
            self.fail(f"{rel}: texel_size must be a positive integer, got {texels!r}")

    def check_pbr(self, rel, body, fmt):
        for category, values in body.items():
            mers = (values or {}).get("global_metalness_emissive_roughness_subsurface")
            if isinstance(mers, str):
                if not re.match(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$", mers):
                    self.fail(f"{rel}:{category}: bad hex MERS {mers!r}")
            elif not (isinstance(mers, list) and len(mers) in (3, 4)
                      and all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in mers)):
                self.fail(f"{rel}:{category}: expected 3 or 4 values in 0..255, got {mers!r}")

    # -- texture sets and textures ----------------------------------------------

    def texture_sets(self) -> int:
        """Mojang: a texture set is dropped if it references an image that is
        not in the same pack, mixes normal and height map, or a layer has the
        wrong number of channels."""
        count = 0
        for path in self.layered_rglob("*.texture_set.json"):
            count += 1
            rel = path.relative_to(self.pack).as_posix()
            ts = json.loads(path.read_text()).get("minecraft:texture_set", {})
            if "color" not in ts:
                self.fail(f"{rel}: color layer is required")
            if "normal" in ts and "heightmap" in ts:
                self.fail(f"{rel}: normal and heightmap cannot both be set")
            if "metalness_emissive_roughness" in ts and "metalness_emissive_roughness_subsurface" in ts:
                self.fail(f"{rel}: MER and MERS cannot both be set")
            if "heightmap" in ts and "textures/blocks" not in rel:
                self.fail(f"{rel}: height maps only work on blocks; use a normal map")
            for layer, value in ts.items():
                if not isinstance(value, str) or value.startswith("#"):
                    continue
                image = next((path.parent / (value + ext) for ext in (".tga", ".png", ".jpg", ".jpeg")
                              if (path.parent / (value + ext)).is_file()), None)
                if image is None:
                    self.fail(f"{rel}: {layer} image {value} is not in this pack next to the "
                              f"texture set")
                    continue
                mode = Image.open(image).mode
                if layer == "heightmap" and mode not in ("L", "I;16", "I"):
                    self.fail(f"{rel}: height map must be single-channel, {image.name} is {mode}")
        return count

    def environment(self) -> None:
        for rel, (mode, aspect) in ENVIRONMENT_TEXTURES.items():
            path = self.resolve(rel)
            if path is None:
                continue
            img = Image.open(path)
            if mode and img.mode != mode:
                self.fail(f"{rel}: must be {mode} (transparent background), is {img.mode}")
            w, h = img.size
            if abs(w / h - aspect) > 1e-6:
                self.fail(f"{rel}: must be {aspect:g}:1 like vanilla, is {w}x{h}")

        # A custom sky needs all six faces: with one missing the game draws
        # the whole sky black. Faces of one cubemap must match in size.
        faces = [self.resolve(rel) for rel in SKY_FACES]
        present = [f for f in faces if f]
        if present and len(present) < 6:
            missing = [rel.rsplit("/", 1)[1] for rel, f in zip(SKY_FACES, faces) if not f]
            self.fail(f"sky cubemap is missing {', '.join(missing)} - the game would draw a "
                      f"black sky")
        elif present:
            sizes = {Image.open(f).size for f in present}
            if len(sizes) > 1:
                self.fail(f"sky cubemap faces differ in size: {sorted(sizes)}")
            for rel, f in zip(SKY_FACES, faces):
                img = Image.open(f)
                if img.size[0] != img.size[1]:
                    self.fail(f"{rel}: cubemap faces must be square, is {img.size}")
                if img.mode not in ("RGB", "RGBA"):
                    self.fail(f"{rel}: must be RGB or RGBA, is {img.mode}")

    def misc(self) -> None:
        icon = self.pack / "pack_icon.png"
        if not icon.is_file():
            self.fail("pack_icon.png is missing")
        elif icon.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            self.fail("pack_icon.png is not a PNG")
        for path in sorted(self.pack.rglob("*.json")):
            try:
                json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                self.fail(f"{path.relative_to(self.pack)}: invalid JSON: {exc}")

    # -- against vanilla ----------------------------------------------------------

    def vanilla(self, vanilla: Path, identifiers: dict[str, dict[str, str]]) -> None:
        folders = {"atmosphere": "atmospherics", "lighting": "lighting",
                   "color_grading": "color_grading", "water": "water"}
        for path in sorted((vanilla / "biomes").glob("*.client_biome.json")):
            comps = json.loads(path.read_text())["minecraft:client_biome"]["components"]
            for kind, folder in folders.items():
                ident = comps.get(f"minecraft:{kind}_identifier", {}).get(f"{kind}_identifier")
                if ident and identifiers[folder] and ident not in identifiers[folder]:
                    self.fail(f"vanilla biome {path.name.split('.')[0]} uses {ident}, which this "
                              f"pack does not override, so that biome keeps vanilla {folder}")
        blocks_file = vanilla.parent / "metadata/vanilladata_modules/mojang-blocks.json"
        if blocks_file.is_file():
            known = {b["name"] for b in json.loads(blocks_file.read_text())["data_items"]}
            for block in sorted(getattr(self, "local_blocks", set())):
                if block.startswith("minecraft:") and block not in known:
                    self.fail(f"local_lighting: {block} is not a vanilla block id")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pack", nargs="?", default="bedrock", type=Path)
    parser.add_argument("--vanilla", type=Path,
                        help="Mojang bedrock-samples resource_pack directory, for coverage checks")
    args = parser.parse_args()
    if not args.pack.is_dir():
        print(f"{args.pack} not found - run from the repository root")
        return 1

    c = Checker(args.pack)
    c.manifest()
    identifiers = c.settings()
    texture_sets = c.texture_sets()
    c.environment()
    c.misc()
    if args.vanilla:
        c.vanilla(args.vanilla, identifiers)
    if not c.settings_files() and not texture_sets:
        c.fail("the pack has no settings files and no texture sets, so it changes nothing")
    problems, notes = list(c.problems), list(c.notes)

    # Each subpack is its own effective pack: the base with the subpack laid
    # over it. Report only what a subpack adds, labelled with its folder.
    for subpack in c.subpacks:
        if not (args.pack / "subpacks" / subpack).is_dir():
            continue
        s = Checker(args.pack, subpack)
        s.min_engine = c.min_engine
        s.settings()
        s.texture_sets()
        s.environment()
        problems += [f"[subpack {subpack}] {p}" for p in s.problems if p not in c.problems]
        notes += [f"[subpack {subpack}] {n}" for n in s.notes if n not in c.notes]

    for note in notes:
        print(f"  note: {note}")
    if problems:
        print("\n".join(f"  {p}" for p in problems))
        print(f"\n{len(problems)} problem(s)")
        return 1

    files = sum(1 for p in args.pack.rglob("*") if p.is_file())
    extra = f", {len(c.subpacks)} subpacks" if c.subpacks else ""
    print(f"{args.pack}: OK - {files} files, {len(c.settings_files())} settings files, "
          f"{texture_sets} texture sets{extra}, all keys known to the engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
