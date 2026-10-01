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

The game places the cube with the eye below its centre, so eye level falls
70 % of the way down the side images (measured in game; see
EYE_BELOW_CENTRE). Every pixel is painted for the direction it is actually
seen in.

The clouds are feathery cirrus - "mare's tails" - on a high layer that
curves with the planet: long fibrous strands bent along the wind, bundled
into streaks of varying strength, with denser hooked heads. Seen from the
ground the parallel streaks fan out toward the horizon. There are no seams
between faces because they all sample one continuous field.
"""

from __future__ import annotations

import argparse
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
SUPERSAMPLE = 2          # 2x2 per pixel, so the fine strands near the horizon don't shimmer

_F = np.array([0.0, 0.0, 1.0])
_R = np.array([1.0, 0.0, 0.0])
_U = np.array([0.0, 1.0, 0.0])
# face -> (direction at its centre, direction of image-right, direction of image-down)
FACES = [(_F, _R, -_U), (_R, -_F, -_U), (-_F, -_R, -_U), (-_R, _F, -_U),
         (_U, _R, _F), (-_U, _R, -_F)]

# Where the game puts the six images. They form a plain cube, but the eye is
# not at its centre: it sits this many half-widths below it, so eye level
# falls 70 % of the way down the side images rather than across their
# middle, the side images' middle row shows about 22 degrees up, and the top
# image covers only the sky above 45-55 degrees. Measured in two in-game
# screenshots - the middle row of the side images shows as a straight line
# in the sky that bends at the cube's corners, and the vanishing points of
# those bends fix the camera - and matching a published skybox, which draws
# its horizon 70 % of the way down its side images. Two earlier versions of
# this pack got it wrong: painted for a centred cube, the clouds stopped in
# a square overhead; painted for a flat box, they came out stretched tall.
EYE_BELOW_CENTRE = 0.40

# Subpacks that get the painted clouds; they are the same images. The folders
# and their order live in bedrock/manifest.json.
CLOUD_SUBPACKS = ["unbound_clouds", "high_clouds"]
SEED = 7
HORIZON_HAZE = np.array([0.80, 0.87, 0.97])   # what distant clouds fade toward

# Subpacks whose painted clouds replace the game's own: they also get a fully
# transparent clouds.png, which removes the flat block clouds without the
# player having to find the video setting. The other keeps the game's 3D
# clouds (which cast shadows in Vibrant Visuals) under the cirrus.
REPLACES_VANILLA_CLOUDS = {"unbound_clouds"}


def face_dirs(face: int, n: int, rows: slice = slice(None)) -> np.ndarray:
    """View direction in game of each pixel of a face (n x n), for the rows
    given: the pixel's point on the sky cube, seen from the eye below its
    centre."""
    centre, right, down = FACES[face]
    t = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    v, u = np.meshgrid(t[rows], t, indexing="ij")
    p = centre + u[..., None] * right + v[..., None] * down
    p[..., 1] += EYE_BELOW_CENTRE
    return p / np.linalg.norm(p, axis=-1, keepdims=True)


def eye_level_row(n: int) -> int:
    """First row of a side image (of n) that lies wholly below eye level."""
    return int(np.ceil(n * (1.0 + EYE_BELOW_CENTRE) / 2.0))


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


# Clouds sit in a shell around a planet whose radius is this many units. A
# flat layer would stretch without limit toward the horizon, forcing either
# huge clouds overhead or noise at the horizon; on a curved layer the
# horizon is a finite distance away.
EARTH_RADIUS = 20.0
CIRRUS_ALTITUDE = 3.0     # the high layer; its streaks reach the horizon ~11 units away
WIND = 0.6                # direction the strands stream along (radians)


def shell_distance(up, altitude):
    """Distance along view directions with vertical component `up` to the
    shell `altitude` above the viewer."""
    b = EARTH_RADIUS * up
    return -b + np.sqrt(b * b + 2.0 * EARTH_RADIUS * altitude + altitude * altitude)


def cirrus_density(x, z, seed: int = SEED):
    """0..1 cirrus at layer position x, z."""
    u = x * np.cos(WIND) + z * np.sin(WIND)          # along the wind
    v = -x * np.sin(WIND) + z * np.cos(WIND)         # across it
    # Strands bend: their position across the wind drifts slowly along them.
    vw = v + 1.5 * fbm(u * 0.18, v * 0.18, 3, seed + 3)
    uw = u + 0.6 * fbm(u * 0.18 + 5.1, v * 0.18 + 3.3, 2, seed + 9)
    # Fibres: noise stretched far along the wind and ridged into thin lines,
    # each wrapped in a softer glow.
    f = fbm(uw * 0.35, vw * 7.0, 4, seed + 11)
    fibres = (0.65 * np.clip(1.0 - np.abs(f) * 3.0, 0.0, 1.0) ** 1.5
              + 0.35 * np.clip(1.0 - np.abs(f) * 2.2, 0.0, 1.0))
    # Bundles of strands - the visible streaks - some bright, many faint,
    # tapering at their ends; and the large patches of sky they fill.
    bundle = smoothstep(-0.08, 0.32, fbm(uw * 0.16, vw * 1.4, 3, seed + 21))
    bundle *= 0.5 + 0.5 * smoothstep(-0.3, 0.4, fbm(uw * 0.09 + 7.7, vw * 0.5 - 2.2, 2, seed + 71))
    cover = smoothstep(-0.15, 0.2, fbm(x * 0.07, z * 0.07, 3, seed + 31) + 0.15)
    # Tufts: the dense heads strands trail from, with short feathery barbs
    # set at an angle to the wind.
    tufts = smoothstep(0.62, 0.88, cellular(uw * 0.45, vw * 2.0, seed + 41, octaves=1))
    ub = uw * np.cos(1.0) + vw * np.sin(1.0)
    vb = -uw * np.sin(1.0) + vw * np.cos(1.0)
    barbs = np.clip(1.0 - np.abs(fbm(ub * 0.8, vb * 9.0, 3, seed + 61)) * 2.6, 0.0, 1.0)
    veil = 0.07 * smoothstep(-0.2, 0.4, fbm(u * 0.25, v * 1.2, 3, seed + 51))
    d = cover * (bundle * (0.9 * fibres + 0.8 * tufts * (0.5 + 0.5 * barbs)) + veil)
    return np.clip(d * 1.35, 0.0, 1.0)


def cirrus(d: np.ndarray):
    """Straight-alpha colour and opacity of the cirrus for view directions d."""
    up = np.clip(d[:, 1], 0.0, 1.0)
    t = shell_distance(up, CIRRUS_ALTITUDE)
    dens = cirrus_density(d[:, 0] * t, d[:, 2] * t)
    # Thin veils let the blue through; dense heads are white.
    thin = np.array([0.84, 0.89, 0.97])
    rgb = thin + (1.0 - thin) * np.clip(dens * 1.3, 0.0, 1.0)[:, None]
    # The game's haze is off for the sky, so distance is painted in: far
    # streaks pale toward the horizon's blue and thin out.
    haze = (1.0 - np.exp(-t / 9.0))[:, None] * 0.5
    rgb = rgb * (1.0 - haze) + HORIZON_HAZE * haze
    alpha = (np.clip(dens * 0.95, 0.0, 0.92) * smoothstep(0.0, 0.06, up)
             * (0.55 + 0.45 * np.exp(-t / 8.0)))
    return rgb, alpha * (d[:, 1] > 0.0)


def draw_cloud_face(face: int) -> Image.Image:
    if face == 5:                                   # below the horizon: nothing to draw
        return Image.new("RGBA", (FACE_SIZE, FACE_SIZE), (230, 230, 230, 0))
    n = FACE_SIZE * SUPERSAMPLE
    # A side image below eye level stays empty: the ground covers it, and
    # from a height any clouds there would hang below the horizon.
    last = n if face == 4 else -(-eye_level_row(n) // SUPERSAMPLE) * SUPERSAMPLE
    pre = np.zeros((n, n, 4))
    for r in range(0, last, 128):
        rows = slice(r, min(r + 128, last))
        dirs = face_dirs(face, n, rows)
        rgb, alpha = cirrus(dirs.reshape(-1, 3))
        pre[rows] = np.dstack([(rgb * alpha[:, None]).reshape(dirs.shape),
                               alpha.reshape(dirs.shape[:-1])])
    # Downsample in premultiplied space, then store straight alpha. The colour
    # under transparent pixels stays cloud-coloured, so texture filtering
    # never pulls a dark fringe into the cloud edges.
    pre = pre.reshape(FACE_SIZE, SUPERSAMPLE, FACE_SIZE, SUPERSAMPLE, 4).mean(axis=(1, 3))
    a = pre[..., 3]
    straight = np.where(a[..., None] > 1e-4, pre[..., :3] / np.maximum(a, 1e-6)[..., None], 0.95)
    return Image.fromarray(np.dstack([to_u8(np.clip(straight, 0, 1)), to_u8(a)]), "RGBA")


def draw_skyboxes() -> None:
    faces = [draw_cloud_face(face) for face in range(6)]
    for name in CLOUD_SUBPACKS:
        out = ROOT / "bedrock/subpacks" / name / "textures/environment/overworld_cubemap"
        out.mkdir(parents=True, exist_ok=True)
        for face, image in enumerate(faces):
            image.save(out / f"cubemap_{face}.png", optimize=True)
        clouds = out.parent / "clouds.png"
        if name in REPLACES_VANILLA_CLOUDS:
            # Same size as vanilla's cloud map (256x256), nothing in it.
            Image.new("RGBA", (256, 256), (255, 255, 255, 0)).save(clouds)
        elif clouds.exists():
            clouds.unlink()
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
