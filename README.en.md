# Vibrant Visuals

[日本語](README.md) | **English**

Shader-mod looks for Minecraft, for **both editions**.

| | Contents | Goes to |
|---|---|---|
| [`bedrock/`](bedrock/) | **VYSE-Vibrant Visuals** — a Complementary Unbound style resource pack for Vibrant Visuals | open the `.mcpack` |
| [`java/`](java/) | Shader pack for Iris / OptiFine | `.minecraft/shaderpacks/` |

> **The two editions use completely different formats.** A Java shader pack
> dropped into Bedrock does not even appear in the list, and vice versa.

---

# Bedrock Edition: VYSE-Vibrant Visuals

Recreates the look of the Java shader **Complementary Shaders (Unbound style)**
with Bedrock's Vibrant Visuals renderer.

## Requirements

- Minecraft Bedrock **1.26.0 or newer**
- **Vibrant Visuals switched on** in Video Settings

## Installing

1. Open `VYSE-Vibrant-Visuals-*.mcpack` — it imports itself
2. **Settings → Video → Vibrant Visuals**: on
3. In the world's **Settings → Resource Packs**, activate the pack

**Optional PBR add-on**: put **VYSE-Vibrant Visuals PBR**
(`VYSE-Vibrant-Visuals-PBR-*.mcpack`) **above** VYSE-Vibrant Visuals and
activate both, for material detail:

| | What it does |
|---|---|
| Relief | **Nearly every block**: height maps for 1,221 block textures (leaves, flowers, crops, glass, doors, rails and animated blocks included) and normal maps for the 79 textures of chests, beds, shulker boxes, bells, mob heads, signs and the enchanting table's book (Complementary's generated normals; at half the blocks' strength, so these made objects read as clean, smooth surfaces with a hint of grain). Strong on cobblestone, ores and bricks, medium on wood, nearly flat on wool, none on plain flat blocks such as concrete (a height map draws a thin seam line along block edges, which shows as a grid on plain blocks), gentler on foliage, faint on glass; crevices a little rougher than the raised parts. Only water, lava (vanilla's own relief kept), fire, portals and bubble columns stay as they are |
| Glow | 40 light blocks — glowstone, sea lanterns, froglights, shroomlights, magma and more — glow like light sources (vanilla keeps glowstone at 41 of 255). **Ore minerals glow faintly** (diamond, emerald, lapis, redstone, gold, iron, copper, nether gold, quartz; not coal), like Complementary's glowing ores |
| Shine | Ice, metal and gem blocks, obsidian, glazed terracotta, polished stone, bells and copper chests are smoother, so they catch reflections; gem ores are glossy in their minerals |
| Light through glass | **Stained glass (blocks and panes, 15 colours, not black) lets light through and glows in its own colour when the sun is behind it** — stained glass windows and roofs. Vanilla gives glass no transmission at all. Sunlight passing through cannot tint the floor or walls behind the glass, though: Vibrant Visuals shadows have no colour and no setting for it |
| Wet in rain | **Mobs, boats, minecarts, armor stands and other entities turn slightly darker and glossy while rain falls on them or they are in water** (roughness about halved, so reflections and highlights show), and dry as soon as they are under cover or out of the water. Covers 172 vanilla entities (not the player, whose texture is the skin); add-on entities such as trains are not affected |

