#version 330 compatibility

#define GB_NO_LIGHTMAP
#define GB_MATERIAL MAT_EMISSIVE
#define GB_EMISSIVE 1.0
#include "/lib/program/gbuffer_fragment.glsl"
