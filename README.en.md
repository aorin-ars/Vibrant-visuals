# Vibrant Visuals

[日本語](README.md) | **English**

Shader-mod looks for Minecraft, for **both editions**.

| | Contents | Goes to |
|---|---|---|
| [`bedrock/`](bedrock/) | Resource pack for Vibrant Visuals (deferred rendering) | open the `.mcpack` |
| [`java/`](java/) | Shader pack for Iris / OptiFine | `.minecraft/shaderpacks/` |

> **The two editions use completely different formats.** A Java shader pack
> dropped into Bedrock does not even appear in the list, and vice versa.

---

# Bedrock Edition

## Requirements

- Minecraft Bedrock **1.21.80 or newer**
- **Vibrant Visuals switched on** in Video Settings

## Installing

1. Open `VibrantVisuals-*.mcpack` — it imports itself
2. **Settings → Video → Vibrant Visuals**: on
3. In the world's **Settings → Resource Packs**, activate the pack

To install by hand, unzip it into `com.mojang/resource_packs/`.

## Entity shadows

**Entities casting shadows shaped like their models is a feature of Vibrant
Visuals itself** — switching it on in Video Settings is what produces them.

Their quality, though, *is* configurable from a resource pack
(`shadows/global.json`):

| Key | This pack | Meaning |
|---|---|---|
| `shadow_style` | `soft_shadows` | Softens the shadow edge |
| `texel_size` | 2048 | Shadow map resolution — higher resolves window frames, handrails, bogies |

Drop `texel_size` to 1024 if it costs too much performance.

What a resource pack can and cannot change:

| Can change | Cannot change |
|---|---|
| Shadow softness and shadow map resolution | Which entities cast shadows |
| Sun and moon illuminance and colour | Shadow bias (the striping trade-off) |
| Ambient and sky light intensity | The shader code itself |
| Atmospheric scattering — sky colour, haze, sun glare | |
| Colour grading — contrast, saturation, temperature | |
| Water — waves, caustics, turbidity | |
| PBR defaults for blocks and entities | |

**The other way to make shadows read is to raise the sun and lower the ambient
fill**, which is what the values below do.

| Setting | Vanilla | This pack | Why |
|---|---|---|---|
| Sun illuminance at noon | 100 | 132 | Widens the gap between lit and shadowed |
| Ambient | 0.02 / white | 0.014 / `#BFD4FF` | Shadows fill with sky blue instead of crushing to black |
| Sky intensity | 1.0 | 1.30 | Same; more blue bounce inside shadows |
| Rayleigh strength | 10 | 14 | Deeper blue at the zenith |
| Sun Mie strength (day) | 0.0 | 0.22 | Glow around the sun during the day |
| Contrast / saturation | 1.15 / 1.05 | 1.22 / 1.14 | Photographic punch |
| Water waves | off | on | A surface that moves |
| Entity roughness | 255 | 205 | A little sheen on bodywork and creatures |

## The manifest's `capabilities`

```json
"capabilities": ["pbr"]
```

**Without this line every deferred rendering file — `lighting`, `atmospherics`
and the rest — is silently ignored.** Texture replacement still works, so the
pack looks installed and does nothing, which is the most confusing way for it to
break. `tools/check_bedrock.py` catches it.

## Making an add-on's vehicles look metallic

Vibrant Visuals supports PBR. Adding a **texture set** beside an add-on's
texture gives it lacquered paintwork. For `textures/entity/my_train.png`, add
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

> A constant-value form also exists — the same `[metalness, emission, roughness,
> subsurface]` array `pbr/global.json` uses — and needs no image at all. It is
> used by shipping Vibrant Visuals packs.

## Tuning

Edit the JSON in `bedrock/` directly — they are only numbers.

| Goal | File and key |
|---|---|
| Deeper shadows | `lighting/global.json` → lower `ambient.illuminance` |
| Bluer shadows | same file → push `ambient.color` bluer |
| Stronger sun | same file → raise `sun.illuminance` |
| Bluer sky | `atmospherics/atmospherics.json` → `rayleigh_strength` |
| Calmer colour | `color_grading/color_grading.json` → `saturation` / `contrast` |
| Still water | `water/water.json` → `waves.enabled: false` |
| Sharper shadows | `shadows/global.json` → raise `texel_size` (costs performance) |
| Glossier entities | `pbr/global.json` → lower the third value under `actors` |

Then check it:

```bash
python3 tools/check_bedrock.py
```

Minecraft silently ignores a mistyped key rather than reporting it, so run this
before installing.

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

```bash
python3 tools/check_bedrock.py        # Bedrock pack, including key-name typos
python3 tools/validate_shaders.py     # Java GLSL, 52 stages x 4 macro variants
python3 tools/check_options.py        # Java options consistency
tools/package.sh                      # Build both distributables
```

Pass `--glslang <path>` if `glslangValidator` is not on `PATH`
([prebuilt binaries](https://github.com/KhronosGroup/glslang/releases)).

## License

MIT — see [LICENSE](LICENSE).
