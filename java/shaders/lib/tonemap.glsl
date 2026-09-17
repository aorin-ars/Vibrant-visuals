#ifndef LIB_TONEMAP_GLSL
#define LIB_TONEMAP_GLSL

#include "/lib/common.glsl"

/*
    Display transform.

    Every operator below takes linear scene radiance and returns linear display
    values; the sRGB encode happens once, at the very end of `final`.
*/

vec3 tonemapReinhardJodie(vec3 c) {
    float l = luminance(c);
    vec3 tc = c / (c + 1.0);
    return mix(c / (l + 1.0), tc, tc);
}

const mat3 ACES_INPUT = mat3(
    0.59719, 0.07600, 0.02840,
    0.35458, 0.90834, 0.13383,
    0.04823, 0.01566, 0.83777);

const mat3 ACES_OUTPUT = mat3(
     1.60475, -0.10208, -0.00327,
    -0.53108,  1.10813, -0.07276,
    -0.07367, -0.00605,  1.07602);

vec3 rrtOdtFit(vec3 v) {
    vec3 a = v * (v + 0.0245786) - 0.000090537;
    vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
    return a / b;
}

vec3 tonemapACES(vec3 c) {
    c = ACES_INPUT * c;
    c = rrtOdtFit(c);
    return saturate(ACES_OUTPUT * c);
}

/* Uchimura's "GT" curve - a long linear section with a gentle shoulder. */
vec3 tonemapUchimura(vec3 x) {
    const float P = 1.00;   /* max display brightness */
    const float a = 1.05;   /* contrast of the linear section */
    const float m = 0.22;   /* where the linear section starts */
    const float l = 0.40;   /* how long it runs */
    const float c = 1.33;   /* toe curvature */

    float l0 = ((P - m) * l) / a;
    float S0 = m + l0;
    float S1 = m + a * l0;
    float C2 = (a * P) / (P - S1);
    float CP = -C2 / P;

    vec3 w0 = 1.0 - smoothstep(vec3(0.0), vec3(m), x);
    vec3 w2 = step(vec3(m + l0), x);
    vec3 w1 = 1.0 - w0 - w2;

    vec3 T = m * pow(max(x / m, 1e-5), vec3(c));
    vec3 S = P - (P - S1) * exp(CP * (x - S0));
    vec3 L = m + a * (x - m);

    return saturate(T * w0 + L * w1 + S * w2);
}

const mat3 AGX_INPUT = mat3(
    0.8424790622, 0.0423282422, 0.0423756549,
    0.0784336000, 0.8784686364, 0.0784336000,
    0.0792237451, 0.0791661274, 0.8791429737);

const mat3 AGX_OUTPUT = mat3(
     1.1968790051, -0.0528968517, -0.0529716355,
    -0.0980208811,  1.1519031299, -0.0980434501,
    -0.0990297440, -0.0989611768,  1.1510736726);

vec3 agxContrast(vec3 x) {
    vec3 x2 = x * x;
    vec3 x4 = x2 * x2;
    return 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4
         - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
}

/* AgX: log-encode, sigmoid, rotate back.  Holds saturated highlights together
   instead of letting them clip to a channel, which suits bright paintwork. */
vec3 tonemapAgX(vec3 c) {
    const float minEv = -12.47393;
    const float maxEv = 4.026069;

    c = AGX_INPUT * c;
    c = clamp(log2(max(c, vec3(1e-10))), minEv, maxEv);
    c = (c - minEv) / (maxEv - minEv);
    c = agxContrast(c);
    c = AGX_OUTPUT * c;
    return pow(saturate(c), vec3(2.2));
}

vec3 tonemap(vec3 color) {
#if TONEMAP == 0
    return tonemapReinhardJodie(color);
#elif TONEMAP == 1
    return tonemapACES(color);
#elif TONEMAP == 2
    return tonemapUchimura(color);
#else
    return tonemapAgX(color);
#endif
}

/* ------------------------------------------------------------------ grading */

vec3 whiteBalance(vec3 color, float kelvin) {
    /* Ratio of the target illuminant to D65, from the same Planckian fit the
       block light uses; a no-op at 6500 K. */
    float t = kelvin / 100.0;
    vec3 target;
    if (t <= 66.0) {
        target = vec3(1.0,
                      saturate((99.4708025861 * log(max(t, 1.0)) - 161.1195681661) / 255.0),
                      t <= 19.0 ? 0.0 : saturate((138.5177312231 * log(max(t - 10.0, 1.0)) - 305.0447927307) / 255.0));
    } else {
        target = vec3(saturate(329.698727446 * pow(t - 60.0, -0.1332047592) / 255.0),
                      saturate(288.1221695283 * pow(t - 60.0, -0.0755148492) / 255.0),
                      1.0);
    }
    target = srgbToLinear(max(target, vec3(0.02)));
    target /= max(luminance(target), 1e-3);
    return color * target;
}

/*
    Vibrance lifts muted colours and leaves already-saturated ones alone, so the
    sky and the paint on a train gain depth without the reds turning to neon.
*/
vec3 applyVibrance(vec3 color, float amount) {
    float l = luminance(color);
    float currentSat = maxOf(color) - minOf(color);
    float weight = 1.0 - saturate(currentSat);
    return mix(vec3(l), color, 1.0 + (amount - 1.0) * weight);
}

vec3 colorGrade(vec3 color) {
    color = whiteBalance(color, WHITE_BALANCE);
    color = applyVibrance(color, VIBRANCE);
    color = mix(vec3(luminance(color)), color, SATURATION);
    color = (color - 0.5) * CONTRAST + 0.5;
    return max(color, vec3(0.0));
}

#endif
