#!/usr/bin/env python3
"""Generate every Vibrant Visuals settings file in bedrock/ (and diagnostic/).

    tools/generate_bedrock.py --vanilla <bedrock-samples>/resource_pack

The look is modelled on Complementary Unbound: a warm, strong sun with long
golden hours, deep blue zenith over a pale hazy horizon, blue-filled shadows,
low valley haze that turns into light shafts toward the sun, clear blue water
with real waves, and coloured block light.

Why a generator and not hand-written JSON: since 1.21.90 the vanilla pack
assigns *per-biome* lighting, atmosphere and colour grading to most biomes
(jungle, desert, taiga, mesa, the Nether, the End, ...), and those take
precedence over lighting/global.json. A pack that only overrides the global
files changes plains and forest and nothing else. So every identifier the
vanilla client biomes use is overridden here, at the same path and with the
same identifier, from one palette - which is only maintainable if it is
generated.

--vanilla points at Mojang's vanilla resource pack (github.com/Mojang/bedrock-samples,
folder resource_pack). It is read for three things only: which identifiers the
vanilla biomes use (so none is missed), the distance-fog blocks of the fog
files that are overridden (kept byte-for-byte, only the volumetric part
changes), and the canonical block ids used to check local_lighting entries.
No vanilla file is copied into the pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "bedrock"
DIAG = ROOT / "diagnostic"

# 1.26.0 adds keyframed ambient light and biome water colour; both are used,
# so the manifest's min_engine_version has to be at least this.
LIGHTING_FORMAT = "1.26.0"
ATMOSPHERE_FORMAT = "1.21.40"
GRADING_FORMAT = "1.21.90"
WATER_FORMAT = "1.26.0"
FOG_FORMAT = "1.21.90"          # henyey_greenstein_g needs 1.21.90
LOCAL_LIGHT_FORMAT = "1.21.120"
SHADOW_FORMAT = "1.21.80"
PBR_FORMAT = "1.21.40"
CUBEMAP_FORMAT = "1.21.130"

# Mojang: orbital offset and tone mapping operator cannot be blended between
# biomes, so every file in the pack has to agree on them.
ORBITAL_OFFSET = 20.0
TONE_MAP = "generic"

# Time of day: 0.0 noon, 0.25 sunset, 0.5 midnight, 0.75 sunrise.


# --------------------------------------------------------------------------
# JSON output
# --------------------------------------------------------------------------

def dump(obj) -> str:
    """JSON with short lists kept on one line, the way Mojang's files read."""
    def enc(o, ind):
        pad = "  " * ind
        if isinstance(o, dict):
            if not o:
                return "{}"
            items = [f'{pad}  {json.dumps(k)}: {enc(v, ind + 1)}' for k, v in o.items()]
            return "{\n" + ",\n".join(items) + f"\n{pad}}}"
        if isinstance(o, list) and all(not isinstance(x, (dict, list)) for x in o):
            return "[" + ", ".join(enc(x, ind) for x in o) + "]"
        if isinstance(o, list):
            items = [f"{pad}  {enc(v, ind + 1)}" for v in o]
            return "[\n" + ",\n".join(items) + f"\n{pad}]"
        if isinstance(o, float):
            text = f"{o:.6f}".rstrip("0")
            return text + "0" if text.endswith(".") else text
        return json.dumps(o, ensure_ascii=False)
    return enc(obj, 0) + "\n"


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(obj), encoding="utf-8")


def keyframes(points: dict[float, object]) -> dict[str, object]:
    return {f"{t:.6f}": v for t, v in sorted(points.items())}


def mirror(evening: dict[float, object], morning: dict[float, object] | None = None,
           ) -> dict[float, object]:
    """Evening half (0..0.5) plus its reflection about midnight for the morning.

    `morning` overrides individual reflected stops, for the places where dawn
    should not simply be dusk played backwards.
    """
    out = dict(evening)
    for t, v in evening.items():
        if 0.0 < t < 0.5:
            out[round(1.0 - t, 6)] = v
    out[1.0] = evening[0.0]
    out.update(morning or {})
    return out


def scale_rgb(rgb, tint):
    return [max(0, min(255, round(c * k))) for c, k in zip(rgb, tint)]


def lerp_rgb(a, b, t):
    return [round(x + (y - x) * t) for x, y in zip(a, b)]


# --------------------------------------------------------------------------
# Lighting
# --------------------------------------------------------------------------

# Brighter than vanilla (100) at noon, and held up much longer into the
# afternoon: Complementary's golden hour is still strong direct light, not a
# fade-out. The last stops copy vanilla's shape so the handover to the moon at
# 0.292 is unchanged.
SUN_ILLUMINANCE = mirror({
    0.000: 130.0,
    0.080: 128.0,
    0.150: 110.0,
    0.200: 78.0,
    0.230: 46.0,
    0.250: 24.0,
    0.268: 8.0,
    0.282: 1.2,
    0.2915: 0.01,
    0.292: 0.0,
    0.500: 0.0,
})

# Warm white at noon, a long gold into deep orange at the horizon. After the
# sun is down its colour still drives sky scattering, which is what paints the
# rose-and-violet dusk.
SUN_COLOR = {
    0.000: [255, 241, 222],
    0.120: [255, 234, 206],
    0.180: [255, 214, 166],
    0.215: [255, 186, 120],
    0.240: [255, 152, 78],
    0.262: [255, 120, 52],
    0.285: [255, 118, 92],
    0.320: [255, 140, 150],
    0.500: [255, 110, 60],
    0.680: [255, 140, 150],
    0.715: [255, 124, 98],
    0.738: [255, 130, 60],
    0.760: [255, 164, 90],
    0.790: [255, 196, 134],
    0.840: [255, 224, 184],
    0.900: [255, 236, 210],
    1.000: [255, 241, 222],
}

# Moonlit nights you can see in, with a clear blue cast - vanilla's is 0.4.
MOON_ILLUMINANCE = {
    0.000: 0.0, 0.200: 0.0, 0.225: 0.5, 0.300: 0.7,
    0.700: 0.7, 0.735: 0.5, 0.750: 0.0, 1.000: 0.0,
}
MOON_COLOR = [150, 178, 255]

