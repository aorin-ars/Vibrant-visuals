# Entity shadows (Java Edition)

> This document is about the **Java Edition** pack in `java/`, where the shadow
> mapping is written in the pack itself. On **Bedrock**, shape-accurate entity
> shadows come from the engine's own Vibrant Visuals renderer and a resource
> pack cannot change them — see [the README](../README.md) instead.

How Vibrant Visuals gets an entity to cast a shadow shaped like its model, and
which knob to reach for when it misbehaves.

[日本語の概要は README.md にあります。](../README.md#エンティティの影について)

---

## Why vanilla entities have blob shadows

Minecraft draws a single translucent oval on the ground beneath each entity.
It is a decal, not a shadow: it has no relationship to the model above it, so a
chicken, a horse and a twenty-block train car all get the same ellipse, scaled
to the entity's bounding box.

A shader pack only escapes that by putting the entity's actual geometry into a
shadow map — which means the entity has to be rendered a second time, from the
sun's point of view.

## The shadow pass

`shaders/shadow.vsh` and `shaders/shadow.fsh` are that second render.
`shaders.properties` asks the loader to send everything through it:

```properties
shadowTerrain       = true
shadowEntities      = true
shadowBlockEntities = true
shadowTranslucent   = true
shadowPlayer        = true
```

Nothing in `shadow.vsh` treats entities as a special case, and that is
deliberate. `gl_ModelViewMatrix` already carries the entity's own model
transform — its position, rotation and any animation the game applied — so
projecting an entity vertex is the same operation as projecting a block vertex:

```glsl
vec3 shadowViewPos = (gl_ModelViewMatrix * gl_Vertex).xyz;
vec3 clipPos = projectOrtho(shadowProjection, shadowViewPos);
gl_Position = vec4(distortShadowClip(clipPos), 1.0);
```

The one thing the vertex stage *does* branch on is waving foliage, and it
branches away from entities: `mc_Entity` is zero for anything that is not
terrain, so an entity never enters that path. This matters more than it looks.
If the shadow pass displaced a vertex by even a slightly different amount than
the gbuffers pass did, every shadow would sit beside its caster rather than
under it.

## Distortion, and why it is turned down here

A single shadow map covering 160 blocks at 2048² gives texels 0.156 blocks
across — too coarse for a handrail. The usual fix is to warp the map so more
texels land near the camera:

```glsl
clipPos.xy /= length(clipPos.xy) * SHADOW_DISTORTION + (1.0 - SHADOW_DISTORTION);
```

That is a good trade when the subject is the ground under your feet. It is a
bad trade when the subject is a 200-block consist stretching away down the
platform, because the far end of the train lands in the coarse part of the map
while the near end is far sharper than it needs to be.

Hence `Shadow Distortion` defaults to 0.75 rather than the 0.85–0.9 a
terrain-focused pack would use, and the station-scene guidance in the README
suggests going down to 0.40–0.55. At 0.0 the map is uniform: every shadow in
range gets identical quality.

## Bias

Shadow bias is a tug of war. Too little and a surface shadows itself in stripes
(*acne*); too much and the shadow slides out from under its caster
(*peter-panning*). The amount needed depends on how big a shadow texel is in
world units at that point — and with distortion in play, that varies across the
map.

So it is computed rather than hard-coded. The distortion divides xy by
`f = |xy| * k + (1 - k)`, so the local stretch is `f² / (1 - k)`:

```glsl
float shadowTexelWorldSize(vec2 clipXY) {
    float f = shadowDistortFactor(clipXY);
    float uniformTexel = 2.0 * shadowDistance / float(shadowMapResolution);
    return uniformTexel * f * f / max(1.0 - SHADOW_DISTORTION, 0.05);
}
```

Every offset in the file is a multiple of that number, which is what lets one
setting hold from the player's feet out to the shadow distance.

The offset is applied **along the surface normal**, not along the light:

```glsl
vec3 applyShadowBias(vec3 scenePos, vec3 normal, float NdotL, float biasMultiplier) {
    float texel = shadowTexelWorldSize(sceneToShadowClip(scenePos).xy);
    float grazing = saturate(1.0 - NdotL * NdotL);
    float offset = texel * (0.85 + 2.6 * grazing) * SHADOW_BIAS_SCALE * biasMultiplier;
    return scenePos + normal * offset;
}
```

Normal-offset bias keeps contact shadows attached. A bogie resting on the rails
still darkens the sleeper directly beneath it, which a plain depth bias would
push away.

### The entity multiplier

`biasMultiplier` is where entities diverge from terrain. Entity models are
thin, frequently double sided, and their parts intersect each other — all of
which produce acne at a bias terrain is perfectly happy with. Rather than
loosening the bias globally and blunting every terrain contact shadow,
`shadowBiasForMaterial()` hands entities their own multiplier:

```glsl
float shadowBiasForMaterial(float id) {
    if (id == MAT_ENTITY || id == MAT_VEHICLE || id == MAT_BLOCK_ENTITY || id == MAT_HAND) {
        return ENTITY_SHADOW_BIAS;
    }
    return 1.0;
}
```

`Entity Shadow Bias` defaults to 1.5. Raise it if a model shows dark bands;
lower it if its shadow looks detached.

## Contact hardening

A shadow is only razor sharp where the caster touches the receiver. The penumbra
grows with the distance between them, which is why the shadow under a bogie is
crisp and the one under a roof overhang is soft.

`sampleShadow()` reproduces that in two steps. First it searches for how far
above the receiver the occluders actually are, then it sizes the filter kernel
from that distance:

```glsl
float blockerDistance = max(depth - blocker, 0.0) * depthToWorld;
penumbraWorld = blockerDistance * SUN_ANGULAR_TAN * SHADOW_PENUMBRA_SCALE * SHADOW_SOFTNESS;
```

`SUN_ANGULAR_TAN` is the real tangent of the sun's angular radius.
`SHADOW_PENUMBRA_SCALE` then exaggerates it, because a physically exact solar
penumbra is narrower than one shadow texel at any resolution Minecraft can
afford — correct, and invisible.

Both the blocker search and the filter apply their offsets in *undistorted*
clip space, where xy is linear in world units. Offsetting after the distortion
would make the kernel elliptical, and differently elliptical depending on where
the caster happened to be standing.

## Coloured transmission

The loader keeps two depth buffers: `shadowtex1` holds opaque casters only,
`shadowtex0` holds everything. A texel that is lit in `tex1` but occluded in
`tex0` was shaded by something translucent, and the light that arrives keeps the
colour `shadow.fsh` stored for it:

```glsl
vec3 shadowTap(vec2 uv, float depth) {
    float opaque = step(depth, texture(shadowtex1, uv).r);
    float anything = step(depth, texture(shadowtex0, uv).r);
    vec3 tint = texture(shadowcolor0, uv).rgb;
    return vec3(opaque) * mix(tint, vec3(1.0), anything);
}
```

`shadow.fsh` only discards fully invisible texels (`a < 0.004`) rather than
alpha-testing at the usual 0.1, precisely so partly transparent casters stay in
`shadowtex0` where this test can find them.

`const vec4 shadowcolor0ClearColor = vec4(1.0);` makes untouched texels
transmit white, so anywhere nothing was drawn, light arrives untinted.

## Three more entity-specific details

**The vanilla blob is discarded.** Iris exposes it as the entity id
`minecraft:entity_shadow`, mapped in `entity.properties` and dropped in the
gbuffers fragment stage. The test is not restricted to entity programs, because
which gbuffers program the decal arrives through depends on the loader and the
game version.

**Long entities are kept in range.** Entities are culled from the shadow pass by
the distance of their *origin*. A 20-block car whose origin sits just past the
boundary loses its shadow entirely while most of it is still well inside the
shadow distance. `const float entityShadowDistanceMul = 2.0;` renders entities
out to a multiple of the terrain bound, which costs a little and removes the
pop. Iris only; OptiFine ignores the directive.

**Models with no normals still get shaded.** Custom entity models — especially
ones converted from OBJ — occasionally arrive with zero-length normals. Rather
than turning into flat silhouettes, they fall back to the surface's own
derivatives:

```glsl
float normalLength = length(vNormal);
if (normalLength < 1e-3) {
    normal = normalize(cross(dFdx(vScenePos), dFdy(vScenePos)));
    if (dot(normal, normalize(-vScenePos)) < 0.0) normal = -normal;
}
```

## Tuning reference

| Setting | Default | Raise it when | Lower it when |
|---|---|---|---|
| `Entity Shadow Bias` | 1.50 | A model shows dark banding | Its shadow looks detached |
| `Shadow Bias` | 1.00 | Terrain shows striping | Terrain shadows detach |
| `Entity Shadow Range` | 2.0 | Shadows pop off long vehicles | Shadow rendering costs too much |
| `Shadow Distance` | 160 m | A consist is longer than the range | Frame rate matters more than the far end |
| `Shadow Distortion` | 0.75 | Only the near field matters | Quality must be even across a long scene |
| `Shadow Resolution` | 2048 | Small details are missing from shadows | VRAM or frame time is tight |
| `Shadow Softness` | 1.00 | Shadow edges look digital | Soft shadows are eating detail |

## Debugging

Uncomment `DEBUG_SHADOW_VISIBILITY` in `shaders/lib/settings.glsl` to render the
shadow term on its own, in greyscale. Acne, peter-panning and culling problems
are all far easier to read there than through the finished lighting.
