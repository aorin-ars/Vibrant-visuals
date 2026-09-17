#version 330 compatibility

/*
    Deferred lighting for everything opaque.

    Terrain, block entities, entities and the hand were all written into the
    same g-buffer, so they are lit here by one pass with one shadow lookup -
    which is exactly why a train receives the same sunlight, the same sky term
    and the same soft shadow edge as the platform it is standing beside.

    colortex7 gets a copy of the finished frame; the translucent pass reads it
    for refraction and screen space reflections.
*/

#define USE_SCENE_SAMPLERS
#define USE_SHADOW_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"
#include "/lib/lighting.glsl"
#include "/lib/fog.glsl"

in vec2 texcoord;

/* RENDERTARGETS: 0,7 */

/* Depth-aware blur, so occlusion never bleeds across a silhouette. */
float blurredAmbientOcclusion(vec2 uv, float centerDepth) {
    vec2 texel = 1.0 / vec2(viewWidth, viewHeight);
    float centerLinear = linearizeDepth(centerDepth);

    float total = 0.0;
    float weightSum = 0.0;

    for (int x = -2; x <= 2; x++) {
        for (int y = -2; y <= 2; y++) {
            vec2 offset = vec2(x, y) * texel;
            float sampleDepth = texture(depthtex0, uv + offset).r;
            float difference = abs(linearizeDepth(sampleDepth) - centerLinear);
            float weight = exp(-difference * 2.0) * exp(-float(x * x + y * y) * 0.18);

            total += texture(colortex6, uv + offset).r * weight;
            weightSum += weight;
        }
    }

    return weightSum > 0.0 ? total / weightSum : 1.0;
}

void main() {
    float depth = texture(depthtex0, texcoord).r;
    vec3 color = texture(colortex0, texcoord).rgb;

    /* The sky programs already wrote their own radiance here. */
    if (depth >= 1.0) {
        gl_FragData[0] = vec4(color, 1.0);
        gl_FragData[1] = vec4(color, 1.0);
        return;
    }

    vec4 encodedNormal = texture(colortex1, texcoord);
    vec4 encodedAlbedo = texture(colortex2, texcoord);
    vec4 encodedSurface = texture(colortex3, texcoord);

    Material material;
    material.albedo = encodedAlbedo.rgb;
    material.roughness = encodedSurface.r;
    material.f0 = encodedSurface.g;
    material.emission = encodedSurface.b;
    material.sss = encodedSurface.a;
    material.id = decodeMaterial(encodedAlbedo.a);

    vec3 normal = decodeNormal(encodedNormal.rg);
    vec2 lightLevels = encodedNormal.ba;

    vec3 viewPos = screenToView(vec3(texcoord, depth));
    vec3 scenePos = viewToScenePoint(viewPos);

    float ao = blurredAmbientOcclusion(texcoord, depth);

    ShadingResult shaded = shadeSurface(material, normal, normal, scenePos,
                                        lightLevels, ao, gl_FragCoord.xy);
    color = shaded.color;

#ifdef DEBUG_SHADOW_VISIBILITY
    color = shaded.shadow;
#endif

#ifdef DEBUG_MATERIAL_ID
    color = vec3(fract(material.id * 0.1), fract(material.id * 0.37), fract(material.id * 0.71));
#endif

    color = applyAtmosphericFog(color, scenePos, false);
    if (isEyeInWater != 0) {
        color = applyEyeMediumFog(color, length(scenePos), lightLevels.y);
    }

    gl_FragData[0] = vec4(color, 1.0);
    gl_FragData[1] = vec4(color, 1.0);
}
