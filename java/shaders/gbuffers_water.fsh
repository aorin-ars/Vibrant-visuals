#version 330 compatibility

/*
    Forward shading for translucent surfaces.

    Reflection and refraction both read colortex7, the copy of the opaque frame
    the deferred pass leaves behind, so nothing here samples a buffer it is also
    writing to.
*/

#define USE_GBUFFER_SAMPLERS
#define USE_AUX_SAMPLERS
#define USE_SHADOW_SAMPLERS

/* Reflections are traced below; skip the analytic one in shadeSurface. */
#define LIGHTING_NO_AMBIENT_SPECULAR

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/noise.glsl"
#include "/lib/sky.glsl"
#include "/lib/lighting.glsl"
#include "/lib/fog.glsl"
#include "/lib/waving.glsl"

in vec2 texcoord;
in vec2 lmcoord;
in vec4 glcolor;
in vec3 vNormal;
in vec3 vScenePos;
flat in float vMatID;

/* RENDERTARGETS: 0 */

/*
    Screen space reflection against the opaque depth buffer.  Returns false when
    the ray leaves the screen or runs out of steps, and the caller falls back to
    the analytic sky - which is also what keeps reflections sane when the thing
    being reflected is off-camera.
*/
#ifdef SSR
bool traceReflection(vec3 viewPos, vec3 viewDir, float dither, out vec2 hitUv) {
    hitUv = vec2(0.0);

    vec3 rayStart = viewPos + viewDir * 0.10;
    vec3 rayEnd = viewPos + viewDir * 64.0;

    vec3 startScreen = viewToScreen(rayStart);
    vec3 endScreen = viewToScreen(rayEnd);
    vec3 step = (endScreen - startScreen) / float(SSR_STEPS);

    vec3 position = startScreen + step * (0.5 + dither);

    for (int i = 0; i < SSR_STEPS; i++) {
        if (saturate(position.xy) != position.xy || position.z > 1.0) return false;

        float sceneDepth = texture(depthtex1, position.xy).r;
        if (sceneDepth < position.z && sceneDepth > 0.0) {
            /* Reject hits that are really just the far side of a thin object. */
            float thickness = linearizeDepth(position.z) - linearizeDepth(sceneDepth);
            if (thickness > 4.0) return false;

            /* Binary refinement so the hit lands on the surface, not past it. */
            vec3 refined = position;
            vec3 halfStep = step;
            for (int j = 0; j < SSR_REFINE; j++) {
                halfStep *= 0.5;
                refined += texture(depthtex1, refined.xy).r < refined.z ? -halfStep : halfStep;
            }

            hitUv = refined.xy;
            return true;
        }
        position += step;
    }
    return false;
}
#endif

void main() {
    vec4 color = texture(gtexture, texcoord) * glcolor;
    if (color.a < 0.004) discard;

    bool isWater = vMatID == MAT_WATER;

    vec3 geoNormal = normalize(vNormal);
    vec3 normal = geoNormal;

#ifdef WATER_WAVES
    if (isWater && geoNormal.y > 0.5) {
        vec3 wave = waterNormal((vScenePos + cameraPosition).xz);
        normal = normalize(vec3(wave.x, wave.y, wave.z));
    }
#endif

    vec3 albedo = srgbToLinear(color.rgb);

    Material material = defaultMaterial(isWater ? vec3(0.0) : albedo, vMatID);

    vec2 pixel = gl_FragCoord.xy;
    ShadingResult shaded = shadeSurface(material, normal, geoNormal, vScenePos,
                                        lmcoord, 1.0, pixel);
    vec3 surface = shaded.color;

    /* ------------------------------------------------------------ refraction */

    vec2 screenUv = gl_FragCoord.xy / vec2(viewWidth, viewHeight);
    vec2 refractedUv = screenUv;

#ifdef REFRACTION
    vec2 offset = (normal.xz - geoNormal.xz) * 0.22;
    offset.y *= aspectRatio;
    vec2 candidate = saturate(screenUv + offset);
    /* Only bend light that is actually behind the surface. */
    if (texture(depthtex1, candidate).r > gl_FragCoord.z) refractedUv = candidate;
#endif

    vec3 behind = texture(colortex7, refractedUv).rgb;

    /* --------------------------------------------------------- transmission */

    float opaqueDepth = texture(depthtex1, refractedUv).r;
    float throughDistance = max(linearizeDepth(opaqueDepth) - linearizeDepth(gl_FragCoord.z), 0.0);

    if (isWater) {
        behind = applyWaterFog(behind, throughDistance, lmcoord.y);
        /* The biome's own water colour, on top of the depth absorption. */
        behind = mix(behind, behind * albedo, WATER_ALPHA);
    } else {
        behind *= mix(vec3(1.0), albedo, color.a);
        surface *= color.a;
    }

    /* ---------------------------------------------------------- reflection */

    vec3 viewDir = normalize(-vScenePos);
    float NdotV = saturate(dot(normal, viewDir));
    vec3 f0 = materialF0(material);
    float fresnel = saturate(fresnelSchlick(NdotV, f0).r);

    vec3 reflectDir = reflect(-viewDir, normal);
    vec3 reflection = skyRadiance(reflectDir) * mix(0.05, 1.0, lmcoord.y);

#if defined(WATER_REFLECTIONS) && defined(SSR)
    if (reflectDir.y > -0.05) {
        vec3 viewPos = sceneToViewPoint(vScenePos);
        vec3 viewReflect = sceneToView(reflectDir);
        vec2 hitUv;
        float dither = bayer16(gl_FragCoord.xy);
        if (traceReflection(viewPos, viewReflect, dither, hitUv)) {
            /* Fade towards the sky as the hit approaches the screen border. */
            vec2 border = smoothstep(vec2(0.0), vec2(0.12), hitUv)
                        * smoothstep(vec2(0.0), vec2(0.12), 1.0 - hitUv);
            reflection = mix(reflection, texture(colortex7, hitUv).rgb, border.x * border.y);
        }
    }
#endif

#ifndef WATER_REFLECTIONS
    if (isWater) fresnel *= 0.25;
#endif

    /*
        `surface` is the direct specular lobe, which already carries its own
        Fresnel term from the BRDF - on near-mirror water it is the sun's
        reflection, so attenuating it by Fresnel a second time would dim the
        glint exactly where it should be brightest.
    */
    vec3 result = mix(behind, reflection, fresnel) + surface;

    /* --------------------------------------------------------------- fog */

    result = applyAtmosphericFog(result, vScenePos, false);
    if (isEyeInWater != 0) {
        result = applyEyeMediumFog(result, length(vScenePos), lmcoord.y);
    }

    /*
        Written opaque: `behind` already carries everything this surface sits in
        front of, so the fragment is a finished composite rather than a layer to
        be blended.  The trade-off is that two translucent surfaces stacked in
        front of each other do not accumulate.
    */
    gl_FragData[0] = vec4(result, 1.0);
}
