#version 330 compatibility

/* One gaussian pass over the gathered bloom, to take the last of the mip
   structure out of the halo before it is mixed back in. */

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"

in vec2 texcoord;

/* RENDERTARGETS: 7 */

void main() {
#ifndef BLOOM
    gl_FragData[0] = vec4(0.0, 0.0, 0.0, 1.0);
#else
    vec2 texel = 2.0 / vec2(viewWidth, viewHeight);

    const float kernel[3] = float[3](0.25, 0.125, 0.0625);

    vec3 blurred = vec3(0.0);
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            float weight = kernel[abs(x) + abs(y)];
            blurred += texture(colortex6, texcoord + vec2(x, y) * texel).rgb * weight;
        }
    }

    gl_FragData[0] = vec4(blurred, 1.0);
#endif
}
