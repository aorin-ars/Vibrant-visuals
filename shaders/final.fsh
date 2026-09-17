#version 330 compatibility

/*
    Display transform.

    Exposure, bloom, the tone curve and the grade all happen here, in that
    order, on linear scene radiance - so everything upstream stayed free to be
    as bright as it physically is.
*/

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/noise.glsl"
#include "/lib/tonemap.glsl"

in vec2 texcoord;

vec3 sharpenedScene(vec2 uv, float amount) {
    vec3 centre = texture(colortex0, uv).rgb;
    if (amount <= 0.0) return centre;

    vec2 texel = 1.0 / vec2(viewWidth, viewHeight);
    vec3 neighbours = texture(colortex0, uv + vec2( texel.x, 0.0)).rgb
                    + texture(colortex0, uv + vec2(-texel.x, 0.0)).rgb
                    + texture(colortex0, uv + vec2(0.0,  texel.y)).rgb
                    + texture(colortex0, uv + vec2(0.0, -texel.y)).rgb;

    return max(centre + (centre - neighbours * 0.25) * amount, vec3(0.0));
}

void main() {
    /* Temporal accumulation softens the image slightly; the extra sharpening
       here is what pays that back. */
    float sharpenAmount = SHARPEN;
#ifdef TAA
    sharpenAmount += TAA_SHARPEN;
#endif

    vec3 color = sharpenedScene(texcoord, sharpenAmount);

#ifdef BLOOM
    vec3 bloom = texture(colortex7, texcoord).rgb;
    color = mix(color, bloom, saturate(0.045 * BLOOM_STRENGTH));
#endif

    float exposure = MANUAL_EXPOSURE;
#ifdef AUTO_EXPOSURE
    exposure *= max(texture(colortex4, texcoord).r, 1e-3);
#endif
    color *= exposure * mix(1.0, 1.35, screenBrightness);

    color = tonemap(color);
    color = colorGrade(color);

    float vignette = 1.0 - VIGNETTE_STRENGTH * pow(saturate(length(texcoord - 0.5) * 1.42), 2.5);
    color *= vignette;

    color = linearToSrgb(saturate(color));

    /* Ordered dither, below one 8-bit step, to keep gradients from banding. */
    color += (bayer16(gl_FragCoord.xy) - 0.5) / 255.0;

    gl_FragColor = vec4(color, 1.0);
}
