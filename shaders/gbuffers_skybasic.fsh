#version 330 compatibility

/*
    The sky dome, drawn procedurally.

    Nothing here touches the g-buffer: the sky keeps the far-plane depth, and
    the deferred pass leaves those pixels exactly as this program left them.
*/

#define USE_GBUFFER_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/space.glsl"
#include "/lib/sky.glsl"

in vec3 vScenePos;
in vec4 glcolor;

/* RENDERTARGETS: 0 */

void main() {
    vec3 direction = normalize(vScenePos);

#ifdef MC_RENDER_STAGE_STARS
    if (renderStage == MC_RENDER_STAGE_STARS) {
        vec3 star = srgbToLinear(glcolor.rgb) * glcolor.a;
        star *= 2.5 * (1.0 - dayFactor()) * (1.0 - rainStrength);
        gl_FragData[0] = vec4(star, 1.0);
        return;
    }

    /* Our own scattering already reddens the horizon; the vanilla sunset quad
       painted on top of it would only wash the gradient out. */
    if (renderStage == MC_RENDER_STAGE_SUNSET) discard;
#endif

    gl_FragData[0] = vec4(skyRadiance(direction), 1.0);
}
