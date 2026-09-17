#version 330 compatibility

/*
    Translucent geometry - water, stained glass, ice, slime.

    Drawn after the deferred pass, so this program shades its own fragments and
    reads the finished opaque frame out of colortex7 for reflection and
    refraction.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/material.glsl"
#include "/lib/waving.glsl"

in vec3 mc_Entity;
in vec2 mc_midTexCoord;

out vec2 texcoord;
out vec2 lmcoord;
out vec4 glcolor;
out vec3 vNormal;
out vec3 vScenePos;
flat out float vMatID;

void main() {
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;

    vec2 rawLm = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
    lmcoord = saturate((rawLm - 0.03125) * (1.0 / 0.9375));

    glcolor = gl_Color;

    vec3 viewPos = (gl_ModelViewMatrix * gl_Vertex).xyz;
    vec3 scenePos = viewToScenePoint(viewPos);

    vec3 viewNormal = normalize(gl_NormalMatrix * gl_Normal);
    vNormal = viewToScene(viewNormal);

    int blockId = int(mc_Entity.x + 0.5);
    vMatID = materialFromBlockId(blockId);

    vec3 displacement = waterDisplacement(blockId, scenePos + cameraPosition, vNormal);
    displacement += wavingDisplacement(blockId, scenePos + cameraPosition,
                                       texcoord.y < mc_midTexCoord.y, lmcoord.y);
    scenePos += displacement;
    vScenePos = scenePos;

    gl_Position = jitterClipPos(gl_ProjectionMatrix * vec4(sceneToViewPoint(scenePos), 1.0));
}
