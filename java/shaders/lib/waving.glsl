#ifndef LIB_WAVING_GLSL
#define LIB_WAVING_GLSL

#include "/lib/common.glsl"

/*
    Vertex animation for foliage.

    Deliberately keeps entities out of it: a train, a boat or a mob must keep
    the exact vertex positions the game gave it, otherwise the gbuffer pass and
    the shadow pass would disagree and the shadow would detach from the model.
*/

vec3 windOffset(vec3 worldPos, float amplitude) {
    float wind = mix(1.0, 2.20, rainStrength) * WAVING_STRENGTH;
    float t = frameTimeCounter * 1.40 * mix(1.0, 1.6, rainStrength);

    float a = sin(t * 1.10 + worldPos.x * 0.45 + worldPos.z * 0.33);
    float b = sin(t * 1.73 + worldPos.x * 0.27 - worldPos.z * 0.61 + 1.70);
    float c = cos(t * 0.87 + worldPos.y * 0.40 + worldPos.z * 0.22);

    return vec3(a + b * 0.55, c * 0.26, b + a * 0.42) * amplitude * wind * 0.055;
}

/*
    `isTopVertex` comes from comparing the vertex UV with the sprite centre, so
    a plant bends from its base instead of sliding off its block.
*/
vec3 wavingDisplacement(int blockId, vec3 worldPos, bool isTopVertex, float skyLight) {
    vec3 offset = vec3(0.0);
    float exposure = smoothstep(0.0, 0.35, skyLight);

#ifdef WAVING_PLANTS
    if (blockId == BLOCK_PLANT_SMALL && isTopVertex) {
        offset = windOffset(worldPos, 1.00);
    } else if (blockId == BLOCK_PLANT_TALL) {
        offset = windOffset(worldPos, isTopVertex ? 1.35 : 0.30);
    } else if (blockId == BLOCK_CROP && isTopVertex) {
        offset = windOffset(worldPos, 0.65);
    }
#endif

#ifdef WAVING_LEAVES
    if (blockId == BLOCK_LEAVES) {
        offset = windOffset(worldPos, 0.75);
    }
#endif

    return offset * exposure;
}

/* Gerstner-ish surface displacement for water, matched by the normal below. */
float waterHeight(vec2 worldXZ) {
    float t = frameTimeCounter * 0.85;
    float h = 0.0;
    h += sin(dot(worldXZ, vec2( 0.42,  0.29)) + t * 1.10) * 0.55;
    h += sin(dot(worldXZ, vec2(-0.31,  0.55)) + t * 1.43) * 0.38;
    h += sin(dot(worldXZ, vec2( 0.77, -0.23)) + t * 0.87) * 0.22;
    h += sin(dot(worldXZ, vec2( 1.31,  0.91)) + t * 2.10) * 0.09;
    return h * 0.045 * WATER_WAVE_HEIGHT;
}

/*
    Applied identically in gbuffers_water and in the shadow pass, so the surface
    and the shadow it casts stay in step.
*/
vec3 waterDisplacement(int blockId, vec3 worldPos, vec3 normal) {
#ifdef WATER_WAVES
    if (blockId == BLOCK_WATER && normal.y > 0.5) {
        return vec3(0.0, waterHeight(worldPos.xz), 0.0);
    }
#endif
    return vec3(0.0);
}

vec3 waterNormal(vec2 worldXZ) {
    const float eps = 0.08;
    float h  = waterHeight(worldXZ);
    float hx = waterHeight(worldXZ + vec2(eps, 0.0));
    float hz = waterHeight(worldXZ + vec2(0.0, eps));
    return normalize(vec3(h - hx, eps, h - hz));
}

#endif