A block's texture set may only use images in its own pack, so this add-on
has to contain the vanilla block textures. It is therefore built from your
copy of the vanilla files instead of living in the repository
([how to build it](#development)). **Personal use only** — do not
redistribute it.

To install by hand, unzip into `com.mojang/resource_packs/`.

## What changes

| | Vanilla Vibrant Visuals | VYSE-Vibrant Visuals |
|---|---|---|
| Picture | "generic" tone mapping | **ACES (filmic) tone mapping**: firm shade, rich midtones, bright skies and sunsets rolling smoothly into white. A different look from stock Vibrant Visuals at the root |
| Sunlight | Whitish, fades early in the afternoon | **Clear white** at noon, at vanilla's 100 (125 blew out bright walls and the sky); the contrast with the shade comes from less sky light. Gold as the sun gets low, then deep orange, and a **red-orange sun** in its last few degrees at sunset and sunrise, the land glowing orange |
| Sky through the day | Muted | **Strongly orange sunrises and sunsets**, like photographs. Sunrise (indigo overhead, a red-orange band along the horizon) → morning (warm cream horizon in a blue sky) → noon (blue sky paling to an almost white horizon) → late afternoon (gold to orange horizon) → sunset (amber high into the sky over a red-orange horizon, a wide glow around the sun) → afterglow (red fading to violet) → night (navy) → late night (deep navy). Never black |
| Sky | Nearly one even blue (Rayleigh 10) | Rayleigh down to 1.3, so the sky is a real gradient from the blue zenith to a pale horizon; a **small halo gathered around the sun** instead of vanilla's milky haze over half the sky; a faint halo around the moon at night |
| Shadows | Grey (full sky light) | Sky light cut to 60 %, for a clear step between sun and shade; shade stays blue-grey, never black. Short shadows (noon sun 78° up). More sky light at sunset, so the coloured sky fills the shade |
| Night | Moonlight 0.4 | Early in the night **moonlight 0.6**, blue: moonlit faces stand out and the valley haze glows blue. **The deep night is dark like a real one**: moonlight 0.2 (half of vanilla), less sky light, a nearly black-blue sky; shapes show faint blue-grey and shade is close to black. Torches and other block light are not dimmed, so they stand out in the dark |
| Air | Uniform fog in some biomes | **Clear air with depth**: distant terrain fades to blue rather than milky white, haze gathers in valleys and caves (densest low, gone around y=170), glows gold toward a low sun and blue under the moon. **Light shafts** through leaves and cave openings **show without looking into the sun** — with the sun off screen or behind a tree, wherever the light makes them. Mistier in humid forests, swamps and savannas, clearer in deserts; none in the Nether |
| Rain | Dark grey fog | **A soft, misty rain**: a pale blue-grey mist softens things a few dozen blocks away and swallows the distance, trees turning to grey silhouettes (it starts at 6 % of the render distance and is complete at 62 %); the haze thickens and reaches over the hills. Raindrops splash as the game's own small blue droplets |
| Water | No waves, the old water pattern | **Clear water**: nothing in it but water (no plankton, no silt) and a more transparent surface than vanilla's, so the bottom and water plants show through; vanilla's water pattern (white streaks) and its normal map are replaced, leaving only gentle ripples, so the sky and shore reflect cleanly; a hint of the biome's water colour |
| Underwater | — | The game's own (an earlier underwater fog made the player's shadow show up as a dark shape, so it was removed) |
| Block light | One colour | **Coloured**: torches and fire orange, soul fire cyan, redstone red, amethyst and ender blocks violet, sea lanterns cyan-white, end rods a cool bluish white, invisible light blocks the cool white of fluorescent tubes (#EEF4FF) for lighting train cars and stations — 122 blocks |
| Sun and moon | Squares | **Small round sun** (1/6 the width of vanilla's square; its halo comes from the sky's scattering), **small round moon** with craters and all 8 phases |
| Clouds | Flat blocky slabs | **Soft fair-weather clouds painted across the whole sky** (a skybox): white patches with blue gaps between them and ragged, wispy margins, smaller and denser toward the horizon; tinted orange at sunset. [See below](#sky-clouds-skybox) |
| Grading | Contrast 1.15 / saturation 1.05 | On top of ACES: contrast 1.10 / saturation 1.10, no extra gain (it helped blow out daylight), and a slightly cool white balance (6100 K) — the clean, faintly blue cast of Complementary's daytime (leaves blue-green rather than lime); shadows lean slightly cool, highlights slightly warm (tinted, not brightened) |

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
take on the light — white at noon, gold to orange at sunset, dim grey-blue
shapes at night. In rain the game dims the sun and greys the sky, and the
clouds grey over with it, so the whole sky reads as one overcast deck (the
amount of cloud itself is an image and cannot follow the weather).

**Choose the clouds in the pack's settings**: world Settings → Resource Packs →
tap the active VYSE-Vibrant Visuals → the gear (⚙).

| Option | What it is | The game's own clouds |
|---|---|---|
| **Sky: soft clouds** (default) | Soft fair-weather clouds | **Hidden automatically** (no flat blocky clouds) |
| Sky: soft clouds + the game's clouds | The same clouds | Keep them on — for pairing with the shadow-casting vanilla clouds |
| Sky: no clouds | Nothing painted | Up to you |
| Lite: the game's clouds, faster | Nothing painted, plus lighter water. [Lite mode](#lite-mode) | Shown as usual (turn them off in Video Settings for even less work) |

Worth knowing:

- Painted clouds **do not move**; they are fixed to the sky
- Distant clouds fade to pale blue inside the images (the game's haze erased low clouds entirely)
- Only the Overworld has them; the Nether and the End are unchanged

The face order (0–3 the sides from left to right, 4 the top, 5 the bottom) was
confirmed by matching the edges between faces of several working skyboxes.

**The eye is not at the centre of the sky cube.** The six images form an
ordinary cube, but the eye sits 0.40 half-widths below its centre. So eye
level (the horizon) falls **70 % of the way down the side images**, not
across their middle; the side images' middle row shows about 22° up, and
the top image covers only the sky above 45–55°.

This was worked out from two in-game screenshots: the middle row of the side
images shows as a straight line in the sky that bends at the cube's corners,
and the vanishing points of those bends fix the field of view and eye level.
A published skybox that draws its horizon 70 % of the way down its side
images agrees. The clouds are painted pixel by pixel for this arrangement,
so they keep their proper size and spacing in game (`EYE_BELOW_CENTRE` in
`tools/draw_sky.py`). Two earlier versions got it wrong: painted for an eye
at the centre, the clouds stopped in a square overhead; painted for a flat
box, they came out stretched tall, with a mirrored copy below the horizon.

The clouds themselves are a fair-weather field on a layer that curves with
the planet: noise at three scales — patches and clear gaps, clumps within a
patch, ragged margins — with thin, translucent edges and solid white cores.
The patches line up a little along the wind, but nothing forms stripes or
swirls, so the sky looks natural whichever way you look (the previous
cirrus, its strands all converging on one point of the horizon, read as a
swirl). Every face samples the same continuous layer, so there are no seams.
No photos are used; it is all computed. No sun direction is baked in (the
real one moves); the game adds the sun's colour.

## Lite mode

Pick **Lite: the game's clouds, faster** in the pack's settings (the gear ⚙)
for a lighter version: light, sky and fog look the same; only the costly parts
change.

| | Normal | Lite |
|---|---|---|
| Clouds | Painted cloud images (6 × 1024×1024) | **No images**: the game's usual clouds (which Video Settings can also turn off) |
| Water waves | 20 octaves | **10 octaves** (about half the work per water pixel). Each octave steps further, so the surface still runs from the same broad swell to the same fine ripples |
| Light, sky, fog, PBR, shadows | | Unchanged (changing them changes the look) |

To be honest, **a pack cannot make much lighter**. Most of Vibrant Visuals'
cost is the rendering itself — shadows, volumetric fog, reflections — and
only the video settings change its quality. For a smooth game, use lite mode
together with these video settings (names vary by version; roughly the most
gain for the least visible loss first):

1. **Upscaling / resolution**: upscaling on, or a slightly lower render resolution. The biggest gain
2. **Point light shadows**: off (shadows of torch light; hardly noticed by day or outdoors)
3. **Volumetric fog quality**: low to medium (light shafts stay)
4. **Reflection quality**: low (water reflections a little coarser)
5. **Shadow quality**: medium (distant shadows a little coarser)
6. **Render distance**: a little shorter (the distance haze hides it)
7. **Clouds**: off (in lite mode they are the game's clouds, so Video Settings can hide them)

The **PBR add-on** (block relief and gloss) adds textures and memory; on a
weak device, leaving it off saves the most.

## What a resource pack cannot do

Vibrant Visuals' shaders belong to the engine; a resource pack only supplies
numbers and textures. These Complementary features cannot be reproduced:

- Grass and leaves waving in the wind
- **Moving** volumetric clouds, auroras, nebulae (static clouds painted into the sky are possible — see above)
- The ground itself turning wet and reflective in rain (a block's gloss comes from its texture and cannot follow the weather; entities can switch textures when wet, which the PBR add-on does)
- A darker, overcast sky or softer light only while it rains (lighting and sky settings cannot follow the weather; the overcast look of rain is the game's own)
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
subsurface]`; lower roughness is glossier — this pack uses 190, vanilla 255).
That is a soft satin: a broad, faint highlight, no mirror reflections. It is
not smoother because Vibrant Visuals does not block the sky inside an entity:
every surface inside a train car is lit by, and reflects, the open sky, and at
150 interiors washed out pale blue. Vanilla mobs without a texture set use it
too; it sits mid-range in Mojang's own mob materials (Steve: 154-255).

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

### Generating them for an MTC train (`tools/build_train_pbr.py`)

For MTC train add-ons the texture sets can be generated:

```bash
python3 tools/build_train_pbr.py train.mcaddon --out build/train_pbr --preview build/train_preview
```

It paints every model face's UV rectangle onto the texture to learn which
part (bone) uses each pixel, then picks a material from the bone names (the
MTC / TBTK template's romanised Japanese: `tsurikawa` strap rails, `turikawa`
straps, `nidana` luggage racks, `sodesikiri` seat-end partitions, `yukasita`
underfloor, `maku` destination signs, `lcd`, `mascon`, `panta`...), from MTC's
alpha code (255 outside, 127 inside, lower for light fittings, 0 for window
cut-outs) and from colour. Stainless is satin silver, stripes are glossy film, the
black front is glass-glossy, walls are laminate, floors rubber, seats
moquette; signs, LCDs, cab lamps, headlights and ceiling lights glow; no bump
maps (clean RTX-style surfaces). Bodies and fittings stay mostly diffuse with a
thin metallic sheen: fully metallic, they mirrored their surroundings and
turned grey by day, and glittered. The add-on half self-lights the whole
interior; in Vibrant Visuals that flattens the shading, so surfaces only get
a faint glow and the light fittings do the glowing.

The output is **a separate resource pack to put above the add-on**; the add-on
is not modified. Since a texture set needs its images in the same pack, it
contains copies of the add-on's colour textures — **personal use only**, like
the add-on. The colours are unchanged; only the alpha code that half
self-lights the interior is taken out, since it washes the cabin flat white
in Vibrant Visuals (`--keep-glow` keeps it). `--preview` also writes images of the part guesses and of the
materials (red = glow, green = gloss, blue = metal).

## Smoothing mesh parts (`tools/smooth_meshes.py`)

Bedrock models are boxes ("cubes"), and some add-ons add free-form meshes
(`poly_mesh`). A mesh's polygons share vertices, but **the classic renderer
shades with exactly the normals written in the model file**; most exporters
write each polygon's flat normal, so even a rounded part shows a crease along
every edge. This tool is for that case. Some models already have smooth
normals and show creases only in Vibrant Visuals; that comes from how Vibrant
Visuals draws them, not from the model, and this tool cannot fix it (the
cause is being narrowed down). Resource packs cannot change the Vibrant Visuals
shaders, so the only fix is in the model file (vanilla models are all boxes,
with no meshes).

```bash
python3 tools/smooth_meshes.py addon.mcaddon --out build/smooth_meshes
```

Each mesh corner gets the average normal of the polygons sharing its vertex
(area-weighted), so shading flows across shared edges. Folds sharper than
`--angle` (default 80°) stay sharp — a cylinder's caps keep their edge while
its sides go smooth (`--angle 180` smooths everything that shares a vertex).
Box parts are left exactly as they are. The output is **a separate resource
pack to put above the add-on**, holding only the model files with meshes,
under the same paths and identifiers so they replace the add-on's. The add-on
is not modified. Personal use only.

## Clear sky after reopening a rainy world (`weather_sync/`)

Reopen a world while it rains and the rain falls from a clear, sunny sky —
the game's own bug, which lasts until the weather next changes. A resource
pack cannot touch the weather, so there is a **separate behavior pack, "VYSE
Weather Sync"** (`VYSE-Weather-Sync-*.mcpack`). Turn it on under the world's
Settings → Behavior Packs: three seconds after you join, if it is raining
(or thundering), it stops the rain for a moment and starts it again, which
brings the rainy sky back. The game picks a new duration for the rain;
nothing else in the world is changed.

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
| Night brightness | `MOON_ILLUMINANCE` (the deep night is its 0.400–0.600 entries), the night entries of `SKY_INTENSITY`, `DEEP_NIGHT_ZENITH` (midnight sky colour) |
| Less / more haze | first number of each `HAZE` entry (density) |
| How light shafts show | third number of each `HAZE` entry (forward scattering: closer to 1 shows them only looking into the sun, lower shows them from the side too) |
| Overall character | `TONE_MAP` (`aces`, `generic`, `hable`, ...) |
| Calmer colour | `saturation` / `contrast` in `BASE_GRADE` |
| Still water | `waves.enabled` in `WATER` → `False` |
| More biome colour in water | `biome_water_color_contribution` in `WATER` (0–1) |
| Block light colours | `LIGHT_COLORS` |
| Cloud brightness and sunset tint | `ambient_light_illuminance` (brightness) and `directional_light_contribution` (how much the sun colours them) in `CLOUD_CUBEMAP` |
| Amount of cloud | `n + 0.03` in `cloud_density`, in `tools/draw_sky.py` (raise the `0.03` for more cloud) |
| How the game places the sky images (if clouds sit wrong) | `EYE_BELOW_CENTRE` (how far below the cube's centre the eye is), in `tools/draw_sky.py` |
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
python3 tools/draw_sky.py                        # round sun and moon, cloud skyboxes (takes minutes; also the lite clouds)
python3 tools/draw_water.py                      # plain water textures
python3 tools/check_bedrock.py --vanilla $V      # keys, value ranges, every biome covered
tools/package.sh --vanilla $V                    # distributables, including the PBR add-on

python3 tools/validate_shaders.py     # Java GLSL, 52 stages x 4 macro variants
python3 tools/check_options.py        # Java options consistency
```

Pass `--glslang <path>` if `glslangValidator` is not on `PATH`
([prebuilt binaries](https://github.com/KhronosGroup/glslang/releases)).

## License

MIT — see [LICENSE](LICENSE). The PBR add-on (output of
`tools/build_pbr.py`) contains Mojang's textures, is not covered by this
license, and is for personal use only.
