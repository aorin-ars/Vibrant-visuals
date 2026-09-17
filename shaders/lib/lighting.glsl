#ifndef LIB_LIGHTING_GLSL
#define LIB_LIGHTING_GLSL

#include "/lib/common.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"
#include "/lib/brdf.glsl"
#include "/lib/material.glsl"
#include "/lib/shadow.glsl"

/*
    One shading routine for the whole pack.

    The deferred pass calls it for opaque geometry and the forward translucent
    programs call it for water and glass, so a pane of stained glass and the
    block behind it are lit by exactly the same sun, sky and shadow term.
*/

/* Planckian locus fit (Neil Bartlett), converted to linear light. */
vec3 blackbody(float kelvin) {
    float t = max(kelvin, 1000.0) / 100.0;
    vec3 c;
    if (t <= 66.0) {
        c.r = 255.0;
        c.g = 99.4708025861 * log(max(t, 1.0)) - 161.1195681661;
        c.b = t <= 19.0 ? 0.0 : 138.5177312231 * log(max(t - 10.0, 1.0)) - 305.0447927307;
    } else {
        c.r = 329.698727446 * pow(t - 60.0, -0.1332047592);
        c.g = 288.1221695283 * pow(t - 60.0, -0.0755148492);
        c.b = 255.0;
    }
    c = saturate(c / 255.0);
    return srgbToLinear(c) / max(luminance(srgbToLinear(c)), 1e-3);
}

float blockLightFalloff(float lm) {
    float x = saturate(lm);
    float s = x * x;
    return s * s * 1.50 + x * 0.08;
}

float skyLightFalloff(float lm) {
    float x = saturate(lm);
    return x * x * (3.0 - 2.0 * x);
}

/*
    Entity geometry gets a looser shadow bias than terrain.

    Entity models are thin, frequently double sided and their parts intersect
    each other, all of which produce shadow acne at a bias that terrain is
    perfectly happy with.  Loosening it only for entities keeps terrain contact
    shadows tight.
*/
float shadowBiasForMaterial(float id) {
    if (id == MAT_ENTITY || id == MAT_VEHICLE || id == MAT_BLOCK_ENTITY || id == MAT_HAND) {
        return ENTITY_SHADOW_BIAS;
    }
    return 1.0;
}

struct ShadingResult {
    vec3 color;
    vec3 shadow;
};

ShadingResult shadeSurface(
        Material m,
        vec3 normal,        /* shading normal, scene space           */
        vec3 geoNormal,     /* geometric normal, scene space         */
        vec3 scenePos,      /* camera-relative world position        */
        vec2 lm,            /* block / sky light levels, 0..1        */
        float ao,           /* screen space ambient occlusion, 0..1  */
        vec2 pixel) {

    vec3 viewDir = normalize(-scenePos);
    vec3 lightDir = shadowLightDir();

    float blockLm = blockLightFalloff(lm.x);
    float skyLm = skyLightFalloff(lm.y);

    float NdotL = dot(normal, lightDir);
    float geoNdotL = dot(geoNormal, lightDir);
    float NdotV = saturate(dot(normal, viewDir));

    /* ------------------------------------------------------------- shadows */

    vec3 shadow = vec3(1.0);
#ifdef USE_SHADOW_SAMPLERS
    shadow = sampleShadow(scenePos, geoNormal, geoNdotL,
                          shadowBiasForMaterial(m.id), pixel);
#else
    shadow = vec3(step(0.0, geoNdotL));
#endif

    /* Lift the floor of the shadow slightly; fully black shadows read as
       holes once the sky ambient is this directional. */
    shadow = mix(vec3(SHADOW_BRIGHTNESS), vec3(1.0), shadow);

    /* Sunlight cannot reach a surface the sky cannot reach either. */
    shadow *= smoothstep(0.0, 0.14, lm.y);
    shadow *= 1.0 - rainStrength * 0.65;

    /* ------------------------------------------------------- direct diffuse */

    float lambert = saturate(NdotL);
#ifdef SUBSURFACE_SCATTERING
    float wrapped = diffuseWrap(NdotL, 0.60);
    float diffuseTerm = mix(lambert, wrapped, m.sss);
#else
    float diffuseTerm = lambert;
#endif

    vec3 directE = directIrradiance();
    vec3 directDiffuse = directE * shadow * diffuseTerm;

    /* ------------------------------------------------------ ambient diffuse */

    vec3 warmLight = blackbody(BLOCKLIGHT_TEMPERATURE);
    float blockLevel = blockLm;

#ifdef HANDHELD_LIGHT
    /* Whatever the player is carrying, falling off with the inverse square. */
    float handLightLevel = float(max(heldBlockLightValue, heldBlockLightValue2)) / 15.0;
    blockLevel += saturate(handLightLevel * 10.0 / (1.0 + dot(scenePos, scenePos)));
#endif

    vec3 skyE = skyIrradiance(normal) * skyLm;
    vec3 blockE = warmLight * blockLevel * BLOCKLIGHT_INTENSITY;

    float ambientOcclusion = mix(1.0, ao, SSAO_STRENGTH);
    vec3 ambientDiffuse = skyE * ambientOcclusion + blockE * mix(0.55, 1.0, ambientOcclusion);

    ambientDiffuse += MINIMUM_LIGHT * vec3(0.85, 0.92, 1.20);
    ambientDiffuse += nightVision * vec3(0.30, 0.34, 0.30);

    /* --------------------------------------------------------- composition */

    float metalness = saturate((m.f0 - 0.30) / 0.70);
    vec3 diffuseAlbedo = m.albedo * (1.0 - metalness);
    vec3 color = diffuseAlbedo * RCP_PI * (directDiffuse + ambientDiffuse);

#ifdef SPECULAR_HIGHLIGHT
    vec3 f0 = materialF0(m);

    vec3 directSpec = specularGGX(normal, viewDir, lightDir, m.roughness, f0);
    color += directSpec * directE * shadow;

    /* Sky reflection through the split-sum approximation - cheap, and enough
       to put moving highlights along a train's flank as it rolls past. */
    vec3 reflDir = reflect(-viewDir, normal);
    vec3 skyReflection = skyRadiance(reflDir) * skyLm * ambientOcclusion;
    color += skyReflection * envBRDFApprox(f0, m.roughness, NdotV);
#endif

    color += m.albedo * m.emission * 4.0;

    /* Blindness and the darkness effect swallow everything else. */
    color *= 1.0 - saturate(blindness + darknessFactor * 0.8);

    ShadingResult result;
    result.color = color;
    result.shadow = shadow;
    return result;
}

#endif
