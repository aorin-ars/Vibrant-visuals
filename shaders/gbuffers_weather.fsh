#version 330 compatibility

/* Rain and snow, lit by the sky rather than by the flat vanilla tint. */

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"

in vec2 texcoord;
in vec2 lmcoord;
in vec4 glcolor;

/* RENDERTARGETS: 0 */

void main() {
    vec4 tex = texture(gtexture, texcoord) * glcolor;
    if (tex.a < 0.01) discard;

    vec3 color = srgbToLinear(tex.rgb) * skyAverage() * mix(0.15, 1.0, lmcoord.y);
    gl_FragData[0] = vec4(color, tex.a * 0.55);
}
