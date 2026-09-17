#version 330 compatibility

/* Untextured geometry such as the block outline. */
#define GB_NO_TEXTURE
#define GB_NO_LIGHTMAP
#include "/lib/program/gbuffer_fragment.glsl"
