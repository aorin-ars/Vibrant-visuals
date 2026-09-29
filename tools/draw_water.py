#!/usr/bin/env python3
"""Draw the water surface textures and texture sets into bedrock/textures/blocks/.

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
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "bedrock/textures/blocks"

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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (w, h, alpha) in WATER.items():
        Image.new("RGBA", (w, h), (GREY, GREY, GREY, alpha)).save(OUT / f"{name}.png")
        mers = np.zeros((h, w, 4), np.uint8)
        mers[...] = MERS
        Image.fromarray(mers, "RGBA").save(OUT / f"{name}_mers.png")
        (OUT / f"{name}.texture_set.json").write_text(json.dumps({
            "format_version": "1.21.30",
            "minecraft:texture_set": {
                "color": name,
                "metalness_emissive_roughness_subsurface": f"{name}_mers",
            },
        }, indent=2) + "\n")
        print(f"{OUT / name}: {w}x{h}, texture set without a normal map")


if __name__ == "__main__":
    main()