# Fallback light for caves and for surfaces with nothing to reflect. Kept at
# vanilla strength so caves stay dark, but tinted like the sky above: cool by
# day, deep blue at night, lilac through twilight.
AMBIENT_COLOR = {
    0.000: [204, 220, 255],
    0.220: [214, 212, 240],
    0.280: [180, 170, 220],
    0.360: [128, 150, 220],
    0.640: [128, 150, 220],
    0.720: [190, 172, 214],
    0.780: [216, 212, 236],
    1.000: [204, 220, 255],
}
AMBIENT_ILLUMINANCE = {
    0.000: 0.022, 0.250: 0.020, 0.360: 0.017,
    0.640: 0.017, 0.750: 0.020, 1.000: 0.022,
}


def overworld_lighting(identifier: str, *, sun_scale=1.0, sun_tint=(1, 1, 1),
                       moon_color=MOON_COLOR, ambient_tint=(1, 1, 1),
                       sun_color_override=None) -> dict:
    sun_color = ({t: sun_color_override for t in (0.0, 1.0)} if sun_color_override
                 else {t: scale_rgb(c, sun_tint) for t, c in SUN_COLOR.items()})
    return lighting_file(
        identifier,
        sun_illuminance=keyframes({t: round(v * sun_scale, 3) for t, v in SUN_ILLUMINANCE.items()}),
        sun_color=keyframes(sun_color),
        moon_illuminance=keyframes(MOON_ILLUMINANCE),
        moon_color=keyframes({0.0: moon_color, 1.0: moon_color}),
        ambient_color=keyframes({t: scale_rgb(c, ambient_tint) for t, c in AMBIENT_COLOR.items()}),
        ambient_illuminance=keyframes(AMBIENT_ILLUMINANCE),
    )


def lighting_file(identifier, *, sun_illuminance, sun_color, moon_illuminance, moon_color,
                  ambient_color, ambient_illuminance, flash=(10.0, [228, 93, 255]),
                  sky=1.0, format_version=LIGHTING_FORMAT,
                  orbital_offset=ORBITAL_OFFSET) -> dict:
    return {
        "format_version": format_version,
        "minecraft:lighting_settings": {
            "description": {"identifier": identifier},
            "directional_lights": {
                "orbital": {
                    "sun": {"illuminance": sun_illuminance, "color": sun_color},
                    "moon": {"illuminance": moon_illuminance, "color": moon_color},
                    "orbital_offset_degrees": orbital_offset,
                },
                "flash": {"illuminance": flash[0], "color": flash[1]},
            },
            "emissive": {"desaturation": 0.0},
            "ambient": {"color": ambient_color, "illuminance": ambient_illuminance},
            "sky": {"intensity": sky},
        },
    }


def constant(value) -> dict:
    return keyframes({0.0: value, 1.0: value})


LIGHTING = {
    # file name -> settings. Warm biomes get a warmer, slightly stronger sun;
    # cold ones a whiter one. The differences are kept small on purpose:
    # Complementary keeps one sun across the world and lets fog and water
    # carry the biome.
    "global.json": overworld_lighting("minecraft:default_lighting"),
    "cold_lighting.json": overworld_lighting(
        "minecraft:cold_lighting", sun_tint=(0.97, 1.0, 1.04)),
    "coolish_lighting.json": overworld_lighting(
        "minecraft:coolish_lighting", sun_tint=(0.985, 1.0, 1.02)),
    "warmish_lighting.json": overworld_lighting(
        "minecraft:warmish_lighting", sun_tint=(1.0, 0.985, 0.95), moon_color=[128, 156, 255]),
    "hot_lighting.json": overworld_lighting(
        "minecraft:hot_lighting", sun_scale=1.04, sun_tint=(1.0, 0.97, 0.9), moon_color=[116, 146, 255]),
    "desert_lighting.json": overworld_lighting(
        "minecraft:desert_lighting", sun_scale=1.06, sun_tint=(1.0, 0.975, 0.92),
        moon_color=[116, 150, 255]),
    "mesa_lighting.json": overworld_lighting(
        "minecraft:mesa_lighting", sun_scale=1.04, sun_tint=(1.0, 0.96, 0.9),
        moon_color=[128, 156, 255]),
    "ice_plains_spikes_lighting.json": overworld_lighting(
        "minecraft:ice_plains_spikes_lighting", sun_scale=0.8, sun_tint=(0.92, 0.96, 1.0),
        ambient_tint=(0.96, 0.99, 1.0)),
    "mangrove_swamp_lighting.json": overworld_lighting(
        "minecraft:mangrove_swamp_lighting", sun_scale=0.92, sun_tint=(0.98, 1.0, 0.94),
        ambient_tint=(0.96, 1.0, 0.96)),
    "swampland_lighting.json": overworld_lighting(
        "minecraft:swampland_lighting", sun_scale=0.9, sun_tint=(0.97, 1.0, 0.92),
        ambient_tint=(0.95, 1.0, 0.94)),
    "mushroom_island_lighting.json": overworld_lighting(
        "minecraft:mushroom_island_lighting", sun_tint=(0.97, 0.92, 1.0),
        ambient_tint=(1.0, 0.94, 1.0)),
    "roofed_forest_lighting.json": overworld_lighting(
        "minecraft:roofed_forest_lighting", sun_scale=0.8, sun_tint=(1.0, 1.0, 0.97)),
    # The Pale Garden is meant to be sunless and grey; vanilla gives it 5 lux.
    # Keep the mood, just enough light to see the shapes.
    "pale_garden_lighting.json": overworld_lighting(
        "minecraft:pale_garden_lighting", sun_scale=0.08,
        sun_color_override=[200, 214, 240], moon_color=[210, 220, 255],
        ambient_tint=(0.98, 1.0, 1.0)),
    # Nether and End: vanilla drives them with constant 100 lux "sun" and
    # "moon"; only the colour of the fill light changes here.
    "nether_lighting.json": lighting_file(
        "minecraft:nether_lighting",
        sun_illuminance=constant(100.0), sun_color=constant([255, 255, 255]),
        moon_illuminance=constant(100.0), moon_color=constant([255, 255, 255]),
        ambient_color=[255, 232, 214], ambient_illuminance=0.5),
    "end_lighting.json": lighting_file(
        "minecraft:end_lighting",
        sun_illuminance=constant(100.0), sun_color=constant([236, 224, 255]),
        moon_illuminance=constant(100.0), moon_color=constant([236, 224, 255]),
        ambient_color=[216, 200, 255], ambient_illuminance=0.14,
        flash=(4.0, [200, 110, 255])),
}


