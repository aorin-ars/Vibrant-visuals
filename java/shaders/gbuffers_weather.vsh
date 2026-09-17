#version 330 compatibility

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"

out vec2 texcoord;
out vec2 lmcoord;
out vec4 glcolor;

void main() {
    gl_Position = jitterClipPos(ftransform());
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;

    vec2 rawLm = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
    lmcoord = saturate((rawLm - 0.03125) * (1.0 / 0.9375));

    glcolor = gl_Color;
}
