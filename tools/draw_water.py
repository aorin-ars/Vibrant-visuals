#!/usr/bin/env python3
"""Draw the water surface and rain ripple textures, and the ripple particle.

    tools/draw_water.py            (needs Pillow and numpy)

Vanilla's water texture set pairs the old animated water texture with a
normal map made from it. Under Vibrant Visuals that normal map stamps the
classic white wave streaks into the surface and breaks reflections into
noise - the "vanilla" look, and the reason reflections of the sky and
shore do not read.

These replace it with:
  - a flat grey colour (the biome's water colour tints it, as vanilla's does),
    more transparent than vanilla's
  - smooth metalness/emissive/roughness/subsurface, slightly glossier than
    vanilla so reflections stay clean
  - no normal map, so the surface shape comes only from the wave simulation
    in water/water.json: soft ripples that bend reflections without
    shredding them

Sizes match vanilla (the animation frames are counted from the image
height), and a texture set may only use images from its own pack, so all
three layers are drawn here. Nothing is copied from the vanilla pack.

Rain ripples (bedrock/particles/rain_splash.json, textures/particle/)
--------------------------------------------------------------------
A resource pack cannot make the ground wet: a block's glossiness comes from
its texture set and does not change with the weather. What it can change is
the splash every raindrop makes, which the game spawns where rain lands. It
is redefined here as a ring lying flat on the ground (and on water), growing
and breaking up over half a second - the rain ripples of Complementary's
puddles - with a very smooth texture set, so each ring catches the sky and
light like a film of water. Dripstone and leaf drips use the same splash.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

PACK = Path(__file__).resolve().parent.parent / "bedrock"
OUT = PACK / "textures/blocks"

# name -> (width, height, alpha). Vanilla: still water 16x512 (32 frames) at
# alpha 240, flowing water 32x1024 at alpha 255. Lower here, so the surface
# layer lets more of the water below show through: clear water where the
# bottom and plants stay visible, as in Complementary.
WATER = {
    "water_still_grey": (16, 512, 170),
    "water_flow_grey": (32, 1024, 190),
}
GREY = 176                  # vanilla's pattern averages ~165; flat and a touch lighter
MERS = (18, 0, 12, 0)       # vanilla: metalness 18, roughness ~15-22; a little smoother


# Rain ripple flipbook: FRAMES square cells side by side, CELL px each.
RIPPLE_FRAMES = 8
RIPPLE_CELL = 32
RIPPLE_COLOUR = (206, 216, 230)   # a pale, cool sheen; the game lights it
RIPPLE_MERS = (0, 0, 16, 0)       # not metal, very smooth: reflects like water
RIPPLE_SIZE = (0.05, 0.28)        # billboard size at the start and end of its life
RIPPLE_LIFETIME = (0.45, 0.6)     # seconds


def texture_set(folder: Path, name: str) -> None:
    (folder / f"{name}.texture_set.json").write_text(json.dumps({
        "format_version": "1.21.30",
        "minecraft:texture_set": {
            "color": name,
            "metalness_emissive_roughness_subsurface": f"{name}_mers",
        },
    }, indent=2) + "\n")


def draw_ripples() -> None:
    """A ring that thins and breaks into arcs as it spreads; an inner ring
    follows it for the first frames, as behind a real raindrop. Cut-out
    alpha, since the particle material is alpha-tested."""
    n, frames = RIPPLE_CELL, RIPPLE_FRAMES
    y, x = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    r = np.hypot(x, y) / (n / 2)                 # 0 at the centre, 1 at the cell edge
    angle = np.arctan2(y, x)
    rng = np.random.default_rng(11)
    phases = rng.uniform(0, 2 * np.pi, 4)
    breakup = sum(np.sin(k * angle + ph) / k for k, ph in zip((2, 3, 5, 7), phases))
    sheet = np.zeros((n, n * frames, 4), np.uint8)
    for f in range(frames):
        t = f / (frames - 1)
        width = 0.20 - 0.14 * t                   # ring thickness, fraction of the radius
        ring = np.abs(r - 0.82) < width / 2
        ring &= breakup > -2.0 + 2.6 * t ** 1.5   # whole at first, then only arcs
        if 0 < f < 5:
            ring |= np.abs(r - 0.45) < 0.05 * (1 - t)
        cell = sheet[:, f * n:(f + 1) * n]
        cell[ring] = (*RIPPLE_COLOUR, 255)
        cell[~ring] = (*RIPPLE_COLOUR, 0)        # keep colour under the cut-out
    folder = PACK / "textures/particle"
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(sheet, "RGBA").save(folder / "rain_ripple.png")
    mers = np.zeros_like(sheet)
    mers[...] = RIPPLE_MERS
    Image.fromarray(mers, "RGBA").save(folder / "rain_ripple_mers.png")
    texture_set(folder, "rain_ripple")

    grow = f"({RIPPLE_SIZE[1] - RIPPLE_SIZE[0]} * variable.particle_age / variable.particle_lifetime)"
    size = f"{RIPPLE_SIZE[0]} + {grow}"
    particle = {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {
                "identifier": "minecraft:rain_splash_particle",
                "basic_render_parameters": {
                    "material": "particles_alpha",
                    "texture": "textures/particle/rain_ripple",
                },
            },
            "components": {
                # The game emits these itself, one per raindrop that lands.
                "minecraft:emitter_rate_manual": {"max_particles": 300},
                "minecraft:emitter_lifetime_expression": {},
                # A hair above the surface, so the ring does not flicker into it.
                "minecraft:emitter_shape_point": {"offset": [0, 0.02, 0]},
                "minecraft:particle_lifetime_expression": {
                    "max_lifetime": f"Math.random({RIPPLE_LIFETIME[0]}, {RIPPLE_LIFETIME[1]})",
                },
                "minecraft:particle_initial_spin": {"rotation": "Math.random(0, 360)"},
                # Flat on the ground: the face points straight up.
                "minecraft:particle_appearance_billboard": {
                    "size": [size, size],
                    "facing_camera_mode": "direction_z",
                    "direction": {"mode": "custom_direction", "custom_direction": [0, 1, 0]},
                    "uv": {
                        "texture_width": RIPPLE_CELL * RIPPLE_FRAMES,
                        "texture_height": RIPPLE_CELL,
                        "flipbook": {
                            "base_UV": [0, 0],
                            "size_UV": [RIPPLE_CELL, RIPPLE_CELL],
                            "step_UV": [RIPPLE_CELL, 0],
                            "frames_per_second": 16,
                            "max_frame": RIPPLE_FRAMES,
                            "stretch_to_lifetime": True,
                        },
                    },
                },
                "minecraft:particle_appearance_lighting": {},
            },
        },
    }
    (PACK / "particles").mkdir(exist_ok=True)
    (PACK / "particles/rain_splash.json").write_text(json.dumps(particle, indent=2) + "\n")
    print(f"{folder / 'rain_ripple.png'}: {frames} frames, glossy texture set; "
          f"{PACK / 'particles/rain_splash.json'}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (w, h, alpha) in WATER.items():
        Image.new("RGBA", (w, h), (GREY, GREY, GREY, alpha)).save(OUT / f"{name}.png")
        mers = np.zeros((h, w, 4), np.uint8)
        mers[...] = MERS
        Image.fromarray(mers, "RGBA").save(OUT / f"{name}_mers.png")
        texture_set(OUT, name)
        print(f"{OUT / name}: {w}x{h}, texture set without a normal map")
    draw_ripples()


if __name__ == "__main__":
    main()
