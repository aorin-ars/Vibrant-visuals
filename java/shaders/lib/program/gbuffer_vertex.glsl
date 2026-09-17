#ifndef PROGRAM_GBUFFER_VERTEX_GLSL
#define PROGRAM_GBUFFER_VERTEX_GLSL

/*
    Shared vertex stage for every gbuffers program.

    Each program sets a handful of GB_* macros and includes this file; that way
    terrain, entities, block entities and the hand all end up in the same world
    space with the same temporal jitter, which is what lets one deferred pass
    light them identically.

        GB_TERRAIN      block ids, waving foliage, mid-texture coordinates
        GB_ENTITY       entity tint and entity-derived material ids
        GB_NO_LIGHTMAP  program has no lightmap attribute
        GB_NORMAL_MAP   sample the tangent-space normal map if one exists
        GB_MATERIAL     material id to fall back on
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/material.glsl"
#include "/lib/waving.glsl"

#ifndef GB_MATERIAL
    #define GB_MATERIAL MAT_DEFAULT
#endif

out vec2 texcoord;
out vec2 lmcoord;
out vec4 glcolor;
out vec3 vNormal;
out vec3 vScenePos;
/* flat: the material id is an exact integer that gets compared with ==,
   and interpolation would hand the fragment stage 4.9999999 instead of 5. */
flat out float vMatID;

#ifdef GB_TERRAIN
in vec3 mc_Entity;
in vec2 mc_midTexCoord;
#endif

#if defined(GB_NORMAL_MAP) && defined(MC_NORMAL_MAP)
in vec4 at_tangent;
out vec3 vTangent;
out vec3 vBitangent;
#endif

void main() {
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;

#ifdef GB_NO_LIGHTMAP
    lmcoord = vec2(0.0, 1.0);
#else
    vec2 rawLm = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
    lmcoord = saturate((rawLm - 0.03125) * (1.0 / 0.9375));
#endif

    glcolor = gl_Color;

    vec3 viewPos = (gl_ModelViewMatrix * gl_Vertex).xyz;
    vec3 scenePos = viewToScenePoint(viewPos);

    vec3 viewNormal = normalize(gl_NormalMatrix * gl_Normal);
    vNormal = viewToScene(viewNormal);

    float materialId = GB_MATERIAL;

#ifdef GB_TERRAIN
    int blockId = int(mc_Entity.x + 0.5);
    materialId = materialFromBlockId(blockId);

    /* A vertex above the sprite centre is the part of the plant that moves. */
    bool isTopVertex = texcoord.y < mc_midTexCoord.y;
    vec3 displacement = wavingDisplacement(blockId, scenePos + cameraPosition,
                                           isTopVertex, lmcoord.y);
    scenePos += displacement;
    viewPos = sceneToViewPoint(scenePos);
#endif

#ifdef GB_ENTITY
    /*
        Vehicles get their own material so painted bodywork reads as lacquer
        rather than as rock.  See shaders/entity.properties for how to add the
        entities of a train, ship or aircraft mod to this group.
    */
    if (entityId == ENTITY_VEHICLE || entityId == ENTITY_RAIL_CAR) {
        materialId = MAT_VEHICLE;
    } else if (entityId == ENTITY_FLAME || entityId == ENTITY_LIGHTNING) {
        materialId = MAT_EMISSIVE;
    }
#endif

    vMatID = materialId;
    vScenePos = scenePos;

#if defined(GB_NORMAL_MAP) && defined(MC_NORMAL_MAP)
    vec3 viewTangent = normalize(gl_NormalMatrix * at_tangent.xyz);
    vTangent = viewToScene(viewTangent);
    vBitangent = cross(vTangent, vNormal) * sign(at_tangent.w);
#endif

    gl_Position = jitterClipPos(gl_ProjectionMatrix * vec4(viewPos, 1.0));
}

#endif
