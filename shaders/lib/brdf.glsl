#ifndef LIB_BRDF_GLSL
#define LIB_BRDF_GLSL

#include "/lib/common.glsl"

/* Trowbridge-Reitz / GGX normal distribution. */
float distributionGGX(float NdotH, float alpha) {
    float a2 = alpha * alpha;
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    return a2 / max(PI * d * d, 1e-7);
}

/* Height-correlated Smith visibility, already divided by 4*NdotL*NdotV. */
float visibilitySmithGGX(float NdotV, float NdotL, float alpha) {
    float a2 = alpha * alpha;
    float lambdaV = NdotL * sqrt(NdotV * NdotV * (1.0 - a2) + a2);
    float lambdaL = NdotV * sqrt(NdotL * NdotL * (1.0 - a2) + a2);
    return 0.5 / max(lambdaV + lambdaL, 1e-5);
}

vec3 fresnelSchlick(float cosTheta, vec3 f0) {
    float f = saturate(1.0 - cosTheta);
    float f2 = f * f;
    return f0 + (1.0 - f0) * (f2 * f2 * f);
}

/* Karis' analytic fit for the split-sum environment term. */
vec3 envBRDFApprox(vec3 f0, float roughness, float NdotV) {
    const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
    const vec4 c1 = vec4( 1.0,  0.0425,  1.040, -0.040);
    vec4 r = roughness * c0 + c1;
    float a004 = min(r.x * r.x, exp2(-9.28 * NdotV)) * r.x + r.y;
    vec2 ab = vec2(-1.04, 1.04) * a004 + r.zw;
    return f0 * ab.x + ab.y;
}

/*
    Direct specular lobe.

    This is what puts the long sun streak along a train's flank and the bright
    rim on a rail head; the Fresnel term is what makes it appear at grazing
    angles even on nominally dull paint.
*/
vec3 specularGGX(vec3 normal, vec3 viewDir, vec3 lightDir, float roughness, vec3 f0) {
    vec3 halfway = normalize(lightDir + viewDir);
    float NdotL = saturate(dot(normal, lightDir));
    float NdotV = saturate(dot(normal, viewDir)) + 1e-5;
    float NdotH = saturate(dot(normal, halfway));
    float VdotH = saturate(dot(viewDir, halfway));

    float alpha = max(roughness * roughness, 1e-4);
    float D = distributionGGX(NdotH, alpha);
    float V = visibilitySmithGGX(NdotV, NdotL, alpha);
    vec3  F = fresnelSchlick(VdotH, f0);

    return D * V * F * NdotL;
}

/* Lambert, with a wrap term so thin foliage keeps some light on its dark side. */
float diffuseWrap(float NdotL, float wrap) {
    return saturate((NdotL + wrap) / ((1.0 + wrap) * (1.0 + wrap)));
}

#endif