# --------------------------------------------------------------------------
# Atmospherics
# --------------------------------------------------------------------------

# Rayleigh drives the depth of the blue; it is dropped through twilight as
# vanilla does, or dusk goes muddy.
RAYLEIGH = mirror({0.0: 12.0, 0.139: 11.5, 0.25: 6.0, 0.33: 5.5, 0.5: 5.0})

# Vanilla has no sun haze at all during the day. Complementary has a soft
# bright halo around the sun at every hour, flaring wide at the horizon.
SUN_MIE = mirror({0.0: 0.30, 0.15: 0.36, 0.20: 0.55, 0.25: 1.10, 0.28: 0.60,
                  0.35: 0.0, 0.5: 0.0})
SUN_GLARE = mirror({0.0: 0.040, 0.15: 0.045, 0.20: 0.060, 0.25: 0.090, 0.28: 0.060,
                    0.35: 0.0, 0.5: 0.0})
MOON_MIE = {0.0: 0.0, 0.22: 0.0, 0.30: 0.15, 0.70: 0.15, 0.78: 0.0, 1.0: 0.0}

# Horizon blend: vanilla's shape, with the zenith taking over a little lower at
# midday so the deep blue reaches further down the sky.
BLEND_MIN = {0.0: 0.0, 1.0: 0.0}
BLEND_START = mirror({0.0: 0.70, 0.25: 0.50, 0.301: 0.25, 0.5: 0.25})
BLEND_MIE_START = {0.0: 0.5, 0.1: 0.5, 0.2: 1.0, 0.8: 1.0, 0.9: 0.5, 1.0: 0.5}
BLEND_MAX = {0.0: 0.25, 1.0: 0.25}

NIGHT_ZENITH = [26, 34, 62]
NIGHT_HORIZON = [58, 82, 128]


def sky_tables(day_zenith, day_horizon, *, dusk_zenith=(62, 86, 160),
               twilight=None, night_zenith=NIGHT_ZENITH, night_horizon=NIGHT_HORIZON):
    """Zenith and horizon colour keyframes around one day palette.

    Dusk and dawn get their own colours rather than a mirror: sunset is
    orange going to rose and violet, sunrise pinker and more golden.
    """
    t = twilight or {}
    zenith = {
        0.000: day_zenith,
        0.190: lerp_rgb(day_zenith, list(dusk_zenith), 0.12),
        0.250: list(dusk_zenith),
        0.300: t.get("zenith_dusk", [44, 50, 110]),
        0.360: night_zenith,
        0.640: night_zenith,
        0.700: t.get("zenith_dawn", [48, 56, 118]),
        0.750: lerp_rgb(list(dusk_zenith), day_zenith, 0.2),
        0.810: lerp_rgb(day_zenith, list(dusk_zenith), 0.12),
        1.000: day_zenith,
    }
    horizon = {
        0.000: day_horizon,
        0.167: day_horizon,
        0.205: t.get("golden", [255, 196, 140]),
        0.232: t.get("sunset", [255, 160, 96]),
        0.252: t.get("sunset_deep", [255, 128, 84]),
        0.272: t.get("rose", [206, 110, 120]),
        0.300: t.get("violet", [150, 110, 170]),
        0.360: t.get("blue_hour", [92, 100, 168]),
        0.400: night_horizon,
        0.600: night_horizon,
        0.640: t.get("blue_hour_dawn", [96, 104, 176]),
        0.700: t.get("pink_dawn", [196, 150, 196]),
        0.728: t.get("sunrise", [255, 150, 120]),
        0.748: t.get("sunrise_gold", [255, 172, 120]),
        0.770: t.get("morning", [255, 206, 158]),
        0.830: day_horizon,
        1.000: day_horizon,
    }
    return zenith, horizon


def atmosphere(identifier, zenith, horizon, *, rayleigh=RAYLEIGH, sun_mie=SUN_MIE,
               sun_glare=SUN_GLARE, moon_mie=MOON_MIE, blend_start=BLEND_START,
               mie_scale=1.0, rayleigh_scale=1.0) -> dict:
    return {
        "format_version": ATMOSPHERE_FORMAT,
        "minecraft:atmosphere_settings": {
            "description": {"identifier": identifier},
            "horizon_blend_stops": {
                "min": keyframes(BLEND_MIN),
                "start": keyframes(blend_start),
                "mie_start": keyframes(BLEND_MIE_START),
                "max": keyframes(BLEND_MAX),
            },
            "rayleigh_strength": keyframes({t: round(v * rayleigh_scale, 3) for t, v in rayleigh.items()}),
            "sun_mie_strength": keyframes({t: round(v * mie_scale, 3) for t, v in sun_mie.items()}),
            "moon_mie_strength": keyframes(moon_mie),
            "sun_glare_shape": keyframes(sun_glare),
            "sky_zenith_color": keyframes(zenith),
            "sky_horizon_color": keyframes(horizon),
        },
    }


def overworld_atmosphere(identifier, day_zenith, day_horizon, *, twilight=None,
                         dusk_zenith=(62, 86, 160), **kw) -> dict:
    zenith, horizon = sky_tables(day_zenith, day_horizon, dusk_zenith=dusk_zenith,
                                 twilight=twilight)
    return atmosphere(identifier, zenith, horizon, **kw)


