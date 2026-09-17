#ifndef LIB_MATERIAL_GLSL
#define LIB_MATERIAL_GLSL

#include "/lib/common.glsl"

/*
    Surface description handed from the gbuffer programs to the lighting code.

    Resource packs that ship LabPBR maps drive these fields directly; everything
    else falls back to sensible defaults keyed off the material id, which is how
    a plain untextured train model still ends up with glossy painted sides
    instead of the same chalky response as dirt.
*/
struct Material {
    vec3  albedo;
    float roughness;
    float f0;
    float emission;
    float sss;
    float id;
};

Material defaultMaterial(vec3 albedo, float id) {
    Material m;
    m.albedo = albedo;
    m.roughness = 0.88;
    m.f0 = 0.04;
    m.emission = 0.0;
    m.sss = 0.0;
    m.id = id;

    if (id == MAT_FOLIAGE) {
        m.roughness = 0.90;
        m.sss = 0.75;
    } else if (id == MAT_LEAVES) {
        m.roughness = 0.82;
        m.sss = 0.55;
    } else if (id == MAT_EMISSIVE) {
        m.emission = 1.00;
        m.roughness = 0.70;
    } else if (id == MAT_LAMP) {
        m.emission = 0.55;
        m.roughness = 0.55;
    } else if (id == MAT_WATER) {
        m.roughness = 0.02;
        m.f0 = 0.02;
    } else if (id == MAT_GLASS) {
        m.roughness = 0.05;
        m.f0 = 0.08;
    } else if (id == MAT_METAL) {
        m.roughness = 0.32;
        m.f0 = 0.55;
    } else if (id == MAT_ENTITY || id == MAT_BLOCK_ENTITY) {
        m.roughness = mix(0.92, 0.18, ENTITY_SPECULAR);
        m.f0 = mix(0.03, 0.09, ENTITY_SPECULAR);
    } else if (id == MAT_VEHICLE) {
        /* Painted, lacquered bodywork: glossier and a touch more reflective. */
        m.roughness = mix(0.92, 0.12, VEHICLE_SPECULAR);
        m.f0 = mix(0.03, 0.13, VEHICLE_SPECULAR);
    } else if (id == MAT_HAND) {
        m.roughness = 0.75;
    } else if (id == MAT_CLOUD) {
        m.roughness = 0.95;
        m.sss = 0.90;
        m.albedo *= CLOUD_BRIGHTNESS;
    }

    return m;
}

#if defined(MC_SPECULAR_MAP) && defined(USE_GBUFFER_SAMPLERS)
/* LabPBR 1.3 specular map: r smoothness, g reflectance, b porosity/SSS, a emission. */
void applyLabPbrSpecular(inout Material m, vec4 spec) {
    m.roughness = sqr(1.0 - spec.r);

    float reflectance = spec.g;
    if (reflectance * 255.0 >= 229.5) {
        /* Metal: the albedo becomes the reflectance. */
        m.f0 = 1.0;
    } else {
        m.f0 = reflectance;
    }

    if (spec.b * 255.0 > 64.5) {
        m.sss = (spec.b * 255.0 - 65.0) / 190.0;
    }

    if (spec.a < 1.0) {
        m.emission = max(m.emission, spec.a * (255.0 / 254.0));
    }
}
#endif

/* Terrain block ids come from shaders/block.properties via mc_Entity.x. */
float materialFromBlockId(int id) {
    if (id == BLOCK_LEAVES) return MAT_LEAVES;
    if (id == BLOCK_PLANT_SMALL || id == BLOCK_PLANT_TALL || id == BLOCK_CROP) return MAT_FOLIAGE;
    if (id == BLOCK_WATER) return MAT_WATER;
    if (id == BLOCK_LAVA || id == BLOCK_EMISSIVE) return MAT_EMISSIVE;
    if (id == BLOCK_LAMP) return MAT_LAMP;
    if (id == BLOCK_GLASS) return MAT_GLASS;
    if (id == BLOCK_METAL) return MAT_METAL;
    return MAT_DEFAULT;
}

/* Metals tint their reflection with the albedo; dielectrics do not. */
vec3 materialF0(Material m) {
    return mix(vec3(m.f0), m.albedo, saturate((m.f0 - 0.30) / 0.70));
}

#endif
