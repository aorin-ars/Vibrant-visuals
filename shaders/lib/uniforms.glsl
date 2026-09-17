#ifndef LIB_UNIFORMS_GLSL
#define LIB_UNIFORMS_GLSL

/*
    A single place for every uniform the pack uses.

    Which block gets pulled in is decided by the including program, because the
    texture units behind a name are not the same everywhere: gbuffers programs
    see gtexture/lightmap on units 0-1 and only colortex4-7, while composite and
    deferred programs see the full colortex0-15 set.  Declaring the wrong block
    would alias two samplers onto one unit.

        USE_GBUFFER_SAMPLERS  gtexture, lightmap, normals, specular, ...
        USE_AUX_SAMPLERS      colortex4-7 (readable from gbuffers programs)
        USE_SCENE_SAMPLERS    colortex0-7, depthtex0-2 (composite / deferred)
        USE_SHADOW_SAMPLERS   shadowtex0/1, shadowcolor0
*/

/* ------------------------------------------------------------------ matrices */

uniform mat4 gbufferModelView;
uniform mat4 gbufferModelViewInverse;
uniform mat4 gbufferProjection;
uniform mat4 gbufferProjectionInverse;
uniform mat4 gbufferPreviousModelView;
uniform mat4 gbufferPreviousProjection;
uniform mat4 shadowModelView;
uniform mat4 shadowModelViewInverse;
uniform mat4 shadowProjection;
uniform mat4 shadowProjectionInverse;

/* -------------------------------------------------------------------- camera */

uniform vec3  cameraPosition;
uniform vec3  previousCameraPosition;
uniform float near;
uniform float far;
uniform float viewWidth;
uniform float viewHeight;
uniform float aspectRatio;
uniform float eyeAltitude;
uniform float centerDepthSmooth;

/* --------------------------------------------------------------- celestials */

uniform vec3  sunPosition;
uniform vec3  moonPosition;
uniform vec3  shadowLightPosition;
uniform vec3  upPosition;
uniform float sunAngle;
uniform float shadowAngle;
uniform int   moonPhase;

/* ------------------------------------------------------------------- world */

uniform vec3  skyColor;
uniform vec3  fogColor;
uniform float rainStrength;
uniform float wetness;
uniform float frameTime;
uniform float frameTimeCounter;
uniform int   frameCounter;
uniform int   worldTime;
uniform int   worldDay;
uniform int   isEyeInWater;
uniform int   hideGUI;
uniform ivec2 eyeBrightnessSmooth;
uniform float nightVision;
uniform float blindness;
uniform float darknessFactor;
uniform float screenBrightness;
uniform float playerMood;
uniform int   heldBlockLightValue;
uniform int   heldBlockLightValue2;

/* ----------------------------------------------------------- gbuffer inputs */

#ifdef USE_GBUFFER_SAMPLERS
uniform sampler2D gtexture;
uniform sampler2D lightmap;
#ifdef MC_NORMAL_MAP
uniform sampler2D normals;
#endif
#ifdef MC_SPECULAR_MAP
uniform sampler2D specular;
#endif
uniform vec4  entityColor;
uniform int   entityId;
uniform int   blockEntityId;
uniform int   renderStage;
uniform float alphaTestRef;
#endif

/* ------------------------------------------------------------ colour buffers */

#ifdef USE_SCENE_SAMPLERS
uniform sampler2D colortex0;
uniform sampler2D colortex1;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
uniform sampler2D colortex4;
uniform sampler2D colortex5;
uniform sampler2D colortex6;
uniform sampler2D colortex7;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
uniform sampler2D depthtex2;
uniform sampler2D noisetex;
#else
#ifdef USE_AUX_SAMPLERS
uniform sampler2D colortex4;
uniform sampler2D colortex5;
uniform sampler2D colortex6;
uniform sampler2D colortex7;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
uniform sampler2D noisetex;
#endif
#endif

/* ------------------------------------------------------------ shadow buffers */

#ifdef USE_SHADOW_SAMPLERS
uniform sampler2D shadowtex0;
uniform sampler2D shadowtex1;
uniform sampler2D shadowcolor0;
#endif

#endif
