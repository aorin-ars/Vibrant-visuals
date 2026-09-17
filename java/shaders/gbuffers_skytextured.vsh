#version 330 compatibility

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"

out vec2 texcoord;
out vec3 vScenePos;
out vec4 glcolor;

void main() {
    gl_Position = jitterClipPos(ftransform());
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    vScenePos = viewToScenePoint((gl_ModelViewMatrix * gl_Vertex).xyz);
    glcolor = gl_Color;
}
