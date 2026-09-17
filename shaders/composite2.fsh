#version 330 compatibility

/*
    Auto exposure.

    The whole-frame average comes free from the top of colortex0's mip chain.
    colortex4 is never cleared, so the value written here is the value read back
    next frame, which is what makes the adaptation gradual instead of jumping
    every time the camera turns towards the sun.
*/

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"

const bool colortex0MipmapEnabled = true;

in vec2 texcoord;

/* RENDERTARGETS: 4 */

void main() {
#ifndef AUTO_EXPOSURE
    gl_FragData[0] = vec4(1.0, 0.0, 0.0, 1.0);
#else
    /* Geometric mean: bright highlights pull the average far less than they
       would in a linear average, so a single lamp cannot darken a whole room. */
    vec3 average = textureLod(colortex0, vec2(0.5), 10.0).rgb;
    float logAverage = log2(max(luminance(average), 1e-5));
    float target = 0.16 / max(exp2(logAverage), 1e-4);
    target = clamp(target, 0.04, 24.0);

    float previous = texture(colortex4, vec2(0.5)).r;
    if (!(previous > 0.0)) previous = target;

    /* Eyes darken faster than they brighten. */
    float speed = EXPOSURE_SPEED * (target < previous ? 2.2 : 1.1);
    float rate = 1.0 - exp2(-max(frameTime, 1e-3) * speed * 1.4426950);

    gl_FragData[0] = vec4(mix(previous, target, saturate(rate)), 0.0, 0.0, 1.0);
#endif
}
