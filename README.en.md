# Vibrant Visuals

[日本語](README.md) | **English**

A deferred shader pack for Minecraft Java Edition, built around one idea:
**entities should cast shadows shaped like their models**, not the flat oval
the game paints underneath them.

Entities with custom models — the rolling stock of a train mod, a ship, an
aircraft — go through the same shadow pass as terrain, so the silhouette of a
car body, the gap between bogies and the light coming through its windows all
land on the ground as they should.

---

## Requirements

| | |
|---|---|
| Loader | **Iris 1.6+** (recommended) or **OptiFine H9+** |
| Minecraft | 1.16.5 – 1.21.x |
| GPU | OpenGL 3.3 or newer |

Iris is recommended because it supports `entityShadowDistanceMul` (see below).
The pack runs on OptiFine; that one setting is simply ignored there.

## Installing

1. Take a release zip, or build one with `tools/package.sh`
2. Drop it in `.minecraft/shaderpacks/`
3. In game: **Options → Video Settings → Shaders**, pick `VibrantVisuals`

The repository itself is a valid shader pack, so placing this folder in
`shaderpacks/` works too.

---

## Entity shadows

### What changes

Vanilla Minecraft draws a **flat oval texture** under each entity. Every model
gets the same ellipse, so a twenty-block train car drops the same shadow as a
chicken.

This pack instead:

- **Renders entities into the shadow map.** Terrain, block entities and
  entities share one pass, so the shadow always follows the model's real
  outline — including self-shadowing, such as a roof shading the flank below it.
- **Discards the vanilla blob**, which would otherwise sit as a dark ellipse
  underneath an otherwise correct shadow. Toggle: `Hide Blob Shadow`.
- **Keeps the colour of light that passed through something translucent.**
  Stained glass and tinted windows tint the floor rather than blocking it.
- **Hardens at contact and softens with distance.** The shadow stays crisp
  where a bogie meets the rail and spreads under a roof overhang.

### Registering a vehicle mod

Open `shaders/entity.properties` and append the mod's entity ids:

```properties
# Rail vehicles
entity.4011 = minecraft:minecart minecraft:chest_minecart \
              <modid>:<entity_name> <modid>:<entity_name2>

# Road and water
entity.4010 = minecraft:boat minecraft:chest_boat \
              <modid>:<entity_name>
```

Registered entities are shaded as **vehicles**: lacquered paintwork driven by
the `Vehicle glossiness` slider, and a shadow bias tuned for a large rigid body.

> **Shadows work without this.** Registration only changes how the surface is
> shaded. Listing an id that does not exist is harmless — the loader logs it.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Dark banding across a model | Raise `Entity Shadow Bias` |
| Shadow floats away from its caster | Lower `Entity Shadow Bias` / `Shadow Bias` |
| Shadow vanishes at a distance | Raise `Entity Shadow Range` (Iris only), then `Shadow Distance` |
| Rear of a long consist has no shadow | Same; set `Shadow Distance` beyond the full length |
| Shadows look blocky | Raise `Shadow Resolution`, or lower `Shadow Distortion` to even out near and far quality |
| A dark ellipse remains underfoot | Check `Hide Blob Shadow` is on |
| No shadows at all | Check shaders are enabled and `Shadow Distance` is not 0 |

The mechanics are written up in [docs/ENTITY_SHADOWS.md](docs/ENTITY_SHADOWS.md).

---

## Settings for station and depot scenes

Long consists under a platform canopy respond well to:

| Setting | Suggested | Why |
|---|---|---|
| Shadow Distance | 192–256 m | Has to cover the whole consist |
| Entity Shadow Range | 2.0–3.0 | Stops long vehicles being culled by origin distance |
| Shadow Distortion | 0.40–0.55 | Evens out quality from the near end to the far end |
| Shadow Resolution | 2048–4096 | Resolves window frames, handrails, pantographs |
| Vehicle Glossiness | 0.70–0.85 | Reads as painted bodywork |
| Sun Path Angle | -30 to -20° | Keeps the light raking across the flanks all day |

The `High` profile is close to this; start there and adjust.

---

## Options

Everything is adjustable from the in-game shader options screen, in English or
Japanese.

| Screen | Contents |
|---|---|
| Shadows | Resolution, distance, filter, softness, distortion, bias, coloured shadows |
| Entities & Vehicles | Entity-only bias, shadow range, blob shadow, glossiness |
| Lighting | Sun, sky, block light and its colour temperature, specular, AO |
| Sky & Atmosphere | Sun path, sky saturation, fog, light shafts, clouds |
| Water & Reflections | Waves, reflections, refraction, absorption, SSR |
| Waving | Plants, leaves, wind strength |
| Image & Colour | Tone curve, auto exposure, white balance, saturation, bloom, TAA, sharpening |

Profiles: `Potato`, `Low`, `Medium`, `High`, `Ultra`.

---

## Development

The shaders can be checked without launching Minecraft.

```bash
# Compile all 52 stages under 4 macro variants with glslang.
# Includes are resolved the way the loaders do, and reported error lines are
# mapped back to the file they actually came from.
python3 tools/validate_shaders.py

# Cross-check the options across GLSL, shaders.properties and each .lang file
python3 tools/check_options.py

# Build a distributable zip
tools/package.sh
```

Pass `--glslang <path>` if `glslangValidator` is not on `PATH`; prebuilt
binaries are on the
[glslang releases page](https://github.com/KhronosGroup/glslang/releases).

The render pipeline is described in [docs/PIPELINE.md](docs/PIPELINE.md).

## License

MIT — see [LICENSE](LICENSE).
