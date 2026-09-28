#!/usr/bin/env python3
"""Draw the sun, the moon and the cloud skyboxes for bedrock/.

    tools/draw_sky.py [--skip-clouds]       (needs Pillow and numpy)

Everything here is drawn procedurally; no vanilla or third-party art is used.

Sun and moon (bedrock/textures/environment/)
--------------------------------------------
Vanilla's sun and moon are 8x8 pixel squares. Complementary draws a round sun
with a soft corona and a round, cratered moon; these are drawn at 4x the
vanilla resolution, keeping vanilla's layout so the disc lands where the game
expects it:

  sun_vv.png       128x128 RGBA  the sun Vibrant Visuals draws; transparent
                                 background, disc centred, same size as
                                 vanilla's 8/32 square
  sun.png          128x128 RGBA  the sun the classic renderer draws; black
                                 background, since it is blended additively
  moon_phases.png  512x256 RGB   4x2 grid of 128px cells, black background,
                                 phase order as vanilla: 0 full, 1-3 waning
                                 (lit from the left), 4 new, 5-7 waxing

Cloud skyboxes (bedrock/subpacks/<variant>/textures/environment/overworld_cubemap/)
----------------------------------------------------------------------------------
Bedrock draws a custom Overworld sky from six images, cubemap_0..5.png, and
since 1.21.130 Vibrant Visuals lights them through cubemaps/*.json (sun and
sky light, atmospheric haze). Clouds are painted with a transparent
background, so the game's own sky - its colours, sunsets and night - shows
through everywhere else; the clouds themselves pick up the sun's colour.

Face layout, confirmed by matching the edges of several working skyboxes:
0-3 are the four sides in order left to right (each face's right edge meets
the next face's left edge), 4 is the top and 5 the bottom. The top's lower
edge meets face 0's top; the bottom's upper edge meets face 0's bottom.

The clouds are a layer in perspective: every pixel's view direction is
projected onto a curved layer above the viewer and the cloud density is
looked up there, so clouds are larger overhead and crowd together toward the
horizon, and the six faces join without seams because they sample one
continuous field.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bedrock/textures/environment"

CELL = 128                 # 4x vanilla's 32px cell
RADIUS = 18.0              # the moon: a circle with the area of vanilla's 8/32 square, at 4x
SUN_RADIUS = 10.0          # the sun: about 60 % of vanilla's width. Bloom and the
                           # atmosphere's own halo already make it read larger in game


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
    disc = 1.0 - smoothstep(SUN_RADIUS - 0.8, SUN_RADIUS + 0.8, d)

    # Limb darkening: the edge of a real sun is dimmer and warmer than its
    # centre, which is what makes it read as a ball rather than a sticker.
    mu = np.sqrt(np.clip(1.0 - (d / SUN_RADIUS) ** 2, 0.0, 1.0))
    centre = np.array([1.0, 0.99, 0.95])
    limb = np.array([1.0, 0.93, 0.76])
    rgb = limb + (centre - limb) * mu[..., None] ** 0.6
    rgb *= (0.88 + 0.12 * mu)[..., None]

    # Only a thin rim of glow. Vibrant Visuals draws the sun in HDR, so any
    # semi-transparent corona is multiplied up to full white and bloomed: an
    # earlier wide corona made the sun look several times its size in game.
    r = np.clip(d - SUN_RADIUS, 0.0, None)
    corona = 0.25 * np.exp(-r / 1.5)
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


# --------------------------------------------------------------------------
# Cloud skyboxes
# --------------------------------------------------------------------------

FACE_SIZE = 1024
SUPERSAMPLE = 2          # 2x2 per pixel, so the crowded clouds at the horizon don't shimmer

_F = np.array([0.0, 0.0, 1.0])
_R = np.array([1.0, 0.0, 0.0])
_U = np.array([0.0, 1.0, 0.0])
# face -> (direction at its centre, direction of image-right, direction of image-down)
FACES = [(_F, _R, -_U), (_R, -_F, -_U), (-_F, -_R, -_U), (-_R, _F, -_U),
         (_U, _R, _F), (-_U, _R, -_F)]

# Each variant becomes a subpack the player picks in the pack's settings.
# coverage: share of the sky above ~10 degrees covered by cumulus.
# cirrus:   peak opacity of the high, streaky cloud layer.
CLOUD_VARIANTS = {
    # Complementary Unbound's fair-weather sky: puffy cumulus with a few
    # high streaks above them. Meant to replace the game's own clouds.
    "unbound_clouds": {"coverage": 0.40, "cirrus": 0.5},
    # Only the high streaks, for keeping the game's 3D clouds (which cast
    # shadows in Vibrant Visuals) and still getting a fuller sky above them.
    "high_clouds": {"coverage": 0.0, "cirrus": 0.85},
}
SEED = 7
HORIZON_HAZE = np.array([0.80, 0.87, 0.97])   # what distant clouds fade toward

# Subpacks whose painted clouds replace the game's own: they also get a fully
# transparent clouds.png, which removes the flat block clouds without the
# player having to find the video setting.
REPLACES_VANILLA_CLOUDS = {"unbound_clouds"}


def face_dirs(face: int, n: int) -> np.ndarray:
    centre, right, down = FACES[face]
    t = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    v, u = np.meshgrid(t, t, indexing="ij")
    d = centre + u[..., None] * right + v[..., None] * down
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return h ^ (h >> 16)


def gradient_noise(x, y, seed):
    """2D Perlin-style gradient noise, roughly -0.7..0.7."""
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf = x - xi
    yf = y - yi

    def corner(ox, oy):
        angle = _hash(xi + ox, yi + oy, seed).astype(np.float64) * (2 * np.pi / 4294967296.0)
        return np.cos(angle) * (xf - ox) + np.sin(angle) * (yf - oy)

    fx = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
    fy = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    bottom = corner(0, 0) + (corner(1, 0) - corner(0, 0)) * fx
    top = corner(0, 1) + (corner(1, 1) - corner(0, 1)) * fx
    return bottom + (top - bottom) * fy


def fbm(x, y, octaves, seed):
    total = np.zeros_like(x)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * gradient_noise(x, y, seed + o * 101)
        norm += amp
        amp *= 0.5
        x, y = x * 2.0 + 17.3, y * 2.0 - 9.1
    return total / norm


def cellular(x, y, seed, octaves=3):
    """Inverted Worley noise: round, cauliflower-like puffs, 0..1."""
    total = np.zeros_like(x)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        xi = np.floor(x).astype(np.int64)
        yi = np.floor(y).astype(np.int64)
        xf, yf = x - xi, y - yi
        nearest = np.full(x.shape, 9.0)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                h = _hash(xi + ox, yi + oy, seed + o * 31)
                px = ox + (h & 0xFFFF) / 65535.0
                py = oy + ((h >> 16) & 0xFFFF) / 65535.0
                nearest = np.minimum(nearest, (px - xf) ** 2 + (py - yf) ** 2)
        total += amp * (1.0 - np.clip(np.sqrt(nearest), 0.0, 1.0))
        norm += amp
        amp *= 0.5
        x, y = x * 2.0 + 3.1, y * 2.0 - 7.7
    return total / norm


# Cloud layers are curved like the real sky: a shell around a planet whose
# radius is this many cumulus altitudes. A flat layer would stretch without
# limit toward the horizon, forcing either huge clouds overhead or noise at
# the horizon; on a curved layer the horizon is a finite distance away.
EARTH_RADIUS = 20.0


def layer_hit(d: np.ndarray, altitude: float):
    """Horizontal offset at which view directions d meet a cloud layer
    `altitude` above the viewer (in cumulus altitudes)."""
    up = np.clip(d[..., 1], 0.0, 1.0)
    r = EARTH_RADIUS
    dist = np.sqrt((r + altitude) ** 2 - r * r * (1.0 - up * up)) - r * up
    return d[..., 0] * dist, d[..., 2] * dist


def cumulus_density(d: np.ndarray, seed: int):
    """Raw density of the cumulus layer, and how far away the point is."""
    px, pz = layer_hit(d, 1.0)
    # Domain warp breaks up the grid-aligned look of plain noise.
    qx = px + 0.22 * fbm(px * 1.6 + 5.2, pz * 1.6 + 1.3, 3, seed + 11)
    qz = pz + 0.22 * fbm(px * 1.6 + 1.7, pz * 1.6 + 9.2, 3, seed + 23)
    # Fair-weather cumulus come as separate heaps, so the base shape is
    # cellular: one round cell per cloud, roughened by fbm so no two match,
    # and a finer cellular layer carving the outline into billows.
    heaps = cellular(qx * 1.7, qz * 1.7, seed + 51, octaves=1)
    density = (0.62 * heaps + 0.38 * (0.5 + fbm(qx * 2.2, qz * 2.2, 5, seed))
               + 0.30 * (cellular(qx * 5.0, qz * 5.0, seed + 77) - 0.57))
    return density, np.hypot(px, pz)


@lru_cache(maxsize=None)
def coverage_thresholds(coverage: float, seed: int) -> tuple[float, float]:
    """Density at which clouds start, so that `coverage` of the sky above
    about 10 degrees is cloud, and the density of the thickest cores."""
    rng = np.random.default_rng(seed + 999)
    v = rng.normal(size=(160000, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    density, _ = cumulus_density(v[v[:, 1] > 0.17], seed)
    return float(np.quantile(density, 1.0 - coverage)), float(np.quantile(density, 0.995))


def cloud_layer(d: np.ndarray, coverage: float, cirrus: float, seed: int = SEED):
    """Straight-alpha colour and opacity of the clouds for view directions d."""
    above = d[..., 1] > 0
    white = np.array([1.0, 1.0, 1.0])
    base_grey = np.array([0.64, 0.69, 0.80])

    if coverage > 0:
        lo, hi = coverage_thresholds(coverage, seed)
        density, dist = cumulus_density(d, seed)
        depth = np.clip((density - lo) / (hi - lo), 0.0, 1.0)
        a_cu = smoothstep(0.0, 0.08, depth)
        # Clouds run all the way down to the horizon. The game's own haze is
        # switched off for the skybox (it erased everything below ~20
        # degrees), so distance is drawn in here: far clouds thin out a
        # little and fade toward the pale blue of the horizon.
        a_cu *= smoothstep(0.0, 0.035, d[..., 1]) * (0.55 + 0.45 * np.exp(-dist / 5.0)) * above

        # Seen from below, a cumulus shows its flat grey base on the side
        # toward the viewer and its sunlit top on the far side. Look a little
        # further out along the line of sight: if the cloud ends soon beyond
        # this point, the top is in view and the pixel is bright.
        far = d.copy()
        far[..., 1] /= 1.14
        density_far, _ = cumulus_density(far, seed)
        top = 1.0 - smoothstep(0.05, 0.55, np.clip((density_far - lo) / (hi - lo), 0.0, 1.0))
        core = smoothstep(0.10, 0.85, depth)
        light = 1.0 - 0.34 * core * (1.0 - 0.75 * top) + 0.05 * (1.0 - smoothstep(0.0, 0.15, depth))
        k = np.clip((light - 0.62) / 0.43, 0.0, 1.0)[..., None]
        rgb_cu = base_grey + (white - base_grey) * k
        haze = (1.0 - np.exp(-dist / 4.0))[..., None] * 0.45
        rgb_cu = rgb_cu * (1.0 - haze) + HORIZON_HAZE * haze
    else:
        a_cu = np.zeros(d.shape[:-1])
        rgb_cu = np.broadcast_to(white, d.shape).copy()

    # Cirrus: a higher layer, stretched along one wind direction into streaks.
    cx, cz = layer_hit(d, 3.0)
    sx = cx * np.cos(0.6) - cz * np.sin(0.6)
    sz = cx * np.sin(0.6) + cz * np.cos(0.6)
    streaks = fbm(sx * 0.12, sz * 0.9, 5, seed + 301) + 0.35 * fbm(sx * 0.05 + 3.3, sz * 0.05 - 1.1, 2, seed + 401)
    a_ci = smoothstep(0.08, 0.45, streaks) * cirrus
    a_ci *= smoothstep(0.03, 0.25, d[..., 1]) * above
    rgb_ci = np.array([0.97, 0.98, 1.0])

    # Cumulus in front of cirrus.
    alpha = a_cu + a_ci * (1.0 - a_cu)
    rgb = (rgb_cu * a_cu[..., None] + rgb_ci * (a_ci * (1.0 - a_cu))[..., None]) \
        / np.maximum(alpha, 1e-6)[..., None]
    return np.where(alpha[..., None] > 1e-4, rgb, rgb_cu), alpha


def draw_cloud_face(face: int, coverage: float, cirrus: float) -> Image.Image:
    n = FACE_SIZE * SUPERSAMPLE
    if face == 5:                                   # below the horizon: nothing to draw
        return Image.new("RGBA", (FACE_SIZE, FACE_SIZE), (230, 230, 230, 0))
    dirs = face_dirs(face, n)
    rgb = np.empty(dirs.shape)
    alpha = np.empty(dirs.shape[:-1])
    for row in range(0, n, 256):                    # in bands, to keep memory modest
        rgb[row:row + 256], alpha[row:row + 256] = cloud_layer(dirs[row:row + 256], coverage, cirrus)
    # Downsample in premultiplied space, then store straight alpha. The colour
    # under transparent pixels stays cloud-coloured, so texture filtering
    # never pulls a dark fringe into the cloud edges.
    pre = np.dstack([rgb * alpha[..., None], alpha])
    pre = pre.reshape(FACE_SIZE, SUPERSAMPLE, FACE_SIZE, SUPERSAMPLE, 4).mean(axis=(1, 3))
    a = pre[..., 3]
    straight = np.where(a[..., None] > 1e-4, pre[..., :3] / np.maximum(a, 1e-6)[..., None], 0.9)
    return Image.fromarray(np.dstack([to_u8(np.clip(straight, 0, 1)), to_u8(a)]), "RGBA")


def draw_skyboxes() -> None:
    for name, params in CLOUD_VARIANTS.items():
        out = ROOT / "bedrock/subpacks" / name / "textures/environment/overworld_cubemap"
        out.mkdir(parents=True, exist_ok=True)
        for face in range(6):
            draw_cloud_face(face, **params).save(out / f"cubemap_{face}.png", optimize=True)
        if name in REPLACES_VANILLA_CLOUDS:
            # Same size as vanilla's cloud map (256x256), nothing in it.
            Image.new("RGBA", (256, 256), (255, 255, 255, 0)).save(out.parent / "clouds.png")
        size = sum((out / f"cubemap_{f}.png").stat().st_size for f in range(6))
        print(f"{out}: 6 faces {FACE_SIZE}x{FACE_SIZE} RGBA, {size / 1e6:.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--skip-clouds", action="store_true",
                        help="only redraw the sun and moon (the skyboxes take a few minutes)")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    draw_sun_vv().save(OUT / "sun_vv.png", optimize=True)
    draw_sun_classic().save(OUT / "sun.png", optimize=True)
    draw_moon_phases().save(OUT / "moon_phases.png", optimize=True)
    for name in ("sun_vv.png", "sun.png", "moon_phases.png"):
        img = Image.open(OUT / name)
        print(f"{OUT / name}: {img.size[0]}x{img.size[1]} {img.mode}")
    if not args.skip_clouds:
        draw_skyboxes()


if __name__ == "__main__":
    main()
