#version 330 compatibility

/*
    Depth is written for free; the colour buffer written here is the tint that
    light picks up on its way through a translucent caster.  A pane of stained
    glass, a sheet of ice or a train's tinted side window therefore drops a
    coloured shadow instead of a flat black one.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"

in vec2 texcoord;
in vec4 glcolor;

/* RENDERTARGETS: 0 */

void main() {
    vec4 color = texture(gtexture, texcoord) * glcolor;

    /*
        Only fully invisible texels are dropped.  Anything with a trace of alpha
        still belongs in shadowtex0 so the lighting pass can tell "blocked by
        something see-through" apart from "blocked by something solid".
    */
    if (color.a < 0.004) discard;

#ifdef HIDE_VANILLA_ENTITY_SHADOW
    /* The vanilla blob is a ground decal - letting it cast would self-shadow. */
    if (entityId == ENTITY_BLOB_SHADOW) discard;
#endif

    /*
        Transmitted colour.  Opaque casters land in shadowtex1 as well, where
        they block the light outright, so the value written for them is never
        read back - only the translucent ones matter here.
    */
    vec3 transmitted = mix(vec3(1.0), color.rgb, color.a);
    transmitted *= 1.0 - color.a * 0.55;

    gl_FragData[0] = vec4(transmitted, 1.0);
}
