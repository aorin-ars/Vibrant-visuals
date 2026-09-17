#ifndef LIB_SETTINGS_GLSL
#define LIB_SETTINGS_GLSL

/*
    Vibrant Visuals - user settings.

    Every #define in this file is picked up by the in-game shader options
    screen.  Display names and descriptions live in shaders/lang/*.lang, which
    is why the identifiers below carry no trailing prose: OptiFine and Iris
    only accept a bare value list in the trailing comment.
*/

/* ------------------------------------------------------------------ shadows */

#define SHADOW_FILTER 2 //[0 1 2 3]
#define SHADOW_SOFTNESS 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00 3.00]
#define SHADOW_DISTORTION 0.75 //[0.00 0.40 0.55 0.65 0.75 0.85 0.90]
#define SHADOW_BIAS_SCALE 1.00 //[0.50 0.75 1.00 1.25 1.50 2.00 3.00]
#define SHADOW_BRIGHTNESS 0.10 //[0.00 0.05 0.10 0.15 0.20 0.30]
#define COLORED_SHADOWS

/* ------------------------------------------------------- entities & vehicles */

#define ENTITY_SHADOW_BIAS 1.50 //[1.00 1.25 1.50 2.00 2.50 3.00 4.00]
#define HIDE_VANILLA_ENTITY_SHADOW
#define ENTITY_SPECULAR 0.55 //[0.00 0.25 0.40 0.55 0.70 0.85 1.00]
#define VEHICLE_SPECULAR 0.85 //[0.00 0.25 0.40 0.55 0.70 0.85 1.00]

/* ----------------------------------------------------------------- lighting */

#define SUN_ILLUMINANCE 1.00 //[0.50 0.75 1.00 1.25 1.50 2.00]
#define SKY_ILLUMINANCE 1.00 //[0.50 0.75 1.00 1.25 1.50 2.00]
#define BLOCKLIGHT_INTENSITY 1.00 //[0.50 0.75 1.00 1.25 1.50 2.00]
#define BLOCKLIGHT_TEMPERATURE 2600.0 //[2000.0 2300.0 2600.0 3000.0 3500.0 4500.0 6500.0]
#define MINIMUM_LIGHT 0.03 //[0.00 0.01 0.03 0.06 0.10 0.20]
#define SPECULAR_HIGHLIGHT
#define HANDHELD_LIGHT
#define SUBSURFACE_SCATTERING

#define SSAO
#define SSAO_SAMPLES 10 //[4 6 8 10 14 20]
#define SSAO_RADIUS 1.20 //[0.50 0.80 1.20 1.80 2.50]
#define SSAO_STRENGTH 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00]

/* --------------------------------------------------------------- atmosphere */

#define SKY_SATURATION 1.10 //[0.80 0.90 1.00 1.10 1.20 1.40]
#define FOG_DENSITY 1.00 //[0.00 0.25 0.50 0.75 1.00 1.50 2.00 3.00]
#define FOG_ALTITUDE_FALLOFF 1.00 //[0.00 0.50 1.00 1.50 2.50]
#define VOLUMETRIC_LIGHT
#define VOLUMETRIC_STEPS 12 //[6 8 12 16 24 32]
#define VOLUMETRIC_STRENGTH 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00 3.00]
#define CLOUD_BRIGHTNESS 1.00 //[0.50 0.75 1.00 1.25 1.50]

/* -------------------------------------------------------------------- water */

#define WATER_WAVES
#define WATER_WAVE_HEIGHT 1.00 //[0.00 0.50 0.75 1.00 1.50 2.00]
#define WATER_REFLECTIONS
#define WATER_ABSORPTION 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00]
#define WATER_ALPHA 0.25 //[0.10 0.18 0.25 0.35 0.50 0.75]
#define REFRACTION

/* ------------------------------------------------------------------- waving */

#define WAVING_PLANTS
#define WAVING_LEAVES
#define WAVING_STRENGTH 1.00 //[0.00 0.50 0.75 1.00 1.50 2.00]

/* ------------------------------------------------ screen space reflections */

#define SSR
#define SSR_STEPS 20 //[8 12 16 20 28 40]
#define SSR_REFINE 4 //[0 2 4 6]

/* ---------------------------------------------------------------- post-fx */

#define TAA
#define TAA_SHARPEN 0.55 //[0.00 0.25 0.40 0.55 0.75 1.00]
#define BLOOM
#define BLOOM_STRENGTH 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00 3.00]
#define AUTO_EXPOSURE
#define EXPOSURE_SPEED 1.00 //[0.25 0.50 1.00 2.00 4.00]
#define MANUAL_EXPOSURE 1.00 //[0.25 0.50 0.75 1.00 1.50 2.00 3.00]
#define TONEMAP 1 //[0 1 2 3]
#define VIBRANCE 1.15 //[0.80 0.90 1.00 1.10 1.15 1.25 1.40]
#define SATURATION 1.05 //[0.80 0.90 1.00 1.05 1.10 1.20 1.40]
#define CONTRAST 1.05 //[0.90 0.95 1.00 1.05 1.10 1.20]
#define WHITE_BALANCE 6500.0 //[4500.0 5000.0 5500.0 6000.0 6500.0 7000.0 8000.0]
#define VIGNETTE_STRENGTH 0.25 //[0.00 0.15 0.25 0.40 0.60]
#define SHARPEN 0.35 //[0.00 0.15 0.35 0.55 0.80]

/* --------------------------------------------------------------- debugging */

//#define DEBUG_SHADOW_VISIBILITY
//#define DEBUG_MATERIAL_ID

#endif
