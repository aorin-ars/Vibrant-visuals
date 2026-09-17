#version 330 compatibility

/*
    The shadow pass.

    Terrain, block entities and entities all pass through here, which is what
    gives every one of them a shadow shaped like the model rather than the flat
    oval the game draws underneath entities by default.  Nothing in this file
    treats entities as a special case on purpose: `gl_ModelViewMatrix` already
    carries the entity's own transform, so a 20-block train car is projected
    with exactly the same maths as a block of stone.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/shadow.glsl"
#include "/lib/waving.glsl"

in vec3 mc_Entity;
in vec2 mc_midTexCoord;

out vec2 texcoord;
out vec4 glcolor;

void main() {
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    glcolor = gl_Color;

    vec3 shadowViewPos = (gl_ModelViewMatrix * gl_Vertex).xyz;

#ifdef WAVING_PLANTS
    /*
        Foliage has to be displaced by exactly the same amount here as it is in
        gbuffers_terrain; if the two disagree, every blade of grass casts its
        shadow slightly beside itself.  mc_Entity is zero for anything that is
        not terrain, so entities never enter this branch.
    */
    int blockId = int(mc_Entity.x + 0.5);
    if (blockId > 0) {
        vec3 scenePos = (shadowModelViewInverse * vec4(shadowViewPos, 1.0)).xyz;
        vec2 rawLm = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
        float skyLight = saturate((rawLm.y - 0.03125) * (1.0 / 0.9375));
        bool isTopVertex = texcoord.y < mc_midTexCoord.y;

        scenePos += wavingDisplacement(blockId, scenePos + cameraPosition,
                                       isTopVertex, skyLight);
        shadowViewPos = (shadowModelView * vec4(scenePos, 1.0)).xyz;
    }
#endif

    vec3 clipPos = projectOrtho(shadowProjection, shadowViewPos);
    gl_Position = vec4(distortShadowClip(clipPos), 1.0);
}
