#!/usr/bin/env python3
"""Generate every Vibrant Visuals settings file in bedrock/ (and diagnostic/).

    tools/generate_bedrock.py --vanilla <bedrock-samples>/resource_pack

The look is modelled on Complementary Unbound: a filmic (ACES) picture, a
strong sun against deeper blue-grey shade, a blue sky that pales toward the
horizon with a bright halo around the sun, pastel pink and lavender sunsets,
dark navy moonlit nights, a visible haze that fills valleys and caves and
turns into light shafts, clear water, and coloured block light.

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
# ACES, not vanilla's "generic": the filmic curve is most of what makes a
# picture read as "shader" rather than stock Vibrant Visuals - a firm toe for
# shade, rich midtones, and bright skies and sunsets rolling off smoothly
# instead of flattening out.
TONE_MAP = "aces"

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

# Clear sun at vanilla strength, 100 at noon. 125 blew out sunlit walls and
# the sky in game once the ACES curve and the grade's gain were on top; the
# contrast with the shade comes from the reduced sky light below instead.
# The fall-off follows the air the light crosses, not sin(elevation) - the
# engine already shades surfaces by angle - so low sun stays strong and warm.
SUN_ILLUMINANCE = mirror({
    0.000: 100.0,
    0.080: 99.0,
    0.150: 94.0,
    0.200: 84.0,
    0.230: 70.0,
    0.250: 53.0,
    0.265: 35.0,
    0.275: 20.0,
    0.282: 5.5,
    0.2915: 0.01,
    0.292: 0.0,
    0.500: 0.0,
})

# Neutral white from late morning to mid-afternoon - no yellow cast at noon.
# Warmth only arrives with low sun: gold below ~20 degrees, orange at a few
# degrees, deep orange on the horizon - golden rather than red, as in
# Complementary's sunsets, where the land glows warm instead of dimming.
# Dawn is pinker and turns gold faster than dusk. Below the horizon the
# colour only feeds sky scattering, which paints the rose and violet of
# twilight.
SUN_COLOR = {
    0.000: [255, 248, 236],
    0.150: [255, 246, 232],
    0.200: [255, 240, 220],
    0.230: [255, 222, 180],
    0.250: [255, 198, 135],
    0.265: [255, 172, 104],
    0.275: [255, 146, 84],
    0.283: [255, 124, 70],
    0.300: [255, 110, 120],
    0.330: [255, 140, 150],
    0.500: [255, 110, 60],
    0.670: [255, 140, 150],
    0.700: [255, 120, 130],
    0.717: [255, 128, 72],
    0.725: [255, 150, 86],
    0.735: [255, 180, 112],
    0.750: [255, 205, 145],
    0.770: [255, 228, 190],
    0.800: [255, 242, 222],
    0.845: [255, 246, 232],
    1.000: [255, 248, 236],
}

# Blue moonlight that fades into a real, dark night. Early in the night it
# is 0.6 (vanilla 0.4 all night): moonlit faces stand out blue against dark
# shade and the valley haze glows a faint blue, as in Complementary's
# evenings. Toward midnight (深夜) it sinks to 0.2, half of vanilla's, so the
# deep night is dark the way a real one is - shapes in faint blue-grey,
# shade close to black - while torches and other block light, which this
# does not touch, stand out in it. At 1.0 all night, midnight looked like
# dusk.
MOON_ILLUMINANCE = {
    0.000: 0.0, 0.200: 0.0, 0.225: 0.4, 0.300: 0.6, 0.360: 0.32, 0.400: 0.2,
    0.600: 0.2, 0.640: 0.32, 0.700: 0.6, 0.735: 0.4, 0.750: 0.0, 1.000: 0.0,
}
MOON_COLOR = [124, 160, 255]

# How much the sky lights the shade (0.1-1.0; vanilla 1.0 all day). Full sky
# light is what gives stock Vibrant Visuals its flat, evenly grey look; well
# under half the gap between sunlit and shaded faces is back at 0.6, so
# shadows read as shadows while staying blue-grey rather than black. More sky
# light at sunset, when the glowing sky is the main light; least at night,
# when the moon should do the lighting.
SKY_INTENSITY = mirror({
    0.000: 0.60, 0.200: 0.62, 0.250: 0.68, 0.283: 0.75, 0.300: 0.72,
    0.330: 0.58, 0.360: 0.45, 0.400: 0.30, 0.500: 0.30,
})

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
    0.000: 0.022, 0.283: 0.020, 0.340: 0.017, 0.400: 0.013,
    0.600: 0.013, 0.660: 0.017, 0.717: 0.020, 1.000: 0.022,
}


def overworld_lighting(identifier: str, *, sun_scale=1.0, sun_tint=(1, 1, 1),
                       moon_color=MOON_COLOR, ambient_tint=(1, 1, 1),
                       sun_color_override=None, sky=None) -> dict:
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
        sky=keyframes(SKY_INTENSITY) if sky is None else sky,
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
        "minecraft:warmish_lighting", sun_tint=(1.0, 0.992, 0.975), moon_color=[118, 152, 255]),
    "hot_lighting.json": overworld_lighting(
        "minecraft:hot_lighting", sun_scale=1.04, sun_tint=(1.0, 0.985, 0.95), moon_color=[108, 142, 255]),
    "desert_lighting.json": overworld_lighting(
        "minecraft:desert_lighting", sun_scale=1.06, sun_tint=(1.0, 0.988, 0.955),
        moon_color=[108, 146, 255]),
    "mesa_lighting.json": overworld_lighting(
        "minecraft:mesa_lighting", sun_scale=1.04, sun_tint=(1.0, 0.98, 0.95),
        moon_color=[118, 152, 255]),
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
    # Keep the mood, just enough light to see the shapes - and full sky
    # light, since an overcast sky is the only light it has.
    "pale_garden_lighting.json": overworld_lighting(
        "minecraft:pale_garden_lighting", sun_scale=0.08,
        sun_color_override=[200, 214, 240], moon_color=[210, 220, 255],
        ambient_tint=(0.98, 1.0, 1.0), sky=1.0),
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

# Rayleigh strength. Vanilla runs it at 10 by day, which saturates the whole
# dome into one flat, even blue - a large part of the stock look. Around 1
# (the scale of Mojang's own documentation example) the zenith and horizon
# colours below come through as a real gradient: blue overhead, paling toward
# the horizon, and lit by the sun's colour, so sunsets tint the whole sky.
RAYLEIGH = mirror({0.0: 1.30, 0.15: 1.30, 0.20: 1.20, 0.25: 1.15, 0.283: 1.15,
                   0.30: 1.05, 0.33: 1.30, 0.40: 1.60, 0.5: 1.60})

# The glow around the sun. sun_glare_shape is the tightness of that lobe:
# vanilla's ~0.05 spreads it over half the sky as a milky haze; values of a
# few units gather it into a bright halo around the sun, as in
# Complementary - small at noon (at 8 and twice this strength the first
# in-game test showed a large white blotch round the sun), spreading into a
# big warm glow as the sun sets. The same lobe shapes the moon's glow at
# night.
SUN_MIE = mirror({0.0: 0.22, 0.15: 0.26, 0.20: 0.40, 0.25: 0.90, 0.283: 1.50,
                  0.30: 0.80, 0.34: 0.0, 0.5: 0.0})
SUN_GLARE = mirror({0.0: 12.0, 0.15: 10.0, 0.20: 7.0, 0.25: 4.5, 0.283: 3.2,
                    0.30: 3.5, 0.34: 5.0, 0.5: 5.0})
MOON_MIE = {0.0: 0.0, 0.27: 0.0, 0.33: 0.40, 0.67: 0.40, 0.73: 0.0, 1.0: 0.0}

# Horizon blend: vanilla's shape, with the zenith taking over a little lower at
# midday so the deep blue reaches further down the sky.
BLEND_MIN = {0.0: 0.0, 1.0: 0.0}
BLEND_START = mirror({0.0: 0.70, 0.25: 0.50, 0.301: 0.25, 0.5: 0.25})
BLEND_MIE_START = {0.0: 0.5, 0.1: 0.5, 0.2: 1.0, 0.8: 1.0, 0.9: 0.5, 1.0: 0.5}
BLEND_MAX = {0.0: 0.25, 1.0: 0.25}

# Early night (夜) is navy with a lighter band at the horizon; toward
# midnight (深夜) the sky goes nearly black-blue, as a real night sky does
# away from city lights. A little brighter than the colours would need at
# vanilla's night Rayleigh (5), since this pack's is 1.6.
NIGHT_ZENITH = [20, 36, 92]
NIGHT_HORIZON = [46, 64, 118]
DEEP_NIGHT_ZENITH = [5, 9, 27]
DEEP_NIGHT_HORIZON = [12, 18, 38]

# Complementary's sunset: the whole sky turns pastel - lavender overhead,
# peach to coral-pink at the horizon, rose and violet after the sun is gone.
DUSK_ZENITH = (126, 110, 184)
DAWN_ZENITH = (104, 116, 192)


def sky_tables(day_zenith, day_horizon, *, dusk_zenith=DUSK_ZENITH,
               dawn_zenith=DAWN_ZENITH, twilight=None):
    """Zenith and horizon colour keyframes around one day palette.

    Stops sit at real sun elevations (see the table above SUN_ILLUMINANCE):
    blue noon; a gold, then peach horizon under a softening blue as the sun
    gets low (夕方); coral-pink horizon under a lavender sky with the sun on
    the horizon (日没); rose and violet twilight; navy night. Dawn has its own
    colours: magenta turning orange-gold under a blue-violet sky (早朝), then
    a warm cream horizon in a blue morning sky (朝).
    """
    t = twilight or {}
    day_zenith, day_horizon = list(day_zenith), list(day_horizon)
    dusk_zenith, dawn_zenith = list(dusk_zenith), list(dawn_zenith)
    golden = t.get("golden", [255, 196, 128])
    morning = t.get("morning", [255, 222, 186])
    zenith = {
        0.000: day_zenith,
        0.200: lerp_rgb(day_zenith, dusk_zenith, 0.1),
        0.250: lerp_rgb(day_zenith, dusk_zenith, 0.55),
        0.283: dusk_zenith,
        0.300: t.get("zenith_dusk", [70, 62, 138]),
        0.330: NIGHT_ZENITH,
        0.400: DEEP_NIGHT_ZENITH,
        0.600: DEEP_NIGHT_ZENITH,
        0.670: NIGHT_ZENITH,
        0.700: t.get("zenith_dawn", [48, 60, 132]),
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
        0.265: t.get("sunset", [255, 166, 112]),
        0.278: t.get("sunset_deep", [255, 136, 100]),
        0.290: t.get("afterglow", [246, 116, 120]),
        0.300: t.get("rose", [200, 104, 150]),
        0.315: t.get("violet", [128, 92, 170]),
        0.340: NIGHT_HORIZON,
        0.400: DEEP_NIGHT_HORIZON,
        0.600: DEEP_NIGHT_HORIZON,
        0.660: NIGHT_HORIZON,
        0.685: t.get("violet_dawn", [100, 88, 160]),
        0.700: t.get("magenta_dawn", [184, 108, 152]),
        0.712: t.get("sunrise", [255, 146, 112]),
        0.720: t.get("sunrise_gold", [255, 178, 116]),
        0.735: lerp_rgb(t.get("sunrise_gold", [255, 178, 116]), morning, 0.5),
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
                         dusk_zenith=DUSK_ZENITH, dawn_zenith=DAWN_ZENITH, **kw) -> dict:
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


# Complementary's clear-day sky: a clean mid blue overhead fading to a pale
# blue at the horizon, with a small bright halo around the sun.
DAY_ZENITH = [88, 146, 224]
DAY_HORIZON = [184, 208, 236]

DESERT_TWILIGHT = {"golden": [255, 204, 146], "sunset": [255, 176, 112],
                   "sunset_deep": [255, 146, 96], "rose": [212, 112, 128]}

ATMOSPHERICS = {
    "atmospherics.json": overworld_atmosphere(
        "minecraft:default_atmospherics", DAY_ZENITH, DAY_HORIZON),
    "warmish_atmospherics.json": overworld_atmosphere(
        "minecraft:warmish_atmospherics", [80, 142, 228], [194, 218, 240]),
    "hot_atmospherics.json": overworld_atmosphere(
        "minecraft:hot_atmospherics", [92, 150, 226], [206, 220, 232], twilight=DESERT_TWILIGHT),
    "desert_atmospherics.json": overworld_atmosphere(
        "minecraft:desert_atmospherics", [96, 152, 224], [212, 222, 230], twilight=DESERT_TWILIGHT,
        mie_scale=1.15),
    "mesa_atmospherics.json": overworld_atmosphere(
        "minecraft:mesa_atmospherics", [96, 150, 220], [214, 216, 216], twilight=DESERT_TWILIGHT,
        mie_scale=1.1),
    "ice_plains_spikes_atmospherics.json": overworld_atmosphere(
        "minecraft:ice_plains_spikes_atmospherics", [120, 164, 230], [206, 224, 244],
        twilight={"golden": [240, 216, 214], "sunset": [232, 186, 196],
                  "sunset_deep": [212, 164, 204], "rose": [172, 140, 204]}),
    "mangrove_swamp_atmospherics.json": overworld_atmosphere(
        "minecraft:mangrove_swamp_atmospherics", [104, 146, 200], [186, 206, 214]),
    "swampland_atmospherics.json": overworld_atmosphere(
        "minecraft:swampland_atmospherics", [110, 140, 166], [184, 196, 192], mie_scale=0.8),
    "roofed_forest_atmospherics.json": overworld_atmosphere(
        "minecraft:roofed_forest_atmospherics", [74, 136, 226], [184, 212, 240]),
    "mushroom_island_atmospherics.json": overworld_atmosphere(
        "minecraft:mushroom_island_atmospherics", [124, 136, 204], [222, 216, 238],
        twilight={"sunset": [255, 130, 160], "sunset_deep": [244, 108, 160],
                  "rose": [204, 104, 176], "violet": [144, 92, 194]}),
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

# Vanilla: contrast 1.15, saturation 1.05 through the "generic" curve. The
# ACES curve (TONE_MAP) already deepens contrast and enriches midtone colour,
# so the grade on top of it is milder than a "generic" one would need: a
# touch more contrast and saturation - less than it first had: next to
# Complementary's screenshots, 1.20 turned leaves lime. No extra gain: at
# 1.08 sunlit grass rolled off into pastel in the first in-game test, and
# even 1.02 helped blow out bright daytime surfaces. Standard gamma: a lifted
# gamma washed the picture out in game. Shadows lean cool, highlights a touch
# warm, as in the sunlit reference.
BASE_GRADE = {"contrast": 1.10, "saturation": 1.10, "gain": (1.0, 1.0, 1.0)}
GAMMA = 2.2
# A little cooler than neutral daylight (6500 K), for the clean, slightly
# blue cast of Complementary's daytime: greens lean toward blue-green instead
# of lime, stone and water read cool.
BASE_TEMPERATURE = 6100.0


def grading(identifier, *, temperature=BASE_TEMPERATURE, contrast=None, saturation=None,
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
                    "gain": [0.96, 1.0, 1.07],
                    "gamma": [GAMMA, GAMMA, GAMMA],
                    "offset": [0.0, 0.0, 0.0],
                    "saturation": [1.04, 1.04, 1.04],
                },
                "highlights": {
                    "enabled": True,
                    "highlightsMin": 1.8,
                    "contrast": [1.0, 1.0, 1.0],
                    # Warm, but no brighter: a gain above 1 here pushed
                    # sunlit faces and the sky into white.
                    "gain": [1.0, 0.98, 0.94],
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
    return round(BASE_TEMPERATURE + (kelvin - 6500.0) * keep)


COLOR_GRADING = {
    "color_grading.json": grading("minecraft:default_color_grading"),
    "cold_color_grading.json": grading(
        "minecraft:cold_color_grading", temperature=toward_neutral(10000), saturation=1.00),
    "coolish_color_grading.json": grading(
        "minecraft:coolish_color_grading", temperature=toward_neutral(9000), saturation=1.03),
    "warmish_color_grading.json": grading(
        "minecraft:warmish_color_grading", temperature=toward_neutral(4800), saturation=1.08),
    "hot_color_grading.json": grading(
        "minecraft:hot_color_grading", temperature=toward_neutral(4000), contrast=1.12),
    "desert_color_grading.json": grading(
        "minecraft:desert_color_grading", temperature=toward_neutral(4400), saturation=1.02),
    "mesa_color_grading.json": grading(
        "minecraft:mesa_color_grading", temperature=toward_neutral(4800), saturation=1.04),
    "ice_plains_spikes_color_grading.json": grading(
        "minecraft:ice_plains_spikes_color_grading", temperature=toward_neutral(11000),
        saturation=0.98),
    "lush_caves_color_grading.json": grading(
        "minecraft:lush_caves_color_grading", temperature=toward_neutral(4800), contrast=1.12,
        saturation=1.10),
    "mangrove_swamp_color_grading.json": grading(
        "minecraft:mangrove_swamp_color_grading", temperature=toward_neutral(5125)),
    "mushroom_island_color_grading.json": grading(
        "minecraft:mushroom_island_color_grading", saturation=1.10),
    "pale_garden_color_grading.json": grading(
        "minecraft:pale_garden_color_grading", temperature=toward_neutral(9000),
        saturation=0.80, contrast=1.04),
    "roofed_forest_color_grading.json": grading(
        "minecraft:roofed_forest_color_grading", contrast=1.12, saturation=1.02),
    "swampland_color_grading.json": grading(
        "minecraft:swampland_color_grading", saturation=0.98),
}


# --------------------------------------------------------------------------
# Water
# --------------------------------------------------------------------------

WATER = {
    "format_version": WATER_FORMAT,
    "minecraft:water_settings": {
        "description": {"identifier": "minecraft:default_water"},
        # Clear water: nothing in it but water, so the bottom and plants
        # show through and only depth tints it blue.
        "particle_concentrations": {
            "chlorophyll": 0.0,
            "suspended_sediment": 0.0,
            "cdom": 0.0,
        },
        # Gentle ripples. With vanilla's normal map gone (tools/draw_water.py)
        # these are the only thing shaping the surface, and small, slow
        # waves bend reflections of the sky and shore without breaking them.
        "waves": {
            "enabled": True,
            "depth": 0.35,
            "frequency": 1.2,
            "frequency_scaling": 1.15,
            "mix": 0.25,
            "octaves": 20,
            "pull": 0.3,
            "shape": 1.3,
            "speed": 1.2,
            "speed_scaling": 1.04,
        },
        "caustics": {
            "enabled": True,
            "frame_length": 0.07,
            "power": 2,
            "scale": 0.5,
        },
        # A hint of the biome's water colour (swamps greener, warm oceans
        # more turquoise) without turning oceans an opaque navy.
        "biome_water_color_contribution": 0.12,
    },
}


# --------------------------------------------------------------------------
# Fog (volumetric haze and light shafts)
# --------------------------------------------------------------------------

def haze(density, scattering, g, *, absorption=0.0, floor=62.0, ceiling=170.0):
    """Air fog that is thickest in valleys and thins out with height.

    max_density_height is where it is thickest (sea level, and everything
    below it: caves get the full density), zero_density_height where it is
    gone. Vanilla sets both to 320, which is uniform fog everywhere below the
    build limit; the gradient is what lets mountain tops stand out of the
    haze and light shafts fall into valleys and caves.

    How thick it looks goes roughly with density x (scattering + absorption)
    per block: 0.055 x 0.049 is about 0.0027, a haze that takes a quarter of
    the colour out of terrain about 100 blocks away at sea level - the clear
    but deep air of Complementary's landscapes. Vanilla has 0.05 x 0.06 in a few
    biomes, evenly at every height, and none elsewhere.

    Vibrant Visuals uses only the brightness of an absorption colour, so it
    is given as one number. The colour of the haze comes from scattering:
    slightly blue for clear air, as real haze is.
    """
    return {
        "density": {"max_density": density, "max_density_height": floor,
                    "zero_density_height": ceiling},
        "media": {"scattering": list(scattering), "absorption": [absorption] * 3},
        "g": g,
    }


# Complementary's air: a haze that softens distance to a clear blue, glows
# gold toward a low sun and faint blue under the moon, fills valleys and
# caves, and turns into light shafts where the light falls through leaves or
# cave openings. Blue scatters about twice as much as red, as in real air, so
# distance turns blue rather than milky white. Humid forests and swamps are
# mistier, deserts clearer.
#
# g (the last number) decides from where the shafts can be seen. Light
# shafts are sunlit air next to air in shadow; how bright the sunlit part
# looks depends on the angle to the sun. At g 0.5 air seen at right angles
# to the sun is a tenth as bright as air toward it, so shafts through leaves
# vanished as soon as the sun was out of view. At 0.3 it is a third - the
# shafts stay visible whenever the light's direction lets them form, not
# only when looking into the sun - while the white glare toward the sun
# halves. The densities are a little higher than before to keep the shafts
# strong; the first in-game test, at 0.09 and g 0.5, washed nearby hills
# out to white looking toward the sun.
HAZE = {
    "clear": haze(0.055, (0.032, 0.046, 0.068), 0.30),
    "humid": haze(0.09, (0.042, 0.052, 0.062), 0.30, ceiling=190.0),
    "swamp": haze(0.10, (0.046, 0.054, 0.044), 0.30, absorption=0.06, ceiling=150.0),
    "temperate": haze(0.06, (0.032, 0.046, 0.066), 0.32, ceiling=180.0),
    "roofed": haze(0.11, (0.040, 0.050, 0.052), 0.35),
    "cold": haze(0.05, (0.034, 0.047, 0.070), 0.30),
    "ice_spikes": haze(0.07, (0.038, 0.050, 0.070), 0.30),
    "dry": haze(0.045, (0.046, 0.046, 0.044), 0.30, ceiling=150.0),
    # Complementary's savanna: a warmer, brighter haze over the distance.
    "savanna": haze(0.07, (0.048, 0.048, 0.046), 0.30),
    "mushroom": haze(0.06, (0.050, 0.036, 0.052), 0.30, absorption=0.02, ceiling=160.0),
    # The End is fogged at every height, as in vanilla, but violet.
    "end": haze(0.25, (0.026, 0.016, 0.034), 0.80, floor=320.0, ceiling=320.0),
    # No air fog at all, which is what vanilla's Nether has.
    "none": haze(0.0, (0.0, 0.0, 0.0), 0.75, floor=320.0, ceiling=320.0),
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

# Vanilla fog files *without* a volumetric block that get one here. A biome
# fog is read on top of fog_default, so without an entry of their own the
# Nether biomes would inherit the Overworld haze; they get explicitly none,
# as in vanilla. Savannas get their own warm haze.
FOG_EXTRA = {
    "fog_savanna": "savanna", "fog_savanna_mutated": "savanna", "fog_savanna_plateau": "savanna",
    "fog_hell": "none", "fog_crimson_forest": "none", "fog_warped_forest": "none",
    "fog_soulsand_valley": "none", "fog_basalt_deltas": "none",
}


def volumetric(style: dict, *, with_defaults: bool) -> dict:
    vol = {
        "density": {"air": dict(style["density"])},
        "media_coefficients": {"air": dict(style["media"])},
        "henyey_greenstein_g": {"air": {"henyey_greenstein_g": style["g"]}},
    }
    if with_defaults:
        # Rain thickens the haze (it uses the air coefficients of the biome
        # you are in). Biome fogs do not define it, so this applies
        # everywhere. Underwater is deliberately left to the game: a
        # volumetric water medium made the player's own shadow show up as a
        # dark shape in front of the camera when swimming.
        vol["density"]["weather"] = dict(RAIN_HAZE)
    return vol


# The rainy day of a well-known Java shader showcase (the one reproduced on
# request): an even, light blue-grey mist that softens things a few dozen
# blocks away and swallows the far distance, so trees stand as grey
# silhouettes against a grey sky. Two parts, both only active while it
# rains:
#  - the volumetric haze thickens and reaches higher, so hills are in it too;
#  - the distance fog for weather closes in, pale blue-grey rather than
#    vanilla's dark #666666, so the far distance fades into mist rather than
#    into gloom. As a share of the render distance: begins at 6 %, complete
#    at 62 % - at 12 chunks, about 12 and 120 blocks.
# The overcast sky and soft, shadowless light of rain are the game's own; a
# pack has no per-weather lighting.
RAIN_HAZE = {"max_density": 0.30, "max_density_height": 64.0, "zero_density_height": 300.0}
RAIN_DISTANCE_FOG = {"fog_start": 0.06, "fog_end": 0.62, "fog_color": "#8C939C",
                     "render_distance_type": "render"}


def build_fogs(vanilla: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    extra_seen = set()
    for path in sorted((vanilla / "fogs").glob("*.json")):
        data = json.loads(path.read_text())
        settings = data["minecraft:fog_settings"]
        ident = settings["description"]["identifier"].split(":", 1)[1]

        if ident == "fog_default":
            style, defaults = HAZE["clear"], True
        elif "volumetric" in settings:
            if ident in FOG_EXTRA:
                sys.exit(f"{path.name}: vanilla fog {ident} now has a volumetric block - "
                         f"move it from FOG_EXTRA to FOG_CLASS")
            if ident not in FOG_CLASS:
                sys.exit(f"{path.name}: vanilla fog {ident} has a volumetric block but no "
                         f"entry in FOG_CLASS - classify it")
            if FOG_CLASS[ident] is None:
                continue
            style, defaults = HAZE[FOG_CLASS[ident]], False
        elif ident in FOG_EXTRA:
            extra_seen.add(ident)
            style, defaults = HAZE[FOG_EXTRA[ident]], False
        else:
            continue

        distance = dict(settings["distance"])
        # Overworld fogs only: the Nether's and the End's weather fog stays.
        if (ident == "fog_default" or "weather" in distance) and style is not HAZE["none"] \
                and style is not HAZE["end"]:
            distance["weather"] = dict(RAIN_DISTANCE_FOG)
        out[path.name] = {
            "format_version": FOG_FORMAT,
            "minecraft:fog_settings": {
                "description": settings["description"],
                "distance": distance,
                "volumetric": volumetric(style, with_defaults=defaults),
            },
        }
    if set(FOG_EXTRA) - extra_seen:
        sys.exit(f"FOG_EXTRA names fogs vanilla does not have: {sorted(set(FOG_EXTRA) - extra_seen)}")
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
# Invisible light blocks are how builders light interiors - train cars,
# stations, offices - from ceiling fixtures. Cool white, like fluorescent
# tubes and LED panels, instead of the engine's default warm light.
LIGHT_COLORS.update({f"light_block_{level}": "#EEF4FF" for level in range(16)})
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
        # decides how add-on blocks and entities look.
        # Entities: a soft satin finish - diffuse shading with a broad, faint
        # highlight, no mirror reflections. Not smoother: Vibrant Visuals
        # does not block the sky inside an entity, so the inside of a train
        # car is lit by, and reflects, the open sky on every surface. At
        # roughness 150 that reflection washed car interiors out pale blue;
        # 190 (0.75) keeps it to a faint sheen. That is also the middle of
        # Mojang's own mob materials (Steve 154-255), so the vanilla mobs
        # without a texture set, which use this too, look natural. Not
        # metallic: painted panels, plastics and fabrics are all dielectric.
        "blocks": {"global_metalness_emissive_roughness_subsurface": [0, 0, 255, 0]},
        "actors": {"global_metalness_emissive_roughness_subsurface": [0, 0, 190, 0]},
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
#  - directional light: they turn gold and pink at sunset with the sun,
#    and - the main reason it carries most of their light - it dims in
#    rain, when the game turns the sun down and the sky grey: clouds lit
#    mostly by it grey over with the sky, which then reads as one
#    overcast deck instead of white puffs on a dark sky. The share is one
#    constant for the sun and the moon, and the game exposes nights about
#    as much brighter as the moon is weaker, so moonlit clouds look about
#    as bright against the night as sunlit ones against the day: at 0.22
#    they stood out crisp white at night, 0.12 leaves a faint silver.
#  - ambient: the only light here that follows the clock, but not the
#    weather, so it is kept small - at 8 by day it held the clouds white
#    through rain. It fills in by day, fades through sunset under the
#    sun's share, so clouds keep its gold, and is zero at night, when
#    clouds should be dim grey-blue shapes against the sky. In game this
#    scale is strong (0.7 made clouds glow white at midnight); low at
#    dawn, when clouds are dark silhouettes (早朝). Keyframes sit at real
#    sun elevations, as in the lighting tables.
#  - no atmospheric or volumetric scattering: with it on, the game haze
#    erased every cloud below about 20 degrees, so the sky looked painted
#    only overhead. Distance haze is drawn into the images instead.
CLOUD_CUBEMAP = {
    "format_version": CUBEMAP_FORMAT,
    "minecraft:cubemap_settings": {
        "description": {"identifier": "minecraft:default_cubemap"},
        "lighting": {
            "ambient_light_illuminance": keyframes({
                0.000: 2.5, 0.150: 2.4, 0.200: 2.0, 0.250: 1.5, 0.265: 1.0,
                0.283: 0.6, 0.300: 0.3, 0.330: 0.04, 0.400: 0.0, 0.600: 0.0,
                0.670: 0.04, 0.700: 0.2, 0.717: 0.4, 0.735: 1.0, 0.750: 1.5,
                0.800: 2.0, 0.850: 2.4, 1.000: 2.5,
            }),
            "sky_light_contribution": 1.0,
            "directional_light_contribution": 0.12,
            "affected_by_atmospheric_scattering": False,
            "affected_by_volumetric_scattering": False,
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
