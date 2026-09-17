#ifndef LIB_SPACE_GLSL
#define LIB_SPACE_GLSL

#include "/lib/common.glsl"

/*
    Coordinate spaces used throughout the pack:

      view    - OpenGL eye space, what gl_ModelViewMatrix produces
      scene   - world-aligned axes, still centred on the camera
      world   - scene + cameraPosition, the coordinates the player sees in F3
      screen  - [0,1] on all three axes, z being the depth buffer value
*/

vec3 viewToScene(vec3 viewPos)  { return mat3(gbufferModelViewInverse) * viewPos; }
vec3 sceneToView(vec3 scenePos) { return mat3(gbufferModelView) * scenePos; }

vec3 viewToScenePoint(vec3 viewPos) {
    return (gbufferModelViewInverse * vec4(viewPos, 1.0)).xyz;
}
vec3 sceneToViewPoint(vec3 scenePos) {
    return (gbufferModelView * vec4(scenePos, 1.0)).xyz;
}

vec3 screenToView(vec3 screenPos) {
    vec4 clip = vec4(screenPos * 2.0 - 1.0, 1.0);
    vec4 view = gbufferProjectionInverse * clip;
    return view.xyz / view.w;
}

vec3 viewToScreen(vec3 viewPos) {
    vec4 clip = gbufferProjection * vec4(viewPos, 1.0);
    return (clip.xyz / clip.w) * 0.5 + 0.5;
}

float linearizeDepth(float depth) {
    return (near * far) / (depth * (near - far) + far);
}

float delinearizeDepth(float linear) {
    return (far - (near * far) / linear) / (far - near);
}

/* ------------------------------------------------------------ temporal jitter */

/* Halton(2,3), recentred on the pixel. */
const vec2 TAA_OFFSETS[8] = vec2[8](
    vec2( 0.0000, -0.1666667),
    vec2(-0.2500,  0.1666667),
    vec2( 0.2500, -0.3888889),
    vec2(-0.3750, -0.0555556),
    vec2( 0.1250,  0.2777778),
    vec2(-0.1250, -0.2777778),
    vec2( 0.3750,  0.0555556),
    vec2(-0.4375,  0.3888889)
);

vec2 taaJitter() {
#ifdef TAA
    return TAA_OFFSETS[frameCounter % 8] * 2.0 / vec2(viewWidth, viewHeight);
#else
    return vec2(0.0);
#endif
}

/* Applied to a clip-space position, so the offset has to scale with w. */
vec4 jitterClipPos(vec4 clipPos) {
    clipPos.xy += taaJitter() * clipPos.w;
    return clipPos;
}

/*
    Where this pixel was last frame.  Static geometry only - entity motion is
    handled by the neighbourhood clamp in the TAA resolve, which is what keeps
    fast moving entities such as trains from smearing.
*/
vec3 reprojectScreenPos(vec3 screenPos) {
    vec3 viewPos  = screenToView(screenPos);
    vec3 scenePos = viewToScenePoint(viewPos);
    vec3 previous = scenePos + (cameraPosition - previousCameraPosition);

    vec4 prevView = gbufferPreviousModelView * vec4(previous, 1.0);
    vec4 prevClip = gbufferPreviousProjection * prevView;
    return (prevClip.xyz / prevClip.w) * 0.5 + 0.5;
}

#endif