def flat_atmosphere(identifier, zenith, horizon, rayleigh, *, start=0.8, mie_start=0.5,
                    blend_max=1.0) -> dict:
    """Nether and End: no day cycle, vanilla's plain-number blend stops."""
    return {
        "format_version": ATMOSPHERE_FORMAT,
        "minecraft:atmosphere_settings": {
            "description": {"identifier": identifier},
            "horizon_blend_stops": {"min": 0.0, "start": start, "mie_start": mie_start,
                                    "max": blend_max},
            "rayleigh_strength": constant(rayleigh),
            "sun_mie_strength": constant(0.0),
            "moon_mie_strength": constant(0.0),
            "sun_glare_shape": constant(0.0),
            "sky_zenith_color": constant(zenith),
            "sky_horizon_color": constant(horizon),
        },
    }


# Deep saturated blue overhead, pale hazy blue at the horizon - the gradient
# that makes the sky in Complementary read as "clear summer day".
DAY_ZENITH = [58, 108, 205]
DAY_HORIZON = [178, 206, 240]

DESERT_TWILIGHT = {"golden": [255, 200, 132], "sunset": [255, 164, 88],
                   "sunset_deep": [255, 132, 72], "rose": [214, 116, 104]}

ATMOSPHERICS = {
    "atmospherics.json": overworld_atmosphere(
        "minecraft:default_atmospherics", DAY_ZENITH, DAY_HORIZON),
    "warmish_atmospherics.json": overworld_atmosphere(
        "minecraft:warmish_atmospherics", [60, 112, 204], [188, 212, 230]),
    "hot_atmospherics.json": overworld_atmosphere(
        "minecraft:hot_atmospherics", [66, 122, 204], [212, 208, 190], twilight=DESERT_TWILIGHT),
    "desert_atmospherics.json": overworld_atmosphere(
        "minecraft:desert_atmospherics", [70, 128, 200], [214, 206, 180], twilight=DESERT_TWILIGHT,
        mie_scale=1.15),
    "mesa_atmospherics.json": overworld_atmosphere(
        "minecraft:mesa_atmospherics", [66, 132, 196], [216, 202, 172], twilight=DESERT_TWILIGHT,
        mie_scale=1.1),
    "ice_plains_spikes_atmospherics.json": overworld_atmosphere(
        "minecraft:ice_plains_spikes_atmospherics", [120, 160, 215], [204, 218, 234],
        twilight={"golden": [236, 214, 214], "sunset": [226, 180, 190],
                  "sunset_deep": [206, 160, 200], "rose": [168, 140, 200]}),
    "mangrove_swamp_atmospherics.json": overworld_atmosphere(
        "minecraft:mangrove_swamp_atmospherics", [96, 142, 196], [190, 206, 214]),
    "swampland_atmospherics.json": overworld_atmosphere(
        "minecraft:swampland_atmospherics", [104, 138, 150], [184, 196, 188], mie_scale=0.8),
    "roofed_forest_atmospherics.json": overworld_atmosphere(
        "minecraft:roofed_forest_atmospherics", [52, 96, 170], [172, 196, 222]),
    "mushroom_island_atmospherics.json": overworld_atmosphere(
        "minecraft:mushroom_island_atmospherics", [110, 124, 196], [214, 212, 236],
        twilight={"sunset": [255, 120, 150], "sunset_deep": [240, 100, 150],
                  "rose": [200, 100, 170], "violet": [140, 90, 190]}),
    # Overcast and colourless, like vanilla intends, with no sun halo at all.
    "pale_garden_atmospherics.json": overworld_atmosphere(
        "minecraft:pale_garden_atmospherics", [128, 134, 142], [196, 196, 190],
        dusk_zenith=(96, 100, 110), mie_scale=0.0, rayleigh_scale=0.5,
        twilight={"golden": [200, 190, 180], "sunset": [190, 170, 160],
                  "sunset_deep": [170, 150, 150], "rose": [140, 130, 140],
                  "violet": [110, 110, 130]}),
    # Nether: no sky to see, but these set the colour of distance haze.
    "hell_atmospherics.json": flat_atmosphere(
        "minecraft:hell_atmospherics", [74, 18, 10], [74, 18, 10], 0.15),
    "crimson_forest_atmospherics.json": flat_atmosphere(
        "minecraft:crimson_forest_atmospherics", [70, 10, 12], [70, 10, 12], 0.15),
    "warped_forest_atmospherics.json": flat_atmosphere(
        "minecraft:warped_forest_atmospherics", [26, 30, 44], [26, 30, 44], 0.25),
    "soulsand_valley_atmospherics.json": flat_atmosphere(
        "minecraft:soulsand_valley_atmospherics", [24, 70, 72], [24, 70, 72], 0.15),
    "basalt_deltas_atmospherics.json": flat_atmosphere(
        "minecraft:basalt_deltas_atmospherics", [100, 90, 112], [100, 90, 112], 0.1),
    "end_atmospherics.json": flat_atmosphere(
        "minecraft:end_atmospherics", [34, 20, 58], [8, 4, 16], 50.0,
        start=1.0, blend_max=0.25),
}


# --------------------------------------------------------------------------
# Colour grading
# --------------------------------------------------------------------------

# Vanilla: contrast 1.15, saturation 1.05. Complementary is punchier and more
# saturated, with shadows leaning cool and highlights warm.
BASE_GRADE = {"contrast": 1.20, "saturation": 1.16, "gain": (1.02, 1.01, 1.00)}


