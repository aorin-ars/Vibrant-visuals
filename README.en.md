# Vibrant Visuals

[日本語](README.md) | **English**

Shader-mod looks for Minecraft, for **both editions**.

| | Contents | Goes to |
|---|---|---|
| [`bedrock/`](bedrock/) | **Vibrant Unbound** — a Complementary Unbound style resource pack for Vibrant Visuals | open the `.mcpack` |
| [`java/`](java/) | Shader pack for Iris / OptiFine | `.minecraft/shaderpacks/` |

> **The two editions use completely different formats.** A Java shader pack
> dropped into Bedrock does not even appear in the list, and vice versa.

---

# Bedrock Edition: Vibrant Unbound

Recreates the look of the Java shader **Complementary Shaders (Unbound style)**
with Bedrock's Vibrant Visuals renderer.

## Requirements

- Minecraft Bedrock **1.26.0 or newer**
- **Vibrant Visuals switched on** in Video Settings

## Installing

1. Open `VibrantUnbound-*.mcpack` — it imports itself
2. **Settings → Video → Vibrant Visuals**: on
3. In the world's **Settings → Resource Packs**, activate the pack

**Optional add-on**: activate `VibrantUnbound-Relief-*.mcpack` alongside it to
give stone, wood, ores and other opaque blocks surface relief (the equivalent of
Complementary's generated normals). It is built from the vanilla textures, so
it is not in the repository ([how to build it](#development)). **Personal use
only** — do not redistribute it.

To install by hand, unzip into `com.mojang/resource_packs/`.

## What changes

| | Vanilla Vibrant Visuals | Vibrant Unbound |
|---|---|---|
| Picture | "generic" tone mapping | **ACES (filmic) tone mapping**: firm shade, rich midtones, bright skies and sunsets rolling smoothly into white. A different look from stock Vibrant Visuals at the root |
| Sunlight | Whitish, fades early in the afternoon | **Strong, clear white** at noon, 125 (vanilla 100); gold as the sun gets low, orange to red on the horizon |
| Sky through the day | Muted | A low sun lights the land gold to orange instead of turning red and dim. Early morning (magenta turning orange-gold) → morning (warm cream horizon in a blue sky) → noon (blue sky paling to an almost white horizon) → late afternoon (gold to peach horizon) → sunset (lavender above a coral-pink horizon — the whole sky goes pastel, like Complementary's sunsets) → night (navy) → late night (deep navy). Never black |
| Sky | Nearly one even blue (Rayleigh 10) | Rayleigh down to 1.3, so the sky is a real gradient from the blue zenith to a pale horizon; a **small halo gathered around the sun** instead of vanilla's milky haze over half the sky; a faint halo around the moon at night |
| Shadows | Grey (full sky light) | Sky light cut to 60 %, for a clear step between sun and shade; shade stays blue-grey, never black. Short shadows (noon sun 78° up). More sky light at sunset, so the coloured sky fills the shade |
| Night | Moonlight 0.4 | **Moonlight 1.0**, blue: moonlit faces stand out and the valley haze glows blue |
| Air | Uniform fog in some biomes | **Clear air with depth**: distant terrain fades to blue rather than milky white, haze gathers in valleys and caves (densest low, gone around y=170), glows gold toward a low sun and blue under the moon, and falls in light shafts through leaves and cave openings. Mistier in humid forests, swamps and savannas, clearer in deserts; none in the Nether |
| Rain | — | Haze thickens |
| Water | No waves, the old water pattern | **Clear water**: nothing in it but water (no plankton, no silt) and a more transparent surface than vanilla's, so the bottom and water plants show through; vanilla's water pattern (white streaks) and its normal map are replaced, leaving only gentle ripples, so the sky and shore reflect cleanly; a hint of the biome's water colour |
| Underwater | — | The game's own (an earlier underwater fog made the player's shadow show up as a dark shape, so it was removed) |
| Block light | One colour | **Coloured**: torches and fire orange, soul fire cyan, redstone red, amethyst and ender blocks violet, sea lanterns cyan-white — 106 blocks |
| Sun and moon | Squares | **Small round sun** (its halo comes from the sky's scattering), **round moon** with craters and all 8 phases |
| Clouds | Flat blocky slabs | **Cotton-wool cumulus painted into the sky** (a skybox): bright white tops, blue-grey shaded undersides, with thin cirrus above; tinted by the sun at sunset. [See below](#sky-clouds-skybox) |
| Grading | Contrast 1.15 / saturation 1.05 | On top of ACES: contrast 1.12 / saturation 1.20 / gain 1.02, for Complementary's deep greens and blues; shadows lean slightly cool, highlights slightly warm |

### Why every biome is covered

Since 1.21.90 most vanilla biomes — jungle, desert, taiga, mesa, the Nether,
the End and more — carry **their own lighting, atmosphere and colour grading**,
and those take precedence over `lighting/global.json` and the other global
files. A pack that only overrides the globals changes plains and forest and
nothing else.

This pack overrides **every identifier the vanilla biomes use** (15 lighting,
17 atmosphere, 14 colour grading, 1 water) under the same name, so the look is
the same wherever you are, with small deliberate differences on top — a warmer
desert, a whiter snowfield.

## Sky clouds (skybox)

Bedrock can redraw the Overworld sky from six images
(`textures/environment/overworld_cubemap/cubemap_0..5.png`), and since 1.21.130
Vibrant Visuals lights those images with the sun and sky
(`cubemaps/default_cubemap.json`).

This pack uses that to paint **clouds on a transparent background** into the
sky. Everywhere else the normal Vibrant Visuals sky shows through, so its
colours, sunsets and nights still follow the time of day, and only the clouds
take on the light — white at noon, gold to pink at sunset.

**Choose the clouds in the pack's settings**: world Settings → Resource Packs →
tap the active Vibrant Unbound → the gear (⚙).

| Option | What it is | The game's own clouds |
|---|---|---|
| **Sky: Unbound clouds** (default) | Cotton-wool cumulus with thin high cirrus above | **Hidden automatically** (no flat blocky clouds) |
| Sky: high clouds only | Just the thin cirrus | Keep them on — for pairing with the shadow-casting vanilla clouds |
| Sky: no clouds | Nothing painted | Up to you |

Worth knowing:

- Painted clouds **do not move**; they are fixed to the sky
- Distant clouds fade to pale blue inside the images (the game's haze erased the low clouds entirely)
- Only the Overworld has them; the Nether and the End are unchanged

The face order (0–3 the sides from left to right, 4 the top, 5 the bottom) was
confirmed by matching the edges between faces of several working skyboxes.

**The game does not wrap the six images round the player as a cube.** In an
in-game screenshot the edges of the top image show as straight lines meeting
at a right angle; working the field of view out from their vanishing points,
the top image covered everything above about 21° (15° at its corners), where
a cube's top would stop at 45° (35°). That is a flat box, 0.38 times as tall
as it is wide, and the clouds are painted for that box so they keep their
proper size and spacing in game (`BOX_HEIGHT` in `tools/draw_sky.py`).

In the same screenshot none of the clouds in the upper halves of the side
images appeared above the horizon, which fits the game showing the sides
upside down. The side images are therefore painted **mirror symmetric** about
the horizon: upright or flipped, the same clouds show above it.

The clouds themselves are fair-weather cumulus heaps — flat bases, rounded,
billowing tops — ray-marched pixel by pixel: the lower a point sits in its
heap, the more cloud above shades it, so tops are bright white and undersides
blue-grey, like cotton wool. No sun direction is baked in (the real one
moves); the game adds the sun's colour.

## What a resource pack cannot do

Vibrant Visuals' shaders belong to the engine; a resource pack only supplies
numbers and textures. These Complementary features cannot be reproduced:

- Grass and leaves waving in the wind
- **Moving** volumetric clouds, auroras, nebulae (static clouds painted into the sky are possible — see above)
- Rain puddles and wet-surface reflections
- Depth of field, motion blur, lens flare

Fog density cannot follow the time of day either (fog settings do not support
keyframes).

## Entity shadows

**Entities casting shadows shaped like their models is a feature of Vibrant
Visuals itself** — switching it on in Video Settings is what produces them.
Their resolution comes from the shadow quality video setting; a resource pack
cannot change it.

A pack only chooses the shadow **style** (`shadows/global.json`):

| Key | This pack | Meaning |
|---|---|---|
| `shadow_style` | `soft_shadows` | Soft-edged shadows. `blocky_shadows` gives pixel-art stepped shadows |
| `texel_size` | 16 | With `blocky_shadows`, the grid shadows snap to. Unused by `soft_shadows` |

> Earlier versions of this README called `texel_size` the shadow map
> resolution. That was wrong: it does not make shadows any finer.

## The manifest's `capabilities`

```json
"capabilities": ["pbr"]
```

**Without this line every Vibrant Visuals file — `lighting`, `atmospherics`
and the rest — is silently ignored.** Texture replacement still works, so the
pack looks installed and does nothing, which is the most confusing way for it to
break. `tools/check_bedrock.py` catches it.

## Making an add-on's vehicles look metallic

Vibrant Visuals supports PBR. The quickest lever is the pack-wide default for
entities (`actors` in `pbr/global.json`, `[metalness, emission, roughness,
subsurface]`; lower roughness is glossier — this pack uses 215, vanilla 255).

For a specific texture, `textures/entity/my_train.png`, add
`my_train.texture_set.json` next to it:

```json
{
  "format_version": "1.21.30",
  "minecraft:texture_set": {
    "color": "my_train",
    "metalness_emissive_roughness_subsurface": "my_train_mers"
  }
}
```

`my_train_mers.png` matches the colour texture's size, one channel each:

| Channel | Meaning | For a rail car |
|---|---|---|
| R | Metalness | Painted 0, bare stainless 255 |
| G | Emission | Destination boards and headlights 200–255, else 0 |
| B | Roughness | Polished bodywork 40–70, matte 180+ |
| A | Subsurface | 0 normally |

A texture set is ignored unless every image it names sits **in the same pack,
in the same folder** — it cannot borrow an image from another pack.

## Tuning

The settings files are generated by `tools/generate_bedrock.py`; the numbers
sit near the top of that script. Change them there and regenerate (editing the
JSON directly works too, but regenerating overwrites it).

| Goal | In `tools/generate_bedrock.py` |
|---|---|
| Stronger / weaker sun | `SUN_ILLUMINANCE` |
| Sunset colours | `SUN_COLOR` (the light) and `golden` / `sunset` etc. in `sky_tables` and `DUSK_ZENITH` (the sky) |
| Bluer sky | `DAY_ZENITH` and `RAYLEIGH` |
| Halo around the sun | `SUN_MIE` (brightness) and `SUN_GLARE` (higher keeps it closer to the sun) |
| Darker / lighter shadows | `SKY_INTENSITY` (sky light, 0.1–1.0; lower is darker shade) |
| Darker / lighter caves | `AMBIENT_ILLUMINANCE` |
| Brighter nights | `MOON_ILLUMINANCE` |
| Less / more haze | first number of each `HAZE` entry (density) |
| Stronger light shafts | third number of each `HAZE` entry (forward scattering; closer to 1 concentrates it toward the sun) |
| Overall character | `TONE_MAP` (`aces`, `generic`, `hable`, ...) |
| Calmer colour | `saturation` / `contrast` in `BASE_GRADE` |
| Still water | `waves.enabled` in `WATER` → `False` |
| More biome colour in water | `biome_water_color_contribution` in `WATER` (0–1) |
| Block light colours | `LIGHT_COLORS` |
| Cloud brightness and sunset tint | `ambient_light_illuminance` (brightness) and `directional_light_contribution` (how much the sun colours them) in `CLOUD_CUBEMAP` |
| Amount of cloud | `coverage` (share of the sky) in `CLOUD_VARIANTS`, in `tools/draw_sky.py` |
| How the game places the sky images (if clouds sit wrong) | `BOX_HEIGHT` (box height ÷ width) and `MIRROR_SIDES`, in `tools/draw_sky.py` |
| Tilt of the sun's path | `ORBITAL_OFFSET` (degrees) |

```bash
python3 tools/generate_bedrock.py --vanilla <bedrock-samples>/resource_pack
python3 tools/check_bedrock.py --vanilla <bedrock-samples>/resource_pack
```

Minecraft silently ignores a mistyped key or an out-of-range value rather than
reporting it, so run the check before installing.

---

# Java Edition

A deferred shader pack for Iris / OptiFine, built around **entities casting
shadows shaped like their models** — there the shadow mapping is written in the
pack rather than supplied by the engine.

- Requires **Iris 1.6+** (recommended) or **OptiFine H9+**, Minecraft 1.16.5 – 1.21.x
- Install: drop `VibrantVisuals-Java-*.zip` in `.minecraft/shaderpacks/`
- Details: [docs/ENTITY_SHADOWS.md](docs/ENTITY_SHADOWS.md), [docs/PIPELINE.md](docs/PIPELINE.md)

Options are available in English and Japanese. Profiles: `Potato` through
`Ultra`. For long consists, start at `High`, then raise `Shadow Distance` and
`Entity Shadow Range`.

---

## Development

The Bedrock tools need Mojang's vanilla resource pack (`resource_pack` in
[Mojang/bedrock-samples](https://github.com/Mojang/bedrock-samples)) and
Python with Pillow and numpy.

```bash
git clone --depth 1 https://github.com/Mojang/bedrock-samples
pip install pillow numpy
V=bedrock-samples/resource_pack

python3 tools/generate_bedrock.py --vanilla $V   # settings files (bedrock/ and diagnostic/)
python3 tools/draw_sky.py                        # round sun and moon, cloud skyboxes (takes minutes)
python3 tools/draw_water.py                      # plain water textures
python3 tools/check_bedrock.py --vanilla $V      # keys, value ranges, every biome covered
tools/package.sh --vanilla $V                    # distributables, including the relief add-on

python3 tools/validate_shaders.py     # Java GLSL, 52 stages x 4 macro variants
python3 tools/check_options.py        # Java options consistency
```

Pass `--glslang <path>` if `glslangValidator` is not on `PATH`
([prebuilt binaries](https://github.com/KhronosGroup/glslang/releases)).

## License

MIT — see [LICENSE](LICENSE). The relief add-on (output of
`tools/build_pbr.py`) contains Mojang's textures, is not covered by this
license, and is for personal use only.
