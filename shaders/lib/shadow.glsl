#ifndef LIB_SHADOW_GLSL
#define LIB_SHADOW_GLSL

#include "/lib/common.glsl"
#include "/lib/space.glsl"
#include "/lib/noise.glsl"

/*
    Shape-accurate shadows from a single distorted shadow map.

    Terrain, block entities and entities all render into the same map, so a
    train, a boat or a mob occludes the sun with its real silhouette instead of
    the flat oval Minecraft draws underneath it.  Everything below is written so
    the entity case works as well as the terrain case:

      * offsets are applied before the distortion, which keeps the filter
        kernel circular in world units no matter where the caster sits,
      * the bias is derived from the world size of a shadow texel at the
        caster's position, so a model 120 blocks away is biased more than one
        at the player's feet - no acne far away, no detached shadow up close,
      * callers hand in a bias multiplier, which lets entity geometry (thin,
        double sided, often self-intersecting) use a looser bias than terrain
        without softening terrain contact shadows,
      * the penumbra grows with the distance to the blocker, so a train's
        shadow is crisp under the bogies and soft under the roof overhang.
*/

/* z is squashed so geometry far outside the ortho depth box still casts. */
#define SHADOW_DEPTH_SCALE 0.2

/* How much wider than the real solar disc the penumbra is allowed to grow. */
#define SHADOW_PENUMBRA_SCALE 6.0

#if SHADOW_FILTER == 0
    #define SHADOW_BLOCKER_SAMPLES 1
    #define SHADOW_FILTER_SAMPLES 1
#elif SHADOW_FILTER == 1
    #define SHADOW_BLOCKER_SAMPLES 1
    #define SHADOW_FILTER_SAMPLES 8
#elif SHADOW_FILTER == 2
    #define SHADOW_BLOCKER_SAMPLES 8
    #define SHADOW_FILTER_SAMPLES 14
#else
    #define SHADOW_BLOCKER_SAMPLES 16
    #define SHADOW_FILTER_SAMPLES 28
#endif

float shadowDistortFactor(vec2 clipXY) {
    return max(length(clipXY) * SHADOW_DISTORTION + (1.0 - SHADOW_DISTORTION), 0.05);
}

vec3 distortShadowClip(vec3 clipPos) {
    clipPos.xy /= shadowDistortFactor(clipPos.xy);
    clipPos.z  *= SHADOW_DEPTH_SCALE;
    return clipPos;
}

/* Camera-relative world position -> undistorted shadow clip space. */
vec3 sceneToShadowClip(vec3 scenePos) {
    vec3 shadowView = (shadowModelView * vec4(scenePos, 1.0)).xyz;
    return projectOrtho(shadowProjection, shadowView);
}

/*
    World size of one shadow texel at a given clip position.

    The distortion divides xy by f = |xy| * k + (1 - k), so the local stretch is
    f^2 / (1 - k) - texels shrink near the player and grow towards the edge of
    the map.  Every bias in this file is a multiple of this number, which is why
    the same settings hold from the player's feet out to the shadow distance.
*/
float shadowTexelWorldSize(vec2 clipXY) {
    float f = shadowDistortFactor(clipXY);
    float uniformTexel = 2.0 * shadowDistance / float(shadowMapResolution);
    return uniformTexel * f * f / max(1.0 - SHADOW_DISTORTION, 0.05);
}

/* Depth-buffer units -> world units along the light axis. */
float shadowDepthToWorld() {
    return 2.0 / max(SHADOW_DEPTH_SCALE * abs(shadowProjection[2][2]), 1e-6);
}

/*
    Normal-offset bias.

    Moving the sample along the surface normal rather than along the light keeps
    contact shadows attached: a bogie sitting on the rails still darkens the
    sleeper directly under it, which a plain depth bias would push away.
*/
vec3 applyShadowBias(vec3 scenePos, vec3 normal, float NdotL, float biasMultiplier) {
    vec3 clip = sceneToShadowClip(scenePos);
    float texel = shadowTexelWorldSize(clip.xy);
    float grazing = saturate(1.0 - NdotL * NdotL);
    float offset = texel * (0.85 + 2.6 * grazing) * SHADOW_BIAS_SCALE * biasMultiplier;
    return scenePos + normal * offset;
}

#ifdef USE_SHADOW_SAMPLERS