def grading(identifier, *, temperature=6500.0, contrast=None, saturation=None,
            gain=None) -> dict:
    c = BASE_GRADE["contrast"] if contrast is None else contrast
    s = BASE_GRADE["saturation"] if saturation is None else saturation
    g = BASE_GRADE["gain"] if gain is None else gain
    return {
        "format_version": GRADING_FORMAT,
        "minecraft:color_grading_settings": {
            "description": {"identifier": identifier},
            "color_grading": {
                "midtones": {
                    "contrast": [c, c, c],
                    "gain": list(g),
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [s, s, s],
                },
                "shadows": {
                    "enabled": True,
                    "shadowsMax": 0.45,
                    "contrast": [1.0, 1.0, 1.0],
                    "gain": [0.97, 1.0, 1.05],
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [1.05, 1.05, 1.05],
                },
                "highlights": {
                    "enabled": True,
                    "highlightsMin": 1.6,
                    "contrast": [1.0, 1.0, 1.0],
                    "gain": [1.03, 1.01, 0.97],
                    "gamma": [2.2, 2.2, 2.2],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [1.0, 1.0, 1.0],
                },
                "temperature": {
                    "enabled": True,
                    "temperature": temperature,
                    "type": "color_temperature",
                },
            },
            "tone_mapping": {"operator": TONE_MAP},
        },
    }


def toward_neutral(kelvin: float, keep: float = 0.6) -> float:
    """Vanilla tints biomes hard (desert 4400 K, ice spikes 11000 K).
    Complementary barely tints at all; keep 60 % of vanilla's shift."""
    return round(6500.0 + (kelvin - 6500.0) * keep)


COLOR_GRADING = {
    "color_grading.json": grading("minecraft:default_color_grading"),
    "cold_color_grading.json": grading(
        "minecraft:cold_color_grading", temperature=toward_neutral(10000), saturation=1.10),
    "coolish_color_grading.json": grading(
        "minecraft:coolish_color_grading", temperature=toward_neutral(9000), saturation=1.13),
    "warmish_color_grading.json": grading(
        "minecraft:warmish_color_grading", temperature=toward_neutral(4800), saturation=1.18),
    "hot_color_grading.json": grading(
        "minecraft:hot_color_grading", temperature=toward_neutral(4000), contrast=1.26),
    "desert_color_grading.json": grading(
        "minecraft:desert_color_grading", temperature=toward_neutral(4400), saturation=1.12),
    "mesa_color_grading.json": grading(
        "minecraft:mesa_color_grading", temperature=toward_neutral(4800), saturation=1.14),
    "ice_plains_spikes_color_grading.json": grading(
        "minecraft:ice_plains_spikes_color_grading", temperature=toward_neutral(11000),
        saturation=1.08),
    "lush_caves_color_grading.json": grading(
        "minecraft:lush_caves_color_grading", temperature=toward_neutral(4800), contrast=1.24,
        saturation=1.22),
    "mangrove_swamp_color_grading.json": grading(
        "minecraft:mangrove_swamp_color_grading", temperature=toward_neutral(5125)),
    "mushroom_island_color_grading.json": grading(
        "minecraft:mushroom_island_color_grading", saturation=1.22),
    "pale_garden_color_grading.json": grading(
        "minecraft:pale_garden_color_grading", temperature=toward_neutral(9000),
        saturation=0.85, contrast=1.16),
    "roofed_forest_color_grading.json": grading(
        "minecraft:roofed_forest_color_grading", contrast=1.24, saturation=1.12),
    "swampland_color_grading.json": grading(
        "minecraft:swampland_color_grading", saturation=1.08),
}


# --------------------------------------------------------------------------
# Water
# --------------------------------------------------------------------------

WATER = {
    "format_version": WATER_FORMAT,
    "minecraft:water_settings": {
        "description": {"identifier": "minecraft:default_water"},
        # Nearly clear water: a trace of chlorophyll and organic matter gives
        # the shallow teal, the biome's own water colour does the rest.
        "particle_concentrations": {
            "chlorophyll": 0.2,
            "suspended_sediment": 0.0,
            "cdom": 0.1,
        },
        # Waves are off in vanilla. Tuned for a lively but not stormy surface:
        # shallower than vanilla's depth 1, slower, a few octaves fewer so it
        # stays cheap on phones.
        "waves": {
            "enabled": True,
            "depth": 0.85,
            "frequency": 1.0,
            "frequency_scaling": 1.18,
            "mix": 0.25,
            "octaves": 24,
            "pull": 0.3,
            "shape": 1.4,
            "speed": 1.6,
            "speed_scaling": 1.04,
        },
        "caustics": {
            "enabled": True,
            "frame_length": 0.07,
            "power": 2,
            "scale": 0.5,
        },
        # Swamps come out green, warm oceans turquoise, cold ones deep blue.
        "biome_water_color_contribution": 0.35,
    },
}


# --------------------------------------------------------------------------
# Fog (volumetric haze and light shafts)
# --------------------------------------------------------------------------

def haze(density, scattering, g, *, absorption=(0.0, 0.0, 0.0), floor=64.0, ceiling=224.0):
    """Air fog that is thickest in valleys and thins out with height.

    max_density_height is where it is thickest, zero_density_height where it
    is gone. Vanilla sets both to 320, which is uniform fog everywhere below
    the build limit; the gradient is what lets mountain tops stand out of the
    haze and light shafts fall into it.
    """
    return {
        "density": {"max_density": density, "max_density_height": floor,
                    "zero_density_height": ceiling},
        "media": {"scattering": list(scattering), "absorption": list(absorption)},
        "g": g,
    }


HAZE = {
    "clear": haze(0.08, (0.030, 0.036, 0.044), 0.72),
    "humid": haze(0.10, (0.050, 0.056, 0.056), 0.55, ceiling=256.0),
    "swamp": haze(0.10, (0.050, 0.056, 0.050), 0.50, absorption=(0.25, 0.13, 0.19),
                  ceiling=240.0),
    "temperate": haze(0.08, (0.036, 0.042, 0.050), 0.65, ceiling=240.0),
    "roofed": haze(0.10, (0.038, 0.046, 0.042), 0.70, ceiling=240.0),
    "cold": haze(0.06, (0.030, 0.037, 0.048), 0.70),
    "ice_spikes": haze(0.07, (0.028, 0.034, 0.046), 0.45),
    "dry": haze(0.045, (0.036, 0.032, 0.026), 0.78, ceiling=200.0),
    "mushroom": haze(0.07, (0.042, 0.030, 0.046), 0.40, absorption=(0.042, 0.137, 0.012)),
    # The End is fogged at every height, as in vanilla, but violet.
    "end": haze(0.25, (0.026, 0.016, 0.034), 0.80, floor=320.0, ceiling=320.0),
}

