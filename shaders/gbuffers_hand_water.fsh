#version 330 compatibility

/* Translucent held items, shaded forward like the rest of the translucent pass. */

#define USE_GBUFFER_SAMPLERS
#define USE_AUX_SAMPLERS
#define USE_SHADOW_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"
#include "/lib/lighting.glsl"
#include "/lib/fog.glsl"

in vec2 texcoord;
in vec2 lmcoord;
in vec4 glcolor;
in vec3 vNormal;
in vec3 vScenePos;
flat in float vMatID;

/* RENDERTARGETS: 0 */

void main() {
    vec4 color = texture(gtexture, texcoord) * glcolor;
    if (color.a < 0.004) discard;

    vec3 normal = normalize(vNormal);
    Material material = defaultMaterial(srgbToLinear(color.rgb), MAT_HAND);

    ShadingResult shaded = shadeSurface(material, normal, normal, vScenePos,
                                        lmcoord, 1.0, gl_FragCoord.xy);

    gl_FragData[0] = vec4(shaded.color, color.a);
}
