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
| Sunlight | Whitish, fades early in the afternoon | **Strong, clear white** at noon, 125 (vanilla 100), for a firm step between sun and shade; gold as the sun gets low, orange to red on the horizon |
| Sky through the day | Muted | Following a reference sequence: early morning (magenta turning orange-gold under deep blue) → morning (warm cream horizon in a blue sky) → noon (deep to pale blue) → late afternoon (gold to orange) → sunset (red-orange horizon under violet) → night (navy) → late night (deep navy). Starry navy nights, never black |
| Sky | Dull blue-grey | Vivid deep blue zenith, a horizon that stays blue instead of hazing white; a small sun with only a slight glow |
| Shadows | Grey | Short and crisp at noon (sun 78° up); filled with sky light, blue-grey rather than black; moonlit blue at night (moon 0.7, vanilla 0.4) |
| Air | Uniform fog in some biomes | **Clear air**: only a thin haze softening the far distance (densest low, thinning with height); a little more in humid forests and swamps |
| Rain | — | Haze thickens |
| Water | No waves, the old water pattern | **Clear water**: vanilla's water pattern (white streaks) and its normal map are replaced, leaving only gentle ripples, so the sky and shore reflect cleanly; a hint of the biome's water colour |
| Underwater | — | The game's own (an earlier underwater fog made the player's shadow show up as a dark shape, so it was removed) |
| Block light | One colour | **Coloured**: torches and fire orange, soul fire cyan, redstone red, amethyst and ender blocks violet, sea lanterns cyan-white — 106 blocks |
| Sun and moon | Squares | **Round sun** with a soft corona, **round moon** with craters and all 8 phases |
| Clouds | Flat blocky slabs | **Cumulus and cirrus painted into the sky** (a skybox), turning gold at sunset. [See below](#sky-clouds-skybox) |
| Grading | Contrast 1.15 / saturation 1.05 | Contrast 1.24 / saturation 1.28 — rich, firm colour clearly apart from stock Vibrant Visuals; shadows lean slightly cool, highlights slightly warm |

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
| **Sky: Unbound clouds** (default) | Puffy cumulus with thin high cirrus above | **Hidden automatically** (no flat blocky clouds) |
| Sky: high clouds only | Just the thin cirrus | Keep them on — for pairing with the shadow-casting vanilla clouds |
| Sky: no clouds | Nothing painted | Up to you |

Worth knowing:

- Painted clouds **do not move**; they are fixed to the sky
- Clouds reach down to the horizon; distant ones fade to pale blue inside the images (the game's haze erased the low clouds entirely)
- Only the Overworld has them; the Nether and the End are unchanged
- The cloud lighting values follow a published pack that paints clouds the
  same way; this pack's clouds have not been checked in game yet. Reports of
  how they look at noon, sunset and night will let them be tuned

The face order (0–3 the sides from left to right, 4 the top, 5 the bottom) was
confirmed by matching the edges between faces of several working skyboxes. The
clouds are separate fair-weather cumulus heaps on a layer that curves with the
planet, projected along each view direction, so they are large overhead, crowd
together toward the horizon, and join across the image edges.

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
| Sunset colours | `SUN_COLOR` (the light) and `golden` / `sunset` etc. in `sky_tables` (the sky) |
| Bluer sky | `DAY_ZENITH` and `RAYLEIGH` |
| Darker / lighter shadows | `AMBIENT_ILLUMINANCE` |
| Brighter nights | `MOON_ILLUMINANCE` |
| Less / more haze | first number of each `HAZE` entry (density) |
| Stronger light shafts | third number of each `HAZE` entry (forward scattering; closer to 1 concentrates it toward the sun) |
| Calmer colour | `saturation` / `contrast` in `BASE_GRADE` |
| Still water | `waves.enabled` in `WATER` → `False` |
| More biome colour in water | `biome_water_color_contribution` in `WATER` (0–1) |
| Block light colours | `LIGHT_COLORS` |
| Cloud brightness and sunset tint | `ambient_light_illuminance` (brightness) and `directional_light_contribution` (how much the sun colours them) in `CLOUD_CUBEMAP` |
| Amount of cloud | `coverage` (share of the sky) in `CLOUD_VARIANTS`, in `tools/draw_sky.py` |
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