# Every vanilla fog file that carries a volumetric block, by the haze it gets.
# Fog files without one inherit the default below. A new vanilla fog with a
# volumetric block makes the generator stop until it is classified here.
FOG_CLASS = {
    "fog_bamboo_jungle": "humid", "fog_bamboo_jungle_hills": "humid",
    "fog_jungle": "humid", "fog_jungle_hills": "humid", "fog_jungle_mutated": "humid",
    "fog_jungle_edge": "humid", "fog_humid": "humid", "fog_lush_caves": "humid",
    "fog_mangrove_swamp": "humid",
    "fog_swampland": "swamp", "fog_swampland_mutated": "swamp",
    "fog_beach": "temperate", "fog_cold_taiga": "temperate", "fog_cold_taiga_hills": "temperate",
    "fog_cold_taiga_mutated": "temperate", "fog_deep_lukewarm_ocean": "temperate",
    "fog_deep_warm_ocean": "temperate", "fog_extreme_hills_plus_trees": "temperate",
    "fog_extreme_hills_plus_trees_mutated": "temperate", "fog_lukewarm_ocean": "temperate",
    "fog_mega_taiga": "temperate", "fog_mega_taiga_hills": "temperate",
    "fog_semi_humid": "temperate", "fog_taiga": "temperate", "fog_taiga_hills": "temperate",
    "fog_taiga_mutated": "temperate", "fog_warm_ocean": "temperate",
    "fog_roofed_forest": "roofed", "fog_roofed_forest_mutated": "roofed",
    "fog_deep_frozen_ocean": "cold", "fog_frozen_ocean": "cold", "fog_frozen_river": "cold",
    "fog_ice_mountains": "cold", "fog_ice_plains": "cold",
    "fog_ice_plains_spikes": "ice_spikes",
    "fog_desert": "dry", "fog_desert_hills": "dry", "fog_dry": "dry", "fog_mesa": "dry",
    "fog_mesa_bryce": "dry", "fog_mesa_plateau": "dry", "fog_mesa_plateau_stone": "dry",
    "fog_flower_forest": "clear", "fog_sunflower_plains": "clear",
    "fog_mushroom_island": "mushroom", "fog_mushroom_island_shore": "mushroom",
    "fog_the_end": "end",
    # Their dense fog *is* the biome; left exactly as Mojang made it.
    "fog_pale_garden": None, "fog_sulfur_caves": None,
}


def volumetric(style: dict, *, with_defaults: bool) -> dict:
    vol = {
        "density": {"air": dict(style["density"])},
        "media_coefficients": {"air": dict(style["media"])},
        "henyey_greenstein_g": {"air": {"henyey_greenstein_g": style["g"]}},
    }
    if with_defaults:
        # Rain thickens the haze (it uses the air coefficients of the biome
        # you are in). Underwater gets a clear teal-blue with ~30 blocks of
        # visibility. Biome fogs define neither, so these apply everywhere.
        vol["density"]["weather"] = {"max_density": 0.22, "max_density_height": 64.0,
                                     "zero_density_height": 280.0}
        vol["density"]["water"] = {"max_density": 0.22, "uniform": True}
        vol["media_coefficients"]["water"] = {"scattering": [0.014, 0.026, 0.034],
                                              "absorption": [0.12, 0.06, 0.05]}
        vol["henyey_greenstein_g"]["water"] = {"henyey_greenstein_g": 0.6}
    return vol