/*
    One filtered tap.

    shadowtex1 holds opaque casters only and shadowtex0 holds everything, so a
    texel that is lit in tex1 but occluded in tex0 was shaded by something
    translucent - stained glass, ice, a train's tinted side window - and the
    light that arrives keeps the colour stored in shadowcolor0.
*/
vec3 shadowTap(vec2 uv, float depth) {
    float opaque = step(depth, texture(shadowtex1, uv).r);
#ifdef COLORED_SHADOWS
    float anything = step(depth, texture(shadowtex0, uv).r);
    vec3 tint = texture(shadowcolor0, uv).rgb;
    return vec3(opaque) * mix(tint, vec3(1.0), anything);
#else
    return vec3(opaque);
#endif
}

/* Average depth of the casters above this point, in depth-buffer units. */
float findBlockerDepth(vec3 clipPos, float searchRadius, float rotation, float depth) {
    float sum = 0.0;
    float hits = 0.0;

    for (int i = 0; i < SHADOW_BLOCKER_SAMPLES; i++) {
        vec2 offset = vogelDisk(i, SHADOW_BLOCKER_SAMPLES, rotation) * searchRadius;
        vec2 uv = distortShadowClip(vec3(clipPos.xy + offset, clipPos.z)).xy * 0.5 + 0.5;
        if (saturate(uv) != uv) continue;

        float caster = texture(shadowtex1, uv).r;
        if (caster < depth) {
            sum += caster;
            hits += 1.0;
        }
    }

    return hits > 0.0 ? sum / hits : -1.0;
}

/*
    Main entry point.

      scenePos       camera-relative world position of the receiver
      normal         geometric normal, world aligned
      NdotL          cosine between that normal and the shadow light
      biasMultiplier 1.0 for terrain, larger for entity geometry
      pixel          gl_FragCoord.xy, used to rotate the sampling disk
*/
vec3 sampleShadow(vec3 scenePos, vec3 normal, float NdotL, float biasMultiplier, vec2 pixel) {
    if (NdotL <= 0.0) return vec3(0.0);

    vec3 biased = applyShadowBias(scenePos, normal, NdotL, biasMultiplier);
    vec3 clipPos = sceneToShadowClip(biased);

    /* Outside the map there is nothing to occlude with, so call it lit. */
    float edge = maxOf(abs(clipPos.xy));
    if (edge >= 1.0 || abs(clipPos.z) >= 1.0 / SHADOW_DEPTH_SCALE) return vec3(1.0);

    float depth = distortShadowClip(clipPos).z * 0.5 + 0.5;

    float texelWorld = shadowTexelWorldSize(clipPos.xy);
    float depthToWorld = shadowDepthToWorld();
    depth -= (texelWorld * 0.30 + 0.015) / depthToWorld;

    float rotation = sampleRotation(pixel);

#if SHADOW_FILTER == 0
    vec2 uv = distortShadowClip(clipPos).xy * 0.5 + 0.5;
    vec3 visibility = shadowTap(uv, depth);
#else
    float penumbraWorld;

    #if SHADOW_BLOCKER_SAMPLES > 1
        float searchWorld = clamp(1.6 * SHADOW_SOFTNESS, 0.4, 4.0);
        float blocker = findBlockerDepth(clipPos, searchWorld / shadowDistance, rotation, depth);
        if (blocker < 0.0) return vec3(1.0);   /* nothing above this point at all */

        float blockerDistance = max(depth - blocker, 0.0) * depthToWorld;
        penumbraWorld = blockerDistance * SUN_ANGULAR_TAN * SHADOW_PENUMBRA_SCALE * SHADOW_SOFTNESS;
    #else
        penumbraWorld = texelWorld * SHADOW_SOFTNESS;
    #endif

    penumbraWorld = clamp(penumbraWorld, texelWorld * 0.70, 2.5 * SHADOW_SOFTNESS);
    float filterRadius = penumbraWorld / shadowDistance;

    vec3 visibility = vec3(0.0);
    for (int i = 0; i < SHADOW_FILTER_SAMPLES; i++) {
        vec2 offset = vogelDisk(i, SHADOW_FILTER_SAMPLES, rotation) * filterRadius;
        vec2 uv = distortShadowClip(vec3(clipPos.xy + offset, clipPos.z)).xy * 0.5 + 0.5;
        visibility += shadowTap(saturate(uv), depth);
    }
    visibility /= float(SHADOW_FILTER_SAMPLES);
#endif

    /* Dissolve into "lit" rather than popping at the edge of the map. */
    float fade = smoothstep(0.86, 1.0, edge);
    return mix(visibility, vec3(1.0), fade);
}

#endif /* USE_SHADOW_SAMPLERS */

#endif
