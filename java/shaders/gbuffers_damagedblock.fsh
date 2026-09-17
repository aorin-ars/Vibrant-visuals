#version 330 compatibility

/*
    Block breaking overlay.

    Only the albedo channel is touched, and the blend function in
    shaders.properties keeps the destination alpha, so the material id stored
    alongside it survives and the block keeps being lit as itself.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"

in vec2 texcoord;
in vec4 glcolor;

/* RENDERTARGETS: 2 */

void main() {
    vec4 crack = texture(gtexture, texcoord) * glcolor;
    if (crack.a < 0.01) discard;

    gl_FragData[0] = vec4(srgbToLinear(crack.rgb) * 0.45, crack.a);
}
