#version 330 compatibility

/* Vanilla clouds, dithered into the g-buffer. */
#define GB_NO_LIGHTMAP
#define GB_STOCHASTIC_ALPHA
#define GB_MATERIAL MAT_CLOUD
#include "/lib/program/gbuffer_fragment.glsl"
