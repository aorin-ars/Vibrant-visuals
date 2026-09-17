#version 330 compatibility

/*
    Sun and moon.  The vanilla textures are kept so resource packs still apply;
    they are only lifted into the same HDR range as the rest of the frame.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"

in vec2 texcoord;
in vec3 vScenePos;
in vec4 glcolor;

/* RENDERTARGETS: 0 */

void main() {
    vec4 tex = texture(gtexture, texcoord) * glcolor;
    if (tex.a < 0.01) discard;

    vec3 color = srgbToLinear(tex.rgb);

    /* MC_RENDER_STAGE_* only exists from 1.17 on, so fall back to asking which
       body this quad happens to be facing. */
#ifdef MC_RENDER_STAGE_SUN
    bool isSun = renderStage == MC_RENDER_STAGE_SUN;
#else
    bool isSun = dot(normalize(vScenePos), sunDirection()) > 0.0;
#endif

    if (isSun) {
        color *= sunIrradiance() * 7.0;
    } else {
        color *= vec3(0.62, 0.68, 0.85) * (1.0 - dayFactor() * 0.85);
    }

    color *= 1.0 - rainStrength * 0.85;

    gl_FragData[0] = vec4(color, tex.a);
}
