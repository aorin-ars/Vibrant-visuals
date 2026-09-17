#!/usr/bin/env python3
"""Validate the Bedrock resource pack.

Bedrock fails quietly: a keyframe key that is not a parseable number, a colour
channel above 255 or a mistyped settings identifier does not produce an error,
it just leaves that setting at its vanilla value. This checks the things the
game will not tell you about.

Schemas were taken from Mojang's own vanilla pack (github.com/Mojang/bedrock-samples).
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

PACK = Path("bedrock")

# file -> (expected top-level settings key, expected identifier)
SETTINGS_FILES = {
    "lighting/global.json": ("minecraft:lighting_settings", "minecraft:default_lighting"),
    "atmospherics/atmospherics.json": ("minecraft:atmosphere_settings", "minecraft:default_atmospherics"),
    "color_grading/color_grading.json": ("minecraft:color_grading_settings", "minecraft:default_color_grading"),
    "water/water.json": ("minecraft:water_settings", "minecraft:default_water"),
}

# Maps keyed by time-of-day. Every key must parse as a float in [0,1].
KEYFRAME_PATHS = [
    ("lighting/global.json", ["minecraft:lighting_settings", "directional_lights", "orbital", "sun", "illuminance"], "number"),
    ("lighting/global.json", ["minecraft:lighting_settings", "directional_lights", "orbital", "sun", "color"], "color"),
    ("lighting/global.json", ["minecraft:lighting_settings", "directional_lights", "orbital", "moon", "illuminance"], "number"),
    ("lighting/global.json", ["minecraft:lighting_settings", "directional_lights", "orbital", "moon", "color"], "color"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "rayleigh_strength"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "sun_mie_strength"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "moon_mie_strength"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "sun_glare_shape"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "sky_zenith_color"], "color"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "sky_horizon_color"], "color"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "horizon_blend_stops", "min"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "horizon_blend_stops", "start"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "horizon_blend_stops", "mie_start"], "number"),
    ("atmospherics/atmospherics.json", ["minecraft:atmosphere_settings", "horizon_blend_stops", "max"], "number"),
]

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Key names the engine actually reads, taken from Mojang's vanilla pack. A key
# outside this set is not an error to the game - it is silently ignored, which
# is exactly why a typo here is worth catching before shipping. A value of None
# means "anything below this point is free-form" (keyframe tables, colours).
ALLOWED = {
    "lighting/global.json": {
        "minecraft:lighting_settings": {
            "description": {"identifier": None},
            "directional_lights": {
                "orbital": {
                    "sun": {"illuminance": None, "color": None},
                    "moon": {"illuminance": None, "color": None},
                    "orbital_offset_degrees": None,
                },
                "flash": {"illuminance": None, "color": None},
            },
            "emissive": {"desaturation": None},
            "ambient": {"color": None, "illuminance": None},
            "sky": {"intensity": None},
        },
        "format_version": None,
    },
    "atmospherics/atmospherics.json": {
        "minecraft:atmosphere_settings": {
            "description": {"identifier": None},
            "horizon_blend_stops": {"min": None, "start": None, "mie_start": None, "max": None},
            "rayleigh_strength": None,
            "sun_mie_strength": None,
            "moon_mie_strength": None,
            "sun_glare_shape": None,
            "sky_zenith_color": None,
            "sky_horizon_color": None,
        },
        "format_version": None,
    },
    "color_grading/color_grading.json": {
        "minecraft:color_grading_settings": {
            "description": {"identifier": None},
            "color_grading": {
                "shadows": None,
                "midtones": {"contrast": None, "gain": None, "gamma": None,
                             "offset": None, "saturation": None},
                "highlights": None,
                "temperature": {"enabled": None, "temperature": None, "type": None},
            },
            "tone_mapping": {"operator": None},
        },
        "format_version": None,
    },
    "water/water.json": {
        "minecraft:water_settings": {
            "description": {"identifier": None},
            "particle_concentrations": {"chlorophyll": None, "suspended_sediment": None,
                                        "cdom": None},
            "caustics": {"enabled": None, "frame_length": None, "scale": None, "power": None},
            "waves": {"enabled": None, "frequency": None, "octaves": None, "depth": None,
                      "speed": None, "shape": None, "pull": None, "mix": None,
                      "frequency_scaling": None, "speed_scaling": None},
        },
        "format_version": None,
    },
}


def check_unknown_keys(data, spec, where: str, problems: list[str]) -> None:
    if spec is None or not isinstance(data, dict):
        return
    for key, value in data.items():
        if key not in spec:
            problems.append(f"{where}.{key}: not a key the engine reads "
                            f"(expected one of: {', '.join(sorted(spec))})")
            continue
        check_unknown_keys(value, spec[key], f"{where}.{key}", problems)


def dig(data, path):
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def check_manifest(problems: list[str]) -> None:
    path = PACK / "manifest.json"
    if not path.is_file():
        problems.append("manifest.json is missing")
        return
    manifest = json.loads(path.read_text())

    if manifest.get("format_version") != 2:
        problems.append("manifest format_version must be 2")

    header = manifest.get("header", {})
    modules = manifest.get("modules", [])

    seen: set[str] = set()
    for label, value in [("header", header.get("uuid"))] + [
        (f"module[{i}]", m.get("uuid")) for i, m in enumerate(modules)
    ]:
        try:
            uuid.UUID(str(value))
        except (ValueError, TypeError):
            problems.append(f"{label} uuid is not a valid UUID: {value!r}")
            continue
        if value in seen:
            problems.append(f"{label} reuses uuid {value} - every uuid must be unique")
        seen.add(value)

    for field in ("name", "description", "version", "min_engine_version"):
        if field not in header:
            problems.append(f"manifest header is missing {field}")

    for field in ("version", "min_engine_version"):
        value = header.get(field)
        if not (isinstance(value, list) and len(value) == 3
                and all(isinstance(n, int) for n in value)):
            problems.append(f"manifest header {field} must be three integers, got {value!r}")

    if not any(m.get("type") == "resources" for m in modules):
        problems.append("manifest has no module of type 'resources'")

    # Translated name/description only resolve if the .lang files carry the keys.
    for field in ("name", "description"):
        key = header.get(field)
        if isinstance(key, str) and key.startswith("pack."):
            for lang in sorted((PACK / "texts").glob("*.lang")):
                if not any(line.startswith(key + "=")
                           for line in lang.read_text(encoding="utf-8").splitlines()):
                    problems.append(f"{lang.name} has no entry for {key}")


def check_settings(problems: list[str]) -> None:
    for name, (settings_key, identifier) in SETTINGS_FILES.items():
        path = PACK / name
        if not path.is_file():
            problems.append(f"{name} is missing")
            continue
        data = json.loads(path.read_text())

        if "format_version" not in data:
            problems.append(f"{name}: no format_version")

        if settings_key not in data:
            problems.append(f"{name}: expected top-level key {settings_key}")
            continue

        found = dig(data, [settings_key, "description", "identifier"])
        if found != identifier:
            problems.append(f"{name}: identifier is {found!r}, "
                            f"must be {identifier!r} to override the vanilla setting")


def check_keyframes(problems: list[str]) -> None:
    for name, path, kind in KEYFRAME_PATHS:
        data = json.loads((PACK / name).read_text())
        table = dig(data, path)
        where = f"{name}:{'.'.join(path[1:])}"

        if table is None:
            problems.append(f"{where} is missing")
            continue
        if not isinstance(table, dict) or not table:
            problems.append(f"{where} must be a non-empty keyframe map")
            continue

        for key, value in table.items():
            try:
                t = float(key)
            except ValueError:
                problems.append(f"{where}: key {key!r} is not a number")
                continue
            if not 0.0 <= t <= 1.0:
                problems.append(f"{where}: key {key} is outside 0..1")

            if kind == "number":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    problems.append(f"{where}[{key}]: expected a number, got {value!r}")
                elif value < 0:
                    problems.append(f"{where}[{key}]: negative value {value}")
            else:
                if not (isinstance(value, list) and len(value) == 3
                        and all(isinstance(c, int) for c in value)):
                    problems.append(f"{where}[{key}]: expected [r, g, b], got {value!r}")
                elif not all(0 <= c <= 255 for c in value):
                    problems.append(f"{where}[{key}]: channel outside 0..255: {value}")

        # Time of day wraps, so neither endpoint is required - vanilla's own
        # sky colour tables stop at 0.83. Two stops are the minimum to interpolate.
        if len(table) < 2:
            problems.append(f"{where}: needs at least two keyframes, has {len(table)}")


def check_misc(problems: list[str]) -> None:
    lighting = json.loads((PACK / "lighting/global.json").read_text())
    ambient = dig(lighting, ["minecraft:lighting_settings", "ambient", "color"])
    if not (isinstance(ambient, str) and HEX_COLOR.match(ambient)):
        problems.append(f"lighting ambient.color must be #RRGGBB, got {ambient!r}")

    icon = PACK / "pack_icon.png"
    if not icon.is_file():
        problems.append("pack_icon.png is missing")
    elif icon.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        problems.append("pack_icon.png is not a PNG")

    for path in sorted(PACK.rglob("*.json")):
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"{path.relative_to(PACK)}: invalid JSON: {exc}")


def main() -> int:
    if not PACK.is_dir():
        print(f"{PACK} not found - run from the repository root")
        return 1

    problems: list[str] = []
    check_manifest(problems)
    check_settings(problems)
    for name, spec in ALLOWED.items():
        path = PACK / name
        if path.is_file():
            check_unknown_keys(json.loads(path.read_text()), spec, name, problems)
    check_keyframes(problems)
    check_misc(problems)

    if problems:
        print("\n".join(f"  {p}" for p in problems))
        print(f"\n{len(problems)} problem(s)")
        return 1

    files = sorted(p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file())
    print(f"bedrock pack OK: {len(files)} files, "
          f"{len(SETTINGS_FILES)} settings files, "
          f"{len(KEYFRAME_PATHS)} keyframe tables, all keys known to the engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
