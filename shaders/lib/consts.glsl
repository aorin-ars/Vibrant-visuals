#ifndef LIB_CONSTS_GLSL
#define LIB_CONSTS_GLSL

#include "/lib/settings.glsl"

/*
    Pipeline constants.  OptiFine and Iris parse these `const` declarations out
    of the shader source, so the values have to be literals - the ones carrying
    a trailing value list also show up in the options screen.
*/

/* ---------------------------------------------------------- shadow map setup */

const int   shadowMapResolution = 2048; //[512 1024 1536 2048 3072 4096 6144 8192]
const float shadowDistance = 160.0; //[64.0 96.0 128.0 160.0 192.0 256.0 320.0]
const float shadowDistanceRenderMul = 1.0;
const float shadowIntervalSize = 2.0;

/*
    Entity shadow bound multiplier (Iris).  Entities are culled from the shadow
    pass by the distance of their origin, so a long multi-block entity - a train
    car, a ship, an airship - can vanish from the shadow map while a good part
    of it is still well inside the shadow distance.  Rendering entities out to a
    multiple of the terrain bound keeps their shadow attached to them.
*/
const float entityShadowDistanceMul = 2.0; //[1.0 1.5 2.0 3.0 4.0]

const bool  shadowHardwareFiltering = false;
const bool  shadowtex0Nearest = false;
const bool  shadowtex1Nearest = false;
const bool  shadowcolor0Nearest = false;
const bool  generateShadowMipmap = false;
const bool  generateShadowColorMipmap = false;

/* Light that has passed through nothing must arrive untinted. */
const vec4  shadowcolor0ClearColor = vec4(1.0, 1.0, 1.0, 1.0);

/* ------------------------------------------------------------- world tuning */

const float sunPathRotation = -25.0; //[-50.0 -40.0 -30.0 -25.0 -20.0 -10.0 0.0 10.0 20.0 25.0 30.0 40.0]
const float ambientOcclusionLevel = 0.85; //[0.00 0.25 0.50 0.75 0.85 1.00]
const float wetnessHalflife = 200.0;
const float drynessHalflife = 50.0;
const float eyeBrightnessHalflife = 4.0;
const float centerDepthHalflife = 2.0;

/* ------------------------------------------------------------ gbuffer layout */

/*
    0  RGBA16F  scene radiance (HDR)
    1  RGBA16   octahedral normal .xy | block light | sky light
    2  RGBA16   albedo .rgb | material id
    3  RGBA16   roughness | reflectance | emission | subsurface
    4  RGBA16F  auto exposure history            (never cleared)
    5  RGBA16F  temporal AA history              (never cleared)
    6  RGBA16F  ambient occlusion, then bloom
    7  RGBA16F  opaque scene copy, then bloom
*/
const int colortex0Format = RGBA16F;
const int colortex1Format = RGBA16;
const int colortex2Format = RGBA16;
const int colortex3Format = RGBA16;
const int colortex4Format = RGBA16F;
const int colortex5Format = RGBA16F;
const int colortex6Format = RGBA16F;
const int colortex7Format = RGBA16F;

/* ------------------------------------------------------------- material ids */

#define MAT_DEFAULT      0.0
#define MAT_FOLIAGE      1.0
#define MAT_LEAVES       2.0
#define MAT_EMISSIVE     3.0
#define MAT_LAMP         4.0
#define MAT_WATER        5.0
#define MAT_GLASS        6.0
#define MAT_METAL        7.0
#define MAT_ENTITY       8.0
#define MAT_VEHICLE      9.0
#define MAT_BLOCK_ENTITY 10.0
#define MAT_HAND         11.0
#define MAT_PARTICLE     12.0
#define MAT_SKY          13.0
#define MAT_CLOUD        14.0

#define MAT_ENCODE (1.0 / 255.0)

/* --------------------------------------------------------------- entity ids */
/* Keep in sync with shaders/entity.properties. */

#define ENTITY_BLOB_SHADOW 4000
#define ENTITY_FLAME       4001
#define ENTITY_LIGHTNING   4002
#define ENTITY_VEHICLE     4010
#define ENTITY_RAIL_CAR    4011

/* ---------------------------------------------------------------- block ids */
/* Keep in sync with shaders/block.properties. */

#define BLOCK_PLANT_SMALL  10
#define BLOCK_PLANT_TALL   11
#define BLOCK_LEAVES       12
#define BLOCK_CROP         13
#define BLOCK_WATER        20
#define BLOCK_LAVA         21
#define BLOCK_EMISSIVE     30
#define BLOCK_LAMP         31
#define BLOCK_GLASS        40
#define BLOCK_METAL        50

#endif
