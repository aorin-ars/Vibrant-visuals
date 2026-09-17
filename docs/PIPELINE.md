# Pipeline

What runs, in what order, and why each buffer holds what it does.

## Buffers

| Buffer | Format | Contents | Cleared |
|---|---|---|---|
| `colortex0` | RGBA16F | Scene radiance, linear HDR | yes |
| `colortex1` | RGBA16 | Octahedral normal `.xy`, block light `.z`, sky light `.w` | yes |
| `colortex2` | RGBA16 | Albedo `.rgb`, material id `.a` | yes |
| `colortex3` | RGBA16 | Roughness, reflectance, emission, subsurface | yes |
| `colortex4` | RGBA16F | Auto exposure history | **no** |
| `colortex5` | RGBA16F | Temporal AA history | **no** |
| `colortex6` | RGBA16F | Ambient occlusion, then bloom | yes |
| `colortex7` | RGBA16F | Opaque scene copy, then bloom | yes |
| `shadowtex0` | depth | Every caster, translucent included | yes |
| `shadowtex1` | depth | Opaque casters only | yes |
| `shadowcolor0` | RGBA | Transmission tint of translucent casters | yes, to white |

The two uncleared buffers are the ones with a frame-to-frame dependency:
clearing either would leave exposure jumping to its target instantly and TAA
with no history to accumulate into. They are declared in
`lib/buffers_persist.glsl`, which only composite and deferred programs include —
the loaders reject those directives anywhere else.

`colortex6` and `colortex7` are each used twice, by passes that never overlap.

## Passes

| Pass | Reads | Writes | Does |
|---|---|---|---|
| `shadow` | — | shadow buffers | Terrain, block entities and entities from the sun's view |
| `gbuffers_skybasic` / `skytextured` | — | 0 | Procedural sky, sun and moon. No g-buffer, so the far plane stays untouched |
| `gbuffers_*` (opaque) | — | 1, 2, 3 | Material properties only; `colortex0` is left alone so the sky survives |
| `deferred` | 1, depth | 6 | SSAO |
| `deferred1` | 0–3, 6, shadow | 0, 7 | All opaque lighting, plus fog. `colortex7` is the copy the translucent pass reads |
| `gbuffers_water` / `hand_water` / `weather` | 7, depth, shadow | 0 | Forward-shaded translucents, with SSR and refraction |
| `composite` | 0, depth, shadow | 0 | Volumetric light, marched through the same shadow map |
| `composite1` | 0, 5, depth | 0, 5 | Temporal AA |
| `composite2` | 0 (mips), 4 | 4 | Auto exposure |
| `composite3` | 0 (mips) | 6 | Bloom gather |
| `composite4` | 6 | 7 | Bloom blur |
| `final` | 0, 4, 7 | screen | Exposure, tone curve, grade, vignette, dither |

## Choices worth knowing about

**Opaque gbuffers do not write `colortex0`.** The sky programs draw into it
first, and `deferred1` replaces it for every pixel nearer than the far plane.
Writing black there in between would just burn bandwidth.

**Clouds are full members of the g-buffer.** `blend.gbuffers_clouds = off` plus
a dithered alpha test turns them into cutout geometry, which means they are lit,
fogged and reflected like anything else. Temporal AA turns the dither back into
a soft edge. The alternative — blending them straight into `colortex0` — would
leave `deferred1` lighting the terrain behind them and overwriting the result.

**Translucents read a copy, not the live buffer.** `deferred1` writes the
finished opaque frame to `colortex7`, so `gbuffers_water` can refract and
reflect without sampling a buffer it is also writing to.

**Exposure reads and writes `colortex4` in one pass.** That is safe here:
the loaders double-buffer every colortex, so a program reads the previous
frame's contents while writing the next.

**Fog fades towards the sky in that direction**, evaluated with the same
function `gbuffers_skybasic` uses. Distant terrain therefore dissolves into
exactly the sky behind it, at any time of day, with no per-time-of-day tables.

## Adding a pass

Composite and deferred programs must be numbered consecutively from zero —
`deferred`, `deferred1`, `deferred2`, … — with no gaps, or the loader stops
looking. Each needs a `.vsh` (three lines, including
`lib/program/fullscreen_vertex.glsl`) and a `.fsh` carrying its own
`/* RENDERTARGETS: */` comment.

Run `python3 tools/validate_shaders.py` afterwards. It resolves includes the
way the loaders do, compiles every stage under four macro configurations, and
maps reported line numbers back to the file they came from.
