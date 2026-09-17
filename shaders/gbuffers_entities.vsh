#version 330 compatibility

/* Every entity in the world, trains and ships included. */
#define GB_ENTITY
#define GB_NORMAL_MAP
#define GB_MATERIAL MAT_ENTITY
#include "/lib/program/gbuffer_vertex.glsl"
