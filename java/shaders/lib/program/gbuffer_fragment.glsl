#ifndef PROGRAM_GBUFFER_FRAGMENT_GLSL
#define PROGRAM_GBUFFER_FRAGMENT_GLSL

/*
    Shared fragment stage for the opaque gbuffers programs.

    Writes the deferred g-buffer and nothing else - colortex0 is deliberately
    left alone here so the sky drawn earlier in the frame survives until the
    deferred pass replaces it.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/material.glsl"
#include "/lib/noise.glsl"

#ifndef GB_ALPHA_CUTOFF
    #define GB_ALPHA_CUTOFF 0.10
#endif

in vec2 texcoord;
in vec2 lmcoord;
in vec4 glcolor;
in vec3 vNormal;
in vec3 vScenePos;
flat in float vMatID;

#if defined(GB_NORMAL_MAP) && defined(MC_NORMAL_MAP)
in vec3 vTangent;
in vec3 vBitangent;
#endif

/* RENDERTARGETS: 1,2,3 */

void main() {
#ifdef GB_NO_TEXTURE
    vec4 color = glcolor;
#else
    vec4 color = texture(gtexture, texcoord) * glcolor;
#endif

#ifdef HIDE_VANILLA_ENTITY_SHADOW
    /*
        Drop the flat oval Minecraft paints under every entity.  The shadow map
        already draws this entity's real silhouette, and leaving both in place
        puts a dark ellipse underneath an otherwise correctly shaped shadow.

        Which gbuffers program the blob arrives through depends on the loader
        and the game version, so the test is not restricted to entity programs.
    */
    if (entityId == ENTITY_BLOB_SHADOW) discard;
#endif

#ifdef GB_ENTITY
    /* Hurt flash, creeper charge-up, and the like. */
    color.rgb = mix(color.rgb, entityColor.rgb, entityColor.a);
#endif

#ifdef GB_STOCHASTIC_ALPHA
    /*
        Dithered cutout instead of blending.  Clouds stay full members of the
        g-buffer - lit, fogged and reflected like everything else - and the
        temporal filter turns the dither back into a soft edge.
    */
    float threshold = bayer16(gl_FragCoord.xy);
#ifdef TAA
    /* Advance the pattern each frame; a static one would survive temporal
       accumulation as a visible grid instead of resolving to a soft edge. */
    threshold = fract(threshold + float(frameCounter % 16) * 0.0625);
#endif
    if (color.a < threshold * 0.92 + 0.04) discard;
    color.a = 1.0;
#else
    if (color.a < GB_ALPHA_CUTOFF) discard;
#endif

    vec3 albedo = srgbToLinear(color.rgb);

    /*
        Custom entity models - the ones train, ship and aircraft mods are built
        from - occasionally arrive with zero-length or missing normals.  Falling
        back to the surface's own derivatives keeps such a model shaded, and
        shadowed, instead of turning it into a flat silhouette.
    */
    float normalLength = length(vNormal);
    vec3 normal;
    if (normalLength < 1e-3) {
        normal = normalize(cross(dFdx(vScenePos), dFdy(vScenePos)));
        if (dot(normal, normalize(-vScenePos)) < 0.0) normal = -normal;
    } else {
        normal = vNormal / normalLength;
    }

#if defined(GB_NORMAL_MAP) && defined(MC_NORMAL_MAP)
    vec3 tangentNormal = texture(normals, texcoord).rgb * 2.0 - 1.0;
    tangentNormal.z = sqrt(max(1.0 - dot(tangentNormal.xy, tangentNormal.xy), 0.0));
    mat3 tbn = mat3(normalize(vTangent), normalize(vBitangent), normal);
    normal = normalize(tbn * tangentNormal);
#endif

    Material material = defaultMaterial(albedo, vMatID);

#if defined(GB_NORMAL_MAP) && defined(MC_SPECULAR_MAP)
    applyLabPbrSpecular(material, texture(specular, texcoord));
#endif

#ifdef GB_EMISSIVE
    material.emission = max(material.emission, GB_EMISSIVE);
#endif

    gl_FragData[0] = vec4(encodeNormal(normal), lmcoord);
    gl_FragData[1] = vec4(material.albedo, encodeMaterial(material.id));
    gl_FragData[2] = vec4(material.roughness, material.f0, material.emission, material.sss);
}

#endif
