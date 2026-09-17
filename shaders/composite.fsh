#version 330 compatibility

/*
    Volumetric light.

    The same shadow map the surface shading uses is marched through the air, so
    the shafts line up with the shadows on the ground - including the ones cast
    by entities, which is what puts light bars between the cars of a train or
    through the columns of a station roof.
*/

#define USE_SCENE_SAMPLERS
#define USE_SHADOW_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"
#include "/lib/space.glsl"
#include "/lib/noise.glsl"
#include "/lib/sky.glsl"
#include "/lib/shadow.glsl"

in vec2 texcoord;

/* RENDERTARGETS: 0 */

#ifdef VOLUMETRIC_LIGHT
vec3 marchVolumetricLight(vec3 scenePos, float dither) {
    float maxDistance = min(length(scenePos), shadowDistance * 0.85);
    if (maxDistance < 0.5) return vec3(0.0);

    vec3 rayDir = normalize(scenePos);
    float stepSize = maxDistance / float(VOLUMETRIC_STEPS);

    /* Mostly forward scattering, with a floor so shafts stay visible off-axis. */
    float cosTheta = dot(rayDir, shadowLightDir());
    float phase = mix(0.25 * RCP_PI, miePhase(cosTheta, 0.60), 0.72);

    vec3 accumulated = vec3(0.0);

    for (int i = 0; i < VOLUMETRIC_STEPS; i++) {
        vec3 samplePos = rayDir * ((float(i) + dither) * stepSize);

        vec3 clipPos = sceneToShadowClip(samplePos);
        if (maxOf(abs(clipPos.xy)) >= 1.0) continue;

        vec3 shadowPos = distortShadowClip(clipPos) * 0.5 + 0.5;
        float reference = shadowPos.z - 0.0006;

        vec3 light = vec3(step(reference, texture(shadowtex1, shadowPos.xy).r));
#ifdef COLORED_SHADOWS
        float unblocked = step(reference, texture(shadowtex0, shadowPos.xy).r);
        light *= mix(texture(shadowcolor0, shadowPos.xy).rgb, vec3(1.0), unblocked);
#endif

        /* Haze thins out with altitude and thickens in the rain. */
        float height = samplePos.y + cameraPosition.y;
        float density = exp(-max(height - 62.0, 0.0) * 0.012);
        accumulated += light * density;
    }

    return accumulated * stepSize * phase * directIrradiance()
         * VOLUMETRIC_STRENGTH * mix(0.018, 0.048, rainStrength);
}
#endif

void main() {
    vec3 color = texture(colortex0, texcoord).rgb;

#ifdef VOLUMETRIC_LIGHT
    float depth = texture(depthtex0, texcoord).r;
    vec3 viewPos = screenToView(vec3(texcoord, min(depth, 0.9999)));
    vec3 scenePos = viewToScenePoint(viewPos);

    float dither = bayer16(gl_FragCoord.xy);
#ifdef TAA
    dither = fract(dither + float(frameCounter % 16) * 0.0625);
#endif

    vec3 shafts = marchVolumetricLight(scenePos, dither);
    color += shafts * (isEyeInWater == 1 ? 0.35 : 1.0);
#endif

    gl_FragData[0] = vec4(color, 1.0);
}
