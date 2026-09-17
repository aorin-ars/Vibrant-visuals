#version 330 compatibility

/*
    Screen space ambient occlusion.

    Written on its own so the lighting pass can blur it across depth edges;
    a noisy AO term fed straight into shading is the usual reason contact
    shadows look like sandpaper.
*/

#define USE_SCENE_SAMPLERS

#include "/lib/common.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/buffers_persist.glsl"
#include "/lib/space.glsl"
#include "/lib/noise.glsl"

in vec2 texcoord;

/* RENDERTARGETS: 6 */

void main() {
    float depth = texture(depthtex0, texcoord).r;

    if (depth >= 1.0) {
        gl_FragData[0] = vec4(1.0);
        return;
    }

#ifndef SSAO
    gl_FragData[0] = vec4(1.0);
#else
    vec3 viewPos = screenToView(vec3(texcoord, depth));
    vec3 normal = sceneToView(decodeNormal(texture(colortex1, texcoord).rg));

    float rotation = sampleRotation(gl_FragCoord.xy);
    float occlusion = 0.0;

    for (int i = 0; i < SSAO_SAMPLES; i++) {
        vec3 direction = vogelSphere(i, SSAO_SAMPLES, rotation);
        if (dot(direction, normal) < 0.0) direction = -direction;

        float scale = 0.30 + 0.70 * float(i + 1) / float(SSAO_SAMPLES);
        vec3 samplePos = viewPos + direction * SSAO_RADIUS * scale;
        vec3 sampleScreen = viewToScreen(samplePos);

        if (saturate(sampleScreen.xy) != sampleScreen.xy) continue;

        float sceneDepth = texture(depthtex0, sampleScreen.xy).r;
        if (sceneDepth >= 1.0) continue;

        vec3 scenePos = screenToView(vec3(sampleScreen.xy, sceneDepth));

        /* View space z grows towards the camera, so a larger z is nearer. */
        if (scenePos.z > samplePos.z + 0.02) {
            float range = SSAO_RADIUS / max(abs(viewPos.z - scenePos.z), 1e-3);
            occlusion += saturate(range);
        }
    }

    float ao = 1.0 - occlusion / float(SSAO_SAMPLES);
    gl_FragData[0] = vec4(saturate(ao), 0.0, 0.0, 1.0);
#endif
}
