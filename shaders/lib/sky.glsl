#ifndef LIB_SKY_GLSL
#define LIB_SKY_GLSL

#include "/lib/common.glsl"
#include "/lib/space.glsl"

/*
    A compact single-scattering sky.

    Rayleigh optical depth gives the dome its blue and the horizon its whiteness
    for free, and running the same extinction along the sun ray is what turns
    sunlight orange at low elevations.  Everything is in linear radiance; the
    tonemapper at the end of the frame is what makes it look like a photograph.
*/

/* Rayleigh / aerosol optical depth at the zenith. */
const vec3 TAU_RAYLEIGH = vec3(0.0490, 0.1136, 0.2782);
const vec3 TAU_MIE      = vec3(0.0210);

const vec3 SUN_BASE_IRRADIANCE  = vec3(4.20, 4.05, 3.80);
const vec3 MOON_BASE_IRRADIANCE = vec3(0.020, 0.026, 0.042);
const vec3 NIGHT_SKY_RADIANCE   = vec3(0.0016, 0.0022, 0.0042);
const vec3 GROUND_ALBEDO        = vec3(0.22, 0.21, 0.18);

/*
    Relative air mass.  Exact enough between the zenith and a couple of degrees
    below the horizon, and it never divides by zero.
*/
float airMass(float cosZenith) {
    float c = max(cosZenith, 0.0);
    return 1.0 / (c + 0.025 * exp(-11.0 * c));
}

vec3 sunDirection()   { return normalize(viewToScene(sunPosition)); }
vec3 moonDirection()  { return normalize(viewToScene(moonPosition)); }
vec3 shadowLightDir() { return normalize(viewToScene(shadowLightPosition)); }

/* 1 while the sun is the shadow caster, 0 while the moon is. */
float dayFactor() {
    return smoothstep(-0.06, 0.06, sunDirection().y);
}

/* Extinction of a light source coming from `dir`, normalised to white at the zenith. */
vec3 solarTransmittance(vec3 dir) {
    float m = airMass(dir.y);
    return exp(-(TAU_RAYLEIGH + TAU_MIE) * (m - 1.0));
}

vec3 sunIrradiance() {
    vec3 dir = sunDirection();
    float horizonFade = smoothstep(-0.055, 0.075, dir.y);
    return SUN_BASE_IRRADIANCE * solarTransmittance(dir) * horizonFade * SUN_ILLUMINANCE;
}

vec3 moonIrradiance() {
    vec3 dir = moonDirection();
    float horizonFade = smoothstep(-0.040, 0.090, dir.y);
    /* Phase 0 is full moon, 4 is new moon. */
    float phase = 1.0 - abs(float(moonPhase) - 4.0) * 0.25;
    return MOON_BASE_IRRADIANCE * horizonFade * mix(0.35, 1.0, phase) * SUN_ILLUMINANCE;
}

/* Irradiance of whichever body is currently casting shadows. */
vec3 directIrradiance() {
    return mix(moonIrradiance(), sunIrradiance(), dayFactor());
}

float miePhase(float cosTheta, float g) {
    float gg = g * g;
    float denom = 1.0 + gg - 2.0 * g * cosTheta;
    return (1.0 - gg) / (4.0 * PI * denom * sqrt(max(denom, 1e-4)));
}

float rayleighPhase(float cosTheta) {
    return 0.0596831 * (1.0 + cosTheta * cosTheta);
}

/* Inscattered light along one view ray, before the sun disc is added. */
vec3 scatterAlongRay(vec3 dir, vec3 lightDir, vec3 irradiance, float mieBoost) {
    float cosTheta = dot(dir, lightDir);
    float m = airMass(dir.y);

    vec3 gatheredR = 1.0 - exp(-TAU_RAYLEIGH * m);
    vec3 gatheredM = 1.0 - exp(-TAU_MIE * m);

    vec3 inscatter = gatheredR * rayleighPhase(cosTheta) * 8.0;
    inscatter += gatheredM * miePhase(cosTheta, 0.76) * mieBoost;

    return inscatter * irradiance;
}

vec3 skyRadiance(vec3 dir) {
    dir = normalize(dir);
    vec3 up = vec3(dir.x, abs(dir.y), dir.z);

    vec3 sky = scatterAlongRay(up, sunDirection(), sunIrradiance(), 1.2);
    sky += scatterAlongRay(up, moonDirection(), moonIrradiance(), 0.6);
    sky += NIGHT_SKY_RADIANCE * (1.0 - dayFactor() * 0.85);

    /* Below the horizon the ray sees ground-bounced light instead of sky. */
    float below = smoothstep(0.0, -0.10, dir.y);
    vec3 ground = sky * GROUND_ALBEDO * 1.6;
    sky = mix(sky, ground, below);

    /* Overcast weather flattens the dome towards Minecraft's own fog colour. */
    vec3 overcast = vec3(luminance(sky)) * vec3(0.92, 0.96, 1.05);
    sky = mix(sky, overcast, rainStrength * 0.80);

    sky = mix(vec3(luminance(sky)), sky, SKY_SATURATION);
    return max(sky, vec3(0.0)) * SKY_ILLUMINANCE;
}

/*
    Hemispheric irradiance from the dome.

    Four cardinal samples plus a zenith sample is enough structure to keep north
    facing walls cool and sunward walls warm without an SH projection.
*/
vec3 skyIrradiance(vec3 normal) {
    vec3 zenith = skyRadiance(vec3(0.0, 1.0, 0.0));
    vec3 sunward = skyRadiance(normalize(vec3(sunDirection().x, 0.25, sunDirection().z)));
    vec3 away = skyRadiance(normalize(vec3(-sunDirection().x, 0.25, -sunDirection().z)));
    vec3 horizon = mix(away, sunward, saturate(dot(normalize(vec3(normal.x, 0.0, normal.z) + 1e-5),
                                                   normalize(vec3(sunDirection().x, 0.0, sunDirection().z) + 1e-5)) * 0.5 + 0.5));
    vec3 ground = (zenith + horizon) * 0.5 * GROUND_ALBEDO;

    float upness = normal.y * 0.5 + 0.5;
    vec3 ambient = mix(ground, zenith, upness * upness);
    ambient = mix(ambient, horizon, 1.0 - abs(normal.y));
    return ambient * PI * 0.55;
}

/* Average dome radiance - used for fog and for the water's flat sky term. */
vec3 skyAverage() {
    return (skyRadiance(vec3(0.0, 1.0, 0.0)) * 2.0
          + skyRadiance(normalize(vec3( 1.0, 0.12,  0.0)))
          + skyRadiance(normalize(vec3(-1.0, 0.12,  0.0)))
          + skyRadiance(normalize(vec3( 0.0, 0.12,  1.0)))
          + skyRadiance(normalize(vec3( 0.0, 0.12, -1.0)))) / 6.0;
}

/* Sun and moon discs, drawn into the sky programs only. */
vec3 celestialDiscs(vec3 dir) {
    vec3 result = vec3(0.0);

    float sunCos = dot(dir, sunDirection());
    float sunDisc = smoothstep(0.99965, 0.99987, sunCos);
    result += sunDisc * sunIrradiance() * 30.0;

    float moonCos = dot(dir, moonDirection());
    float moonDisc = smoothstep(0.9990, 0.9996, moonCos);
    result += moonDisc * vec3(0.55, 0.60, 0.72) * (1.0 - dayFactor()) * 1.5;

    return result * (1.0 - rainStrength * 0.9);
}

#endif
