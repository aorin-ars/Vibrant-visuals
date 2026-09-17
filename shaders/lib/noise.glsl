#ifndef LIB_NOISE_GLSL
#define LIB_NOISE_GLSL

#include "/lib/common.glsl"

float hash12(vec2 p) {
    vec3 p3 = fract(p.xyx * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 hash22(vec2 p) {
    vec3 p3 = fract(p.xyx * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

float valueNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = hash12(i);
    float b = hash12(i + vec2(1.0, 0.0));
    float c = hash12(i + vec2(0.0, 1.0));
    float d = hash12(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p, int octaves) {
    float sum = 0.0;
    float amp = 0.5;
    for (int i = 0; i < octaves; i++) {
        sum += valueNoise(p) * amp;
        p = p * 2.03 + 17.3;
        amp *= 0.5;
    }
    return sum;
}

/* Ordered dither, used to break up banding without adding temporal noise. */
float bayer2(vec2 a) {
    a = floor(a);
    return fract(a.x * 0.5 + a.y * a.y * 0.75);
}
#define bayer4(a)  (bayer2(0.5 * (a)) * 0.25 + bayer2(a))
#define bayer8(a)  (bayer4(0.5 * (a)) * 0.25 + bayer2(a))
#define bayer16(a) (bayer8(0.5 * (a)) * 0.25 + bayer2(a))

float interleavedGradientNoise(vec2 pixel) {
    return fract(52.9829189 * fract(0.06711056 * pixel.x + 0.00583715 * pixel.y));
}

/*
    Rotation angle for the sampling disks.

    With TAA on, the pattern advances every frame and the accumulation buffer
    averages it away.  With TAA off it stays fixed per pixel, so soft shadows
    read as a stable dither instead of boiling noise.
*/
float sampleRotation(vec2 pixel) {
#ifdef TAA
    return interleavedGradientNoise(pixel + 5.588238 * float(frameCounter % 64)) * TAU;
#else
    return interleavedGradientNoise(pixel) * TAU;
#endif
}

/* Vogel disk - even coverage of a unit disk with no lookup table. */
vec2 vogelDisk(int index, int count, float rotation) {
    float radius = sqrt((float(index) + 0.5) / float(count));
    float theta  = float(index) * 2.39996323 + rotation;
    return vec2(cos(theta), sin(theta)) * radius;
}

vec3 vogelSphere(int index, int count, float rotation) {
    float z = 1.0 - (2.0 * float(index) + 1.0) / float(count);
    float r = sqrt(max(1.0 - z * z, 0.0));
    float theta = float(index) * 2.39996323 + rotation;
    return vec3(cos(theta) * r, sin(theta) * r, z);
}

#endif
