#!/usr/bin/env python3
"""Draw the round sun and moon into bedrock/textures/environment/.

    tools/draw_sky.py            (needs Pillow and numpy)

Vanilla's sun and moon are 8x8 pixel squares. Complementary draws a round sun
with a soft corona and a round, cratered moon; these are drawn procedurally
here (no vanilla art is used) at 4x the vanilla resolution, keeping vanilla's
layout so the disc lands where the game expects it:

  sun_vv.png       128x128 RGBA  the sun Vibrant Visuals draws; transparent
                                 background, disc centred, same size as
                                 vanilla's 8/32 square
  sun.png          128x128 RGBA  the sun the classic renderer draws; black
                                 background, since it is blended additively
  moon_phases.png  512x256 RGB   4x2 grid of 128px cells, black background,
                                 phase order as vanilla: 0 full, 1-3 waning
                                 (lit from the left), 4 new, 5-7 waxing
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "bedrock/textures/environment"

CELL = 128                 # 4x vanilla's 32px cell
RADIUS = 18.0              # a circle with the area of vanilla's 8/32 square, at 4x


def grid(size: int):
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    c = (size - 1) / 2.0
    return x - c, y - c


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def to_u8(a):
    return np.clip(np.round(a * 255.0), 0, 255).astype(np.uint8)


def sun_layers():
    """Returns (rgb in 0..1, coverage of the disc, corona strength)."""
    x, y = grid(CELL)
    d = np.hypot(x, y)
    disc = 1.0 - smoothstep(RADIUS - 0.8, RADIUS + 0.8, d)

    # Limb darkening: the edge of a real sun is dimmer and warmer than its
    # centre, which is what makes it read as a ball rather than a sticker.
    mu = np.sqrt(np.clip(1.0 - (d / RADIUS) ** 2, 0.0, 1.0))
    centre = np.array([1.0, 0.99, 0.95])
    limb = np.array([1.0, 0.93, 0.76])
    rgb = limb + (centre - limb) * mu[..., None] ** 0.6
    rgb *= (0.88 + 0.12 * mu)[..., None]

    # Corona: a tight bright ring and a wide faint bloom, faded to nothing
    # before the edge of the quad so the square never shows.
    r = np.clip(d - RADIUS, 0.0, None)
    corona = 0.55 * np.exp(-r / 4.0) + 0.18 * np.exp(-r / 16.0)
    corona *= 1.0 - smoothstep(CELL * 0.36, CELL * 0.49, d)
    corona *= 1.0 - disc
    return rgb, disc, corona


def draw_sun_vv() -> Image.Image:
    rgb, disc, corona = sun_layers()
    glow = np.array([1.0, 0.93, 0.78])
    alpha = np.clip(disc + corona, 0.0, 1.0)
    colour = rgb * disc[..., None] + glow * corona[..., None]
    colour = np.where(alpha[..., None] > 0, colour / np.maximum(alpha, 1e-6)[..., None], 0.0)
    return Image.fromarray(np.dstack([to_u8(colour), to_u8(alpha)]), "RGBA")


def draw_sun_classic() -> Image.Image:
    rgb, disc, corona = sun_layers()
    glow = np.array([1.0, 0.9, 0.7])
    colour = rgb * disc[..., None] + glow * (corona * 0.8)[..., None]
    opaque = np.ones(disc.shape)
    return Image.fromarray(np.dstack([to_u8(colour), to_u8(opaque)]), "RGBA")


def moon_surface(rng: np.random.Generator):
    """Albedo over the disc: bright highlands, a few dark maria, craters."""
    x, y = grid(CELL)
    u, v = x / RADIUS, y / RADIUS
    albedo = np.full(x.shape, 0.86)

    for cx, cy, rad, depth in [(-0.35, -0.25, 0.42, 0.20), (0.25, -0.35, 0.30, 0.16),
                               (0.10, 0.20, 0.36, 0.18), (-0.20, 0.45, 0.22, 0.12),
                               (0.45, 0.25, 0.18, 0.10)]:
        dm = np.hypot(u - cx, v - cy) / rad
        albedo -= depth * (1.0 - smoothstep(0.55, 1.0, dm))

    for _ in range(26):
        cx, cy = rng.uniform(-0.9, 0.9, 2)
        if cx * cx + cy * cy > 0.85:
            continue
        rad = rng.uniform(0.05, 0.16)
        dc = np.hypot(u - cx, v - cy) / rad
        albedo -= 0.10 * (1.0 - smoothstep(0.6, 1.0, dc))       # floor
        albedo += 0.07 * np.exp(-((dc - 1.0) / 0.18) ** 2)       # bright rim

    grain = rng.normal(0.0, 0.025, x.shape)
    return np.clip(albedo + grain, 0.35, 1.0)


def draw_moon_phases() -> Image.Image:
    rng = np.random.default_rng(20250617)
    albedo = moon_surface(rng)
    x, y = grid(CELL)
    d = np.hypot(x, y)
    disc = 1.0 - smoothstep(RADIUS - 0.8, RADIUS + 0.8, d)
    u = np.clip(x / RADIUS, -1.0, 1.0)
    v = np.clip(y / RADIUS, -1.0, 1.0)
    z = np.sqrt(np.clip(1.0 - u * u - v * v, 0.0, 1.0))

    tint = np.array([0.86, 0.91, 1.0])          # cold, slightly blue moonlight
    sheet = np.zeros((CELL * 2, CELL * 4, 3))
    for phase in range(8):
        # Angle of the light around the moon: 0 = full (from behind the
        # viewer), negative = from the left (waning), positive = right.
        angle = np.radians([0, -45, -90, -135, 180, 135, 90, 45][phase])
        lambert = u * np.sin(angle) + z * np.cos(angle)
        lit = smoothstep(-0.06, 0.10, lambert)
        shade = 0.25 + 0.75 * np.clip(lambert, 0.0, 1.0) ** 0.35
        earthshine = 0.05
        light = lit * shade + (1.0 - lit) * earthshine
        cell = albedo[..., None] * light[..., None] * tint * disc[..., None]
        row, col = divmod(phase, 4)
        sheet[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL] = cell
    return Image.fromarray(to_u8(sheet), "RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_sun_vv().save(OUT / "sun_vv.png", optimize=True)
    draw_sun_classic().save(OUT / "sun.png", optimize=True)
    draw_moon_phases().save(OUT / "moon_phases.png", optimize=True)
    for name in ("sun_vv.png", "sun.png", "moon_phases.png"):
        img = Image.open(OUT / name)
        print(f"{OUT / name}: {img.size[0]}x{img.size[1]} {img.mode}")


if __name__ == "__main__":
    main()
