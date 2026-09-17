#ifndef LIB_FOG_GLSL
#define LIB_FOG_GLSL

#include "/lib/common.glsl"
#include "/lib/sky.glsl"

/*
    Aerial perspective.

    Distant geometry is blended towards the radiance of the sky in that exact
    direction rather than towards a flat fog colour, which is what keeps a
    hillside blue at noon and pink at sunset without any per-time-of-day tables.
*/

/* Absorption of clear water, per block, roughly following Pope & Fry. */
const vec3 WATER_EXTINCTION = vec3(0.42, 0.09, 0.045);

float heightFogOpticalDepth(vec3 rayDir, float dist, float camY) {
    float k = max(FOG_ALTITUDE_FALLOFF * 0.045, 1e-4);
    float relativeY = clamp(camY - 62.0, -24.0, 512.0);
    float base = exp(-k * relativeY);
    float vertical = k * rayDir.y;

    /* Closed form of the exponential height integral; degrades to dist * base
       as the ray flattens out or as the falloff approaches zero. */
    float t = abs(vertical) < 1e-4
            ? dist * base
            : base * (1.0 - exp(-vertical * dist)) / vertical;

    return max(t, 0.0);
}

vec3 applyAtmosphericFog(vec3 color, vec3 scenePos, bool isSky) {
    float dist = length(scenePos);
    vec3 rayDir = dist > 1e-4 ? scenePos / dist : vec3(0.0, 1.0, 0.0);

    float density = FOG_DENSITY * mix(0.0025, 0.0090, rainStrength);
    float opticalDepth = heightFogOpticalDepth(rayDir, dist, cameraPosition.y);
    float fogAmount = isSky ? 0.0 : 1.0 - exp(-opticalDepth * density);

    /* Hide the render-distance edge behind the same haze. */
    if (!isSky) {
        float border = smoothstep(far * 0.72, far * 0.96, dist);
        fogAmount = max(fogAmount, border);
    }

    vec3 fogColour = skyRadiance(rayDir);
    color = mix(color, fogColour, saturate(fogAmount));

    /* Caves and the darkness effect get their own flat, light-swallowing fog. */
    float caveFog = (1.0 - saturate(float(eyeBrightnessSmooth.y) / 240.0)) * 0.55;
    caveFog = max(caveFog, darknessFactor);
    if (caveFog > 0.0 && !isSky) {
        float t = 1.0 - exp(-dist * 0.010 * caveFog);
        color = mix(color, vec3(0.0), saturate(t * 0.85));
    }

    return color;
}

/* Absorption plus in-scattering for anything seen through water. */
vec3 applyWaterFog(vec3 color, float dist, float skyLight) {
    vec3 extinction = WATER_EXTINCTION * WATER_ABSORPTION;
    vec3 transmittance = exp(-extinction * dist);

    vec3 scatterColour = skyAverage() * mix(0.10, 0.55, skyLight)
                       * vec3(0.20, 0.55, 0.70);

    return color * transmittance + scatterColour * (1.0 - transmittance);
}

/* Fog for the medium the camera itself is inside. */
vec3 applyEyeMediumFog(vec3 color, float dist, float skyLight) {
    if (isEyeInWater == 1) {
        return applyWaterFog(color, dist, skyLight);
    } else if (isEyeInWater == 2) {
        float t = 1.0 - exp(-dist * 2.2);
        return mix(color, vec3(2.20, 0.55, 0.08), saturate(t));
    } else if (isEyeInWater == 3) {
        float t = 1.0 - exp(-dist * 1.1);
        return mix(color, vec3(0.70, 0.76, 0.86), saturate(t));
    }
    return color;
}

#endif
