#version 330 compatibility

/*
    Bloom gather.

    Six levels of colortex0's mip chain, each read with a small tent so the
    steps between them do not show, weighted so the wide levels form the halo
    and the tight ones the core.  No brightness threshold: the whole frame
    contributes in proportion to how bright it already is, which is how real
    glare behaves and why a sunlit train roof blooms while the shadow under it
    does not.
*/

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"

const bool colortex0MipmapEnabled = true;

in vec2 texcoord;

/* RENDERTARGETS: 6 */

vec3 tentSample(float lod) {
    vec2 texel = exp2(lod) / vec2(viewWidth, viewHeight);

    vec3 total = textureLod(colortex0, texcoord, lod).rgb * 4.0;
    total += textureLod(colortex0, texcoord + vec2( texel.x, 0.0), lod).rgb;
    total += textureLod(colortex0, texcoord + vec2(-texel.x, 0.0), lod).rgb;
    total += textureLod(colortex0, texcoord + vec2(0.0,  texel.y), lod).rgb;
    total += textureLod(colortex0, texcoord + vec2(0.0, -texel.y), lod).rgb;

    return total / 8.0;
}

void main() {
#ifndef BLOOM
    gl_FragData[0] = vec4(0.0, 0.0, 0.0, 1.0);
#else
    vec3 bloom = vec3(0.0);
    float weightSum = 0.0;

    for (int level = 1; level <= 6; level++) {
        float weight = 1.0 / float(level);
        bloom += tentSample(float(level)) * weight;
        weightSum += weight;
    }

    gl_FragData[0] = vec4(bloom / weightSum, 1.0);
#endif
}