def build_fogs(vanilla: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted((vanilla / "fogs").glob("*.json")):
        data = json.loads(path.read_text())
        settings = data["minecraft:fog_settings"]
        ident = settings["description"]["identifier"].split(":", 1)[1]

        if ident == "fog_default":
            style, defaults = HAZE["clear"], True
        elif "volumetric" in settings:
            if ident not in FOG_CLASS:
                sys.exit(f"{path.name}: vanilla fog {ident} has a volumetric block but no "
                         f"entry in FOG_CLASS - classify it")
            if FOG_CLASS[ident] is None:
                continue
            style, defaults = HAZE[FOG_CLASS[ident]], False
        else:
            continue

        out[path.name] = {
            "format_version": FOG_FORMAT,
            "minecraft:fog_settings": {
                "description": settings["description"],
                "distance": settings["distance"],
                "volumetric": volumetric(style, with_defaults=defaults),
            },
        }
    return out


# --------------------------------------------------------------------------
# Coloured block light
# --------------------------------------------------------------------------

# Blocks the engine always renders as point lights (Mojang's list). Their
# colour can be changed, their type cannot.
POINT_LIGHT_BLOCKS = {
    "torch", "redstone_torch", "end_rod", "lantern", "soul_lantern", "soul_torch",
    "sea_pickle", "copper_torch",
    "copper_lantern", "exposed_copper_lantern", "weathered_copper_lantern",
    "oxidized_copper_lantern", "waxed_copper_lantern", "waxed_exposed_copper_lantern",
    "waxed_weathered_copper_lantern", "waxed_oxidized_copper_lantern",
}
CANDLE_COLORS = ["", "white_", "orange_", "magenta_", "light_blue_", "yellow_", "lime_",
                 "pink_", "gray_", "light_gray_", "cyan_", "purple_", "blue_", "brown_",
                 "green_", "red_", "black_"]
POINT_LIGHT_BLOCKS |= {f"{c}candle" for c in CANDLE_COLORS}
POINT_LIGHT_BLOCKS |= {f"{c}candle_cake" for c in CANDLE_COLORS}

# The palette Complementary uses for its coloured lighting: fire is orange, not
# vanilla's pale yellow; soul fire cyan; redstone red; ender things violet.
FIRE = "#FFA24D"
FLAME = "#FF9040"
SOUL = "#3FE0FF"
REDSTONE = "#FF3A2E"
LAVA = "#FF6A1F"
ENDER = "#A55CFF"
COPPER = "#B8EF8D"

LIGHT_COLORS = {
    "torch": "#FFB266",
    "lantern": FIRE,
    "campfire": FLAME,
    "fire": FLAME,
    "lit_furnace": FLAME,
    "lit_blast_furnace": FLAME,
    "lit_smoker": FLAME,
    "lit_pumpkin": "#FFAA55",
    "soul_torch": SOUL,
    "soul_lantern": SOUL,
    "soul_campfire": SOUL,
    "soul_fire": SOUL,
    "redstone_torch": REDSTONE,
    "lit_redstone_ore": REDSTONE,
    "lit_deepslate_redstone_ore": REDSTONE,
    "lit_redstone_lamp": "#FFB46E",
    "lava": LAVA,
    "flowing_lava": LAVA,
    "magma": "#FF5A1A",
    "glowstone": "#FFC878",
    "shroomlight": "#FF9B55",
    "sea_lantern": "#B8F0FF",
    "beacon": "#C8F8FF",
    "conduit": "#9EEBFF",
    "end_rod": "#F4E6FF",
    "end_portal": ENDER,
    "portal": ENDER,
    "crying_obsidian": ENDER,
    "respawn_anchor": "#B066FF",
    "enchanting_table": "#B28CFF",
    "ender_chest": "#9A7CFF",
    "dragon_egg": "#C77CFF",
    "amethyst_cluster": "#C98BFF",
    "large_amethyst_bud": "#C98BFF",
    "medium_amethyst_bud": "#C98BFF",
    "small_amethyst_bud": "#C98BFF",
    "ochre_froglight": "#FFD27A",
    "verdant_froglight": "#B8F29A",
    "pearlescent_froglight": "#F7B8FF",
    "glow_lichen": "#9FE8C6",
    "cave_vines_body_with_berries": "#FFB45A",
    "cave_vines_head_with_berries": "#FFB45A",
    "sea_pickle": "#C6FF9E",
    "sculk_catalyst": "#38D9D0",
    "sculk_sensor": "#38D9D0",
    "calibrated_sculk_sensor": "#38D9D0",
    "brewing_stand": "#FFD27A",
    "vault": "#FFB45A",
    "trial_spawner": "#FFB45A",
    "creaking_heart": "#FF9A3C",
    "firefly_bush": "#D8FF7A",
    "copper_torch": COPPER,
    "colored_torch_red": "#FF4040",
    "colored_torch_green": "#5CFF5C",
    "colored_torch_blue": "#5C7CFF",
    "colored_torch_purple": "#C05CFF",
}
LIGHT_COLORS.update({f"{c}candle": FIRE for c in CANDLE_COLORS})
LIGHT_COLORS.update({f"{c}candle_cake": FIRE for c in CANDLE_COLORS})
LIGHT_COLORS.update({b: COPPER for b in POINT_LIGHT_BLOCKS if b.endswith("copper_lantern")})
LIGHT_COLORS.update({f"{w}{a}copper_bulb": "#FFB070"
                     for w in ("", "waxed_") for a in ("", "exposed_", "weathered_", "oxidized_")})


def local_lighting(known_blocks: set[str] | None) -> dict:
    entries = {}
    for block, color in sorted(LIGHT_COLORS.items()):
        ident = f"minecraft:{block}"
        if known_blocks is not None and ident not in known_blocks:
            sys.exit(f"local_lighting: {ident} is not a vanilla block id")
        entries[ident] = {
            "light_color": color,
            "light_type": "point_light" if block in POINT_LIGHT_BLOCKS else "static_light",
        }
    return {"format_version": LOCAL_LIGHT_FORMAT, "minecraft:local_light_settings": entries}


# --------------------------------------------------------------------------
# Shadows and PBR fallbacks
# --------------------------------------------------------------------------

SHADOWS = {
    "format_version": SHADOW_FORMAT,
    # texel_size only matters for blocky shadows (it is the grid shadows snap
    # to, not a shadow map resolution); 16 is the engine default.
    "minecraft:shadow_settings": {"shadow_style": "soft_shadows", "texel_size": 16},
}

PBR = {
    "format_version": PBR_FORMAT,
    "minecraft:pbr_fallback_settings": {
        # [metalness, emissive, roughness, subsurface] for anything without a
        # texture set. Vanilla blocks all have texture sets; this mostly
        # decides how add-on blocks and mobs look. Mobs and add-on vehicles
        # get a faint sheen.
        "blocks": {"global_metalness_emissive_roughness_subsurface": [0, 0, 255, 0]},
        "actors": {"global_metalness_emissive_roughness_subsurface": [0, 0, 215, 0]},
        "items": {"global_metalness_emissive_roughness_subsurface": [0, 0, 255, 0]},
        "particles": {"global_metalness_emissive_roughness_subsurface": [0, 0, 255, 0]},
    },
}


# --------------------------------------------------------------------------
# Sky cubemap lighting (the cloud skyboxes drawn by tools/draw_sky.py)
# --------------------------------------------------------------------------

# How Vibrant Visuals lights the custom Overworld sky. Every biome without a
# minecraft:cubemap_identifier - all vanilla biomes - uses
# minecraft:default_cubemap, so no client biome files are needed; this is how
# shipping sky packs apply their settings too.
#
# The skyboxes are clouds on a transparent background, so these values only
# decide how the clouds are lit; the sky behind them is the atmosphere.
#  - sky light: clouds take on the colour of the sky around them
#  - directional light: they turn gold and pink at sunset with the sun
#  - atmospheric scattering: distant clouds fade into the horizon haze
#  - ambient: a small floor, lowest at night so moonlit clouds stay dim
#    grey instead of glowing
CLOUD_CUBEMAP = {
    "format_version": CUBEMAP_FORMAT,
    "minecraft:cubemap_settings": {
        "description": {"identifier": "minecraft:default_cubemap"},
        "lighting": {
            "ambient_light_illuminance": keyframes({
                0.00: 2.5, 0.22: 3.0, 0.28: 2.0, 0.36: 1.0,
                0.64: 1.0, 0.72: 2.0, 0.78: 3.0, 1.00: 2.5,
            }),
            "sky_light_contribution": 1.0,
            "directional_light_contribution": 0.3,
            "affected_by_atmospheric_scattering": True,
            "affected_by_volumetric_scattering": True,
        },
    },
}

# The engine's own defaults (Mojang's cubemap documentation). The no-clouds
# subpack carries these so it has a file at all - a subpack folder must
# exist, and git does not keep empty ones - and so that choosing it restores
# exactly the unmodified behaviour.
DEFAULT_CUBEMAP = {
    "format_version": CUBEMAP_FORMAT,
    "minecraft:cubemap_settings": {
        "description": {"identifier": "minecraft:default_cubemap"},
        "lighting": {
            "ambient_light_illuminance": keyframes({0.0: 5.625, 1.0: 5.625}),
            "sky_light_contribution": 1.0,
            "directional_light_contribution": 0.0,
            "affected_by_atmospheric_scattering": False,
            "affected_by_volumetric_scattering": True,
        },
    },
}

# Subpack folder -> cubemap settings. The folders and their order live in
# bedrock/manifest.json; the images come from tools/draw_sky.py.
SKY_SUBPACKS = {
    "no_clouds": DEFAULT_CUBEMAP,
    "high_clouds": CLOUD_CUBEMAP,
    "unbound_clouds": CLOUD_CUBEMAP,
}


# --------------------------------------------------------------------------
# Diagnostic pack: every lighting identifier turned magenta
# --------------------------------------------------------------------------

def diagnostic_lighting(identifier: str) -> dict:
    # 1.21.80 syntax only (plain ambient, no keyframed sky): the check pack
    # must be readable by any game that can run Vibrant Visuals at all.
    return lighting_file(
        identifier,
        sun_illuminance=keyframes({0.0: 3.0, 0.292: 0.0, 0.709: 0.0, 1.0: 3.0}),
        sun_color=constant([0, 255, 0]),
        moon_illuminance=keyframes({0.0: 0.0, 0.225: 0.4, 0.735: 0.4, 1.0: 0.0}),
        moon_color=constant([0, 255, 255]),
        ambient_color="#FF00FF",
        ambient_illuminance=2.0,
        flash=(10.0, [255, 255, 255]),
        sky=0.1,
        format_version="1.21.80",
        orbital_offset=0.0,
    )


# --------------------------------------------------------------------------

def vanilla_identifiers(vanilla: Path) -> dict[str, set[str]]:
    used: dict[str, set[str]] = {"atmosphere": set(), "lighting": set(), "color_grading": set(),
                                 "water": set()}
    for path in (vanilla / "biomes").glob("*.client_biome.json"):
        comps = json.loads(path.read_text())["minecraft:client_biome"]["components"]
        for kind in used:
            ident = comps.get(f"minecraft:{kind}_identifier", {}).get(f"{kind}_identifier")
            if ident:
                used[kind].add(ident)
    return used


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vanilla", type=Path, required=True,
                        help="Mojang bedrock-samples resource_pack directory")
    args = parser.parse_args()
    vanilla: Path = args.vanilla
    if not (vanilla / "biomes").is_dir() or not (vanilla / "fogs").is_dir():
        print(f"{vanilla} does not look like the vanilla resource_pack "
              "(git clone https://github.com/Mojang/bedrock-samples)")
        return 1

    blocks_file = vanilla.parent / "metadata/vanilladata_modules/mojang-blocks.json"
    known_blocks = ({b["name"] for b in json.loads(blocks_file.read_text())["data_items"]}
                    if blocks_file.is_file() else None)

    # Nothing the vanilla biomes point at may be left at vanilla.
    produced = {
        "lighting": {v["minecraft:lighting_settings"]["description"]["identifier"]
                     for v in LIGHTING.values()},
        "atmosphere": {v["minecraft:atmosphere_settings"]["description"]["identifier"]
                       for v in ATMOSPHERICS.values()},
        "color_grading": {v["minecraft:color_grading_settings"]["description"]["identifier"]
                          for v in COLOR_GRADING.values()},
        "water": {"minecraft:default_water"},
    }
    missing = {k: sorted(v - produced[k]) for k, v in vanilla_identifiers(vanilla).items()
               if v - produced[k]}
    if missing:
        print(f"vanilla biomes use identifiers this pack does not override: {missing}")
        return 1

    for folder in ("lighting", "atmospherics", "color_grading", "fogs"):
        for old in (PACK / folder).glob("*.json"):
            old.unlink()

    for name, data in LIGHTING.items():
        write(PACK / "lighting" / name, data)
    for name, data in ATMOSPHERICS.items():
        write(PACK / "atmospherics" / name, data)
    for name, data in COLOR_GRADING.items():
        write(PACK / "color_grading" / name, data)
    fogs = build_fogs(vanilla)
    for name, data in fogs.items():
        write(PACK / "fogs" / name, data)
    write(PACK / "water/water.json", WATER)
    write(PACK / "local_lighting/local_lighting.json", local_lighting(known_blocks))
    write(PACK / "shadows/global.json", SHADOWS)
    write(PACK / "pbr/global.json", PBR)
    for subpack, settings in SKY_SUBPACKS.items():
        write(PACK / "subpacks" / subpack / "cubemaps/default_cubemap.json", settings)

    for old in (DIAG / "lighting").glob("*.json"):
        old.unlink()
    for name, data in LIGHTING.items():
        ident = data["minecraft:lighting_settings"]["description"]["identifier"]
        write(DIAG / "lighting" / name, diagnostic_lighting(ident))

    print(f"bedrock/: {len(LIGHTING)} lighting, {len(ATMOSPHERICS)} atmospherics, "
          f"{len(COLOR_GRADING)} colour grading, {len(fogs)} fog, 1 water, "
          f"{len(LIGHT_COLORS)} coloured lights, {len(SKY_SUBPACKS)} sky subpacks")
    print(f"diagnostic/: {len(LIGHTING)} lighting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
