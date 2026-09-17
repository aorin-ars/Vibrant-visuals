#version 330 compatibility

/* Held items, drawn before the deferred pass. */
#define GB_NORMAL_MAP
#define GB_MATERIAL MAT_HAND
#include "/lib/program/gbuffer_fragment.glsl"
