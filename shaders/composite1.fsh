#version 330 compatibility

/*
    Temporal anti-aliasing.

    The history is clipped to the colour statistics of the current pixel's
    neighbourhood, which is what lets a train travel across the frame without
    dragging a smear behind it while still resolving the jittered soft shadows
    and the dithered cloud edges into something smooth.
*/

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"
#include "/lib/space.glsl"

in vec2 texcoord;

/* RENDERTARGETS: 0,5 */

#ifdef TAA
/* RGB <-> YCoCg keeps the clip box aligned with luminance, where the eye is
   most sensitive, instead of with the raw channels. */
vec3 rgbToYCoCg(vec3 c) {
    return vec3(0.25 * c.r + 0.5 * c.g + 0.25 * c.b,
                0.50 * c.r - 0.5 * c.b,
               -0.25 * c.r + 0.5 * c.g - 0.25 * c.b);
}

vec3 ycoCgToRgb(vec3 c) {
    float t = c.x - c.z;
    return vec3(t + c.y, c.x + c.z, t - c.y);
}

vec3 clipToNeighbourhood(vec3 history, vec3 minimum, vec3 maximum) {
    vec3 centre = 0.5 * (maximum + minimum);
    vec3 extent = 0.5 * (maximum - minimum) + 1e-5;
    vec3 offset = history - centre;
    vec3 units = abs(offset / extent);
    float longest = maxOf(units);
    return longest > 1.0 ? centre + offset / longest : history;
}
#endif

void main() {
    vec3 current = texture(colortex0, texcoord).rgb;

#ifndef TAA
    gl_FragData[0] = vec4(current, 1.0);
    gl_FragData[1] = vec4(current, 1.0);
#else
    vec2 texel = 1.0 / vec2(viewWidth, viewHeight);

    /* The g-buffer was rendered with a sub-pixel offset; undo it before the
       position is reprojected, or the history lands half a pixel out. */
    vec2 unjittered = texcoord - taaJitter() * 0.5;
    float depth = texture(depthtex0, texcoord).r;

    vec3 previous = reprojectScreenPos(vec3(unjittered, depth));
    vec2 historyUv = previous.xy;

    vec3 mean = vec3(0.0);
    vec3 meanSquare = vec3(0.0);
    vec3 minimum = vec3( 1e9);
    vec3 maximum = vec3(-1e9);

    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            vec3 neighbour = rgbToYCoCg(texture(colortex0, texcoord + vec2(x, y) * texel).rgb);
            mean += neighbour;
            meanSquare += neighbour * neighbour;
            minimum = min(minimum, neighbour);
            maximum = max(maximum, neighbour);
        }
    }

    mean /= 9.0;
    vec3 sigma = sqrt(max(meanSquare / 9.0 - mean * mean, vec3(0.0)));
    minimum = max(minimum, mean - sigma * 1.35);
    maximum = min(maximum, mean + sigma * 1.35);

    vec3 history = rgbToYCoCg(texture(colortex5, historyUv).rgb);
    history = clipToNeighbourhood(history, minimum, maximum);

    float blend = 0.93;
    if (saturate(historyUv) != historyUv) blend = 0.0;
    /* A large reprojection offset means the pixel is barely related to its
       history, so lean on the current frame. */
    blend *= exp(-length((historyUv - texcoord) / texel) * 0.02);

    vec3 resolved = ycoCgToRgb(mix(rgbToYCoCg(current), history, blend));
    resolved = max(resolved, vec3(0.0));

    gl_FragData[0] = vec4(resolved, 1.0);
    gl_FragData[1] = vec4(resolved, 1.0);
#endif
}
