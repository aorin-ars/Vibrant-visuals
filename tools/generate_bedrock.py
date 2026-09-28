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
# 12 degrees: the noon sun stands high (78 degrees up) so shadows are short,
# but not straight overhead, where blocks would hide their own shadows.
ORBITAL_OFFSET = 12.0
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

# Where the sun actually is. Minecraft's sun does not move at a constant
# rate: its angle is eased so days run long, so keyframe 0.25 ("sunset") still
# has the sun about 12 degrees up. Elevation by keyframe, from the celestial
# angle formula (evening side; the morning mirrors it about 0.5):
#
#   0.000  90  noon            0.250  12  golden hour (reference: 夕方)
#   0.150  47                  0.265   7
#   0.200  30                  0.275   3
#   0.230  20                  0.283   0  sun on the horizon (日没); rises at 0.717 (早朝)
#   0.300  -7  civil dusk      0.330 -17  night (夜);  0.500 midnight (深夜)
#
# Vanilla's own curve agrees: its sun fades to nothing between 0.282 and 0.292.

# Clear, bright midday rather than midsummer glare: 110 at noon (vanilla 100).
# The fall-off follows the air the light crosses, not sin(elevation) - the
# engine already shades surfaces by angle - so low sun stays strong and warm.
SUN_ILLUMINANCE = mirror({
    0.000: 110.0,
    0.080: 109.0,
    0.150: 102.0,
    0.200: 88.0,
    0.230: 70.0,
    0.250: 50.0,
    0.265: 32.0,
    0.275: 18.0,
    0.282: 5.0,
    0.2915: 0.01,
    0.292: 0.0,
    0.500: 0.0,
})

# Neutral white from late morning to mid-afternoon - no yellow cast at noon.
# Warmth only arrives with low sun: gold below ~20 degrees, orange at a few
# degrees, red-orange on the horizon. Dawn is pinker and turns gold faster
# than dusk. Below the horizon the colour only feeds sky scattering, which
# paints the rose and violet of twilight.
SUN_COLOR = {
    0.000: [255, 252, 246],
    0.150: [255, 250, 242],
    0.200: [255, 240, 220],
    0.230: [255, 222, 180],
    0.250: [255, 198, 135],
    0.265: [255, 165, 95],
    0.275: [255, 130, 65],
    0.283: [255, 105, 50],
    0.300: [255, 110, 120],
    0.330: [255, 140, 150],
    0.500: [255, 110, 60],
    0.670: [255, 140, 150],
    0.700: [255, 120, 130],
    0.717: [255, 115, 55],
    0.725: [255, 140, 70],
    0.735: [255, 175, 105],
    0.750: [255, 205, 145],
    0.770: [255, 228, 190],
    0.800: [255, 242, 222],
    0.845: [255, 250, 242],
    1.000: [255, 252, 246],
}

# Moonlit nights you can see in, with a clear blue cast - vanilla's is 0.4.
MOON_ILLUMINANCE = {
    0.000: 0.0, 0.200: 0.0, 0.225: 0.5, 0.300: 0.7,
    0.700: 0.7, 0.735: 0.5, 0.750: 0.0, 1.000: 0.0,
}
MOON_COLOR = [150, 178, 255]

# Fallback light for caves and for surfaces with nothing to reflect. Kept at
# vanilla strength so caves stay dark, pale blue-white by day like the open
# sky, deep blue at night, lilac through twilight.
AMBIENT_COLOR = {
    0.000: [210, 224, 255],
    0.230: [218, 216, 240],
    0.290: [184, 170, 220],
    0.340: [128, 150, 220],
    0.660: [128, 150, 220],
    0.710: [196, 172, 214],
    0.770: [218, 218, 242],
    1.000: [210, 224, 255],
}
AMBIENT_ILLUMINANCE = {
    0.000: 0.022, 0.283: 0.020, 0.340: 0.017,
    0.660: 0.017, 0.717: 0.020, 1.000: 0.022,
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
        "minecraft:warmish_lighting", sun_tint=(1.0, 0.992, 0.975), moon_color=[128, 156, 255]),
    "hot_lighting.json": overworld_lighting(
        "minecraft:hot_lighting", sun_scale=1.04, sun_tint=(1.0, 0.985, 0.95), moon_color=[116, 146, 255]),
    "desert_lighting.json": overworld_lighting(
        "minecraft:desert_lighting", sun_scale=1.06, sun_tint=(1.0, 0.988, 0.955),
        moon_color=[116, 150, 255]),
    "mesa_lighting.json": overworld_lighting(
        "minecraft:mesa_lighting", sun_scale=1.04, sun_tint=(1.0, 0.98, 0.95),
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
RAYLEIGH = mirror({0.0: 12.0, 0.15: 11.5, 0.25: 7.0, 0.283: 6.0, 0.33: 5.5, 0.5: 5.0})

# Sun halo. Kept small at midday - clear air, only a slight softness around
# the sun - and widening as the sun gets low, into the big glow of sunset.
SUN_MIE = mirror({0.0: 0.16, 0.15: 0.20, 0.20: 0.35, 0.25: 0.80, 0.283: 1.10,
                  0.30: 0.55, 0.34: 0.0, 0.5: 0.0})
SUN_GLARE = mirror({0.0: 0.030, 0.15: 0.035, 0.20: 0.050, 0.25: 0.080, 0.283: 0.095,
                    0.30: 0.060, 0.34: 0.0, 0.5: 0.0})
MOON_MIE = {0.0: 0.0, 0.26: 0.0, 0.33: 0.15, 0.67: 0.15, 0.74: 0.0, 1.0: 0.0}

# Horizon blend: vanilla's shape, with the zenith taking over a little lower at
# midday so the deep blue reaches further down the sky.
BLEND_MIN = {0.0: 0.0, 1.0: 0.0}
BLEND_START = mirror({0.0: 0.70, 0.25: 0.50, 0.301: 0.25, 0.5: 0.25})
BLEND_MIE_START = {0.0: 0.5, 0.1: 0.5, 0.2: 1.0, 0.8: 1.0, 0.9: 0.5, 1.0: 0.5}
BLEND_MAX = {0.0: 0.25, 1.0: 0.25}

# Night is navy, not black: a lighter band at the horizon early in the night
# (夜), deepening toward midnight (深夜).
NIGHT_ZENITH = [16, 30, 74]
NIGHT_HORIZON = [40, 54, 96]
DEEP_NIGHT_ZENITH = [6, 12, 32]
DEEP_NIGHT_HORIZON = [18, 26, 48]


def sky_tables(day_zenith, day_horizon, *, dusk_zenith=(60, 58, 120),
               dawn_zenith=(48, 78, 168), twilight=None):
    """Zenith and horizon colour keyframes around one day palette.

    Stops sit at real sun elevations (see the table above SUN_ILLUMINANCE),
    and follow the reference sequence: blue noon; gold, then orange at the
    horizon with the upper sky still deep blue (夕方); red-orange horizon under
    a violet sky at sunset (日没); rose and violet twilight; navy night.
    Dawn has its own colours: magenta turning orange-gold under a deep blue
    sky (早朝), then a warm cream horizon in a blue morning sky (朝).
    """
    t = twilight or {}
    day_zenith, day_horizon = list(day_zenith), list(day_horizon)
    dusk_zenith, dawn_zenith = list(dusk_zenith), list(dawn_zenith)
    golden = t.get("golden", [255, 176, 100])
    morning = t.get("morning", [252, 222, 176])
    zenith = {
        0.000: day_zenith,
        0.200: lerp_rgb(day_zenith, dusk_zenith, 0.1),
        0.250: lerp_rgb(day_zenith, dusk_zenith, 0.6),
        0.283: dusk_zenith,
        0.300: t.get("zenith_dusk", [40, 40, 96]),
        0.330: NIGHT_ZENITH,
        0.400: DEEP_NIGHT_ZENITH,
        0.600: DEEP_NIGHT_ZENITH,
        0.670: NIGHT_ZENITH,
        0.700: t.get("zenith_dawn", [40, 56, 128]),
        0.717: dawn_zenith,
        0.750: lerp_rgb(dawn_zenith, day_zenith, 0.6),
        0.800: lerp_rgb(day_zenith, dawn_zenith, 0.1),
        1.000: day_zenith,
    }
    horizon = {
        0.000: day_horizon,
        0.167: day_horizon,
        0.210: lerp_rgb(day_horizon, golden, 0.35),
        0.235: lerp_rgb(day_horizon, golden, 0.7),
        0.250: golden,
        0.265: t.get("sunset", [255, 150, 70]),
        0.278: t.get("sunset_deep", [250, 112, 46]),
        0.290: t.get("afterglow", [230, 100, 70]),
        0.300: t.get("rose", [190, 96, 120]),
        0.315: t.get("violet", [120, 90, 150]),
        0.340: NIGHT_HORIZON,
        0.400: DEEP_NIGHT_HORIZON,
        0.600: DEEP_NIGHT_HORIZON,
        0.660: NIGHT_HORIZON,
        0.685: t.get("violet_dawn", [100, 86, 150]),
        0.700: t.get("magenta_dawn", [170, 100, 140]),
        0.712: t.get("sunrise", [245, 130, 80]),
        0.720: t.get("sunrise_gold", [255, 160, 80]),
        0.735: lerp_rgb(t.get("sunrise_gold", [255, 160, 80]), morning, 0.5),
        0.750: morning,
        0.770: lerp_rgb(morning, day_horizon, 0.6),
        0.800: lerp_rgb(morning, day_horizon, 0.9),
        0.833: day_horizon,
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
                         dusk_zenith=(60, 58, 120), dawn_zenith=(48, 78, 168), **kw) -> dict:
    zenith, horizon = sky_tables(day_zenith, day_horizon, dusk_zenith=dusk_zenith,
                                 dawn_zenith=dawn_zenith, twilight=twilight)
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


# Deep vivid blue overhead fading to a pale, clear blue at the horizon - a
# clean midday gradient, saturated but short of a blue filter.
DAY_ZENITH = [44, 104, 214]
DAY_HORIZON = [186, 214, 244]

DESERT_TWILIGHT = {"golden": [255, 196, 128], "sunset": [255, 164, 88],
                   "sunset_deep": [255, 128, 60], "rose": [214, 110, 104]}

ATMOSPHERICS = {
    "atmospherics.json": overworld_atmosphere(
        "minecraft:default_atmospherics", DAY_ZENITH, DAY_HORIZON),
    "warmish_atmospherics.json": overworld_atmosphere(
        "minecraft:warmish_atmospherics", [46, 106, 210], [192, 216, 238]),
    "hot_atmospherics.json": overworld_atmosphere(
        "minecraft:hot_atmospherics", [56, 118, 208], [206, 212, 206], twilight=DESERT_TWILIGHT),
    "desert_atmospherics.json": overworld_atmosphere(
        "minecraft:desert_atmospherics", [60, 122, 208], [208, 210, 200], twilight=DESERT_TWILIGHT,
        mie_scale=1.15),
    "mesa_atmospherics.json": overworld_atmosphere(
        "minecraft:mesa_atmospherics", [58, 126, 204], [212, 208, 192], twilight=DESERT_TWILIGHT,
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
        "minecraft:roofed_forest_atmospherics", [44, 98, 196], [180, 204, 232]),
    "mushroom_island_atmospherics.json": overworld_atmosphere(
        "minecraft:mushroom_island_atmospherics", [110, 124, 196], [214, 212, 236],
        twilight={"sunset": [255, 120, 150], "sunset_deep": [240, 100, 150],
                  "rose": [200, 100, 170], "violet": [140, 90, 190]}),
    # Overcast and colourless, like vanilla intends, with no sun halo at all.
    "pale_garden_atmospherics.json": overworld_atmosphere(
        "minecraft:pale_garden_atmospherics", [128, 134, 142], [196, 196, 190],
        dusk_zenith=(96, 100, 110), dawn_zenith=(96, 100, 110), mie_scale=0.0, rayleigh_scale=0.5,
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

# Vanilla: contrast 1.15, saturation 1.05. Here: moderate contrast so shadows
# stay readable, saturation a little above natural, and a slightly lifted
# gamma (2.3 against the standard 2.2) for a bright exposure that still keeps
# detail in the whites. Highlights are left neutral - direct sun is white -
# and only the shadows lean a touch toward blue-grey.
BASE_GRADE = {"contrast": 1.14, "saturation": 1.12, "gain": (1.0, 1.0, 1.0)}
GAMMA = 2.3


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
                    "gamma": [GAMMA, GAMMA, GAMMA],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [s, s, s],
                },
                "shadows": {
                    "enabled": True,
                    "shadowsMax": 0.45,
                    "contrast": [1.0, 1.0, 1.0],
                    "gain": [0.98, 1.0, 1.03],
                    "gamma": [GAMMA, GAMMA, GAMMA],
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


def toward_neutral(kelvin: float, keep: float = 0.4) -> float:
    """Vanilla tints biomes hard (desert 4400 K, ice spikes 11000 K), which
    puts a colour filter over the whole screen. Keep 40 % of vanilla's shift:
    enough for a biome to feel different, not enough to tint daylight."""
    return round(6500.0 + (kelvin - 6500.0) * keep)


COLOR_GRADING = {
    "color_grading.json": grading("minecraft:default_color_grading"),
    "cold_color_grading.json": grading(
        "minecraft:cold_color_grading", temperature=toward_neutral(10000), saturation=1.08),
    "coolish_color_grading.json": grading(
        "minecraft:coolish_color_grading", temperature=toward_neutral(9000), saturation=1.10),
    "warmish_color_grading.json": grading(
        "minecraft:warmish_color_grading", temperature=toward_neutral(4800), saturation=1.13),
    "hot_color_grading.json": grading(
        "minecraft:hot_color_grading", temperature=toward_neutral(4000), contrast=1.18),
    "desert_color_grading.json": grading(
        "minecraft:desert_color_grading", temperature=toward_neutral(4400), saturation=1.10),
    "mesa_color_grading.json": grading(
        "minecraft:mesa_color_grading", temperature=toward_neutral(4800), saturation=1.12),
    "ice_plains_spikes_color_grading.json": grading(
        "minecraft:ice_plains_spikes_color_grading", temperature=toward_neutral(11000),
        saturation=1.06),
    "lush_caves_color_grading.json": grading(
        "minecraft:lush_caves_color_grading", temperature=toward_neutral(4800), contrast=1.18,
        saturation=1.16),
    "mangrove_swamp_color_grading.json": grading(
        "minecraft:mangrove_swamp_color_grading", temperature=toward_neutral(5125)),
    "mushroom_island_color_grading.json": grading(
        "minecraft:mushroom_island_color_grading", saturation=1.16),
    "pale_garden_color_grading.json": grading(
        "minecraft:pale_garden_color_grading", temperature=toward_neutral(9000),
        saturation=0.85, contrast=1.12),
    "roofed_forest_color_grading.json": grading(
        "minecraft:roofed_forest_color_grading", contrast=1.18, saturation=1.10),
    "swampland_color_grading.json": grading(
        "minecraft:swampland_color_grading", saturation=1.06),
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


# Clear air first: just enough haze to soften the far distance and let the
# light read as passing through air, never enough to grey the picture. Humid
# and swampy biomes keep a little more, as their character.
HAZE = {
    "clear": haze(0.03, (0.030, 0.036, 0.044), 0.72, ceiling=200.0),
    "humid": haze(0.05, (0.050, 0.056, 0.056), 0.55, ceiling=240.0),
    "swamp": haze(0.06, (0.050, 0.056, 0.050), 0.50, absorption=(0.25, 0.13, 0.19),
                  ceiling=240.0),
    "temperate": haze(0.035, (0.036, 0.042, 0.050), 0.65, ceiling=220.0),
    "roofed": haze(0.05, (0.038, 0.046, 0.042), 0.70, ceiling=220.0),
    "cold": haze(0.03, (0.030, 0.037, 0.048), 0.70, ceiling=200.0),
    "ice_spikes": haze(0.035, (0.028, 0.034, 0.046), 0.45, ceiling=200.0),
    "dry": haze(0.02, (0.036, 0.032, 0.026), 0.78, ceiling=180.0),
    "mushroom": haze(0.04, (0.042, 0.030, 0.046), 0.40, absorption=(0.042, 0.137, 0.012)),
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
#  - ambient: a small floor. Lowest late at night, so moonlit clouds stay
#    dim blue-grey instead of glowing (夜, 深夜); low at dawn, when clouds are
#    dark silhouettes against the brightening sky (早朝); highest with the
#    low golden sun of late afternoon (夕方). Keyframes sit at real sun
#    elevations, as in the lighting tables.
CLOUD_CUBEMAP = {
    "format_version": CUBEMAP_FORMAT,
    "minecraft:cubemap_settings": {
        "description": {"identifier": "minecraft:default_cubemap"},
        "lighting": {
            "ambient_light_illuminance": keyframes({
                0.000: 2.5, 0.250: 3.0, 0.283: 2.2, 0.300: 1.6, 0.330: 1.1,
                0.400: 0.7, 0.600: 0.7, 0.670: 1.1, 0.700: 1.0, 0.717: 1.2,
                0.750: 2.6, 1.000: 2.5,
            }),
            "sky_light_contribution": 1.0,
            "directional_light_contribution": 0.4,
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
