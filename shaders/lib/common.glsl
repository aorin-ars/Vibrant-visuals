#ifndef LIB_COMMON_GLSL
#define LIB_COMMON_GLSL

#include "/lib/consts.glsl"

const float PI      = 3.14159265358979323846;
const float TAU     = 6.28318530717958647692;
const float RCP_PI  = 0.31830988618379067154;
const float HALF_PI = 1.57079632679489661923;

/* Tangent of the sun's angular radius - the reason shadows are not razor sharp. */
const float SUN_ANGULAR_TAN = 0.00465;

float saturate(float x) { return clamp(x, 0.0, 1.0); }
vec2  saturate(vec2 x)  { return clamp(x, 0.0, 1.0); }
vec3  saturate(vec3 x)  { return clamp(x, 0.0, 1.0); }
vec4  saturate(vec4 x)  { return clamp(x, 0.0, 1.0); }

float sqr(float x) { return x * x; }
vec3  sqr(vec3 x)  { return x * x; }

float maxOf(vec2 v) { return max(v.x, v.y); }
float maxOf(vec3 v) { return max(v.x, max(v.y, v.z)); }
float minOf(vec3 v) { return min(v.x, min(v.y, v.z)); }

float luminance(vec3 color) { return dot(color, vec3(0.2126, 0.7152, 0.0722)); }

/* Cheap sRGB <-> linear pair; accurate enough for albedo and far cheaper than pow(). */
vec3 srgbToLinear(vec3 c) {
    return c * (c * (c * 0.305306011 + 0.682171111) + 0.012522878);
}
vec3 linearToSrgb(vec3 c) {
    return max(1.055 * pow(max(c, vec3(0.0)), vec3(0.4166666667)) - 0.055, vec3(0.0));
}

float remap(float x, float lo, float hi) {
    return saturate((x - lo) / max(hi - lo, 1e-6));
}

/* Smooth, always-positive falloff used all over the atmosphere code. */
float expFalloff(float x, float k) { return exp2(-x * k * 1.442695); }

vec3 projectOrtho(mat4 m, vec3 v) {
    return vec3(m[0][0], m[1][1], m[2][2]) * v + m[3].xyz;
}

vec3 projectPerspective(mat4 m, vec3 v) {
    vec4 p = m * vec4(v, 1.0);
    return p.xyz / p.w;
}

/* Octahedral normal encoding: 3 floats of direction into 2 stable channels. */
vec2 encodeNormal(vec3 n) {
    n /= max(abs(n.x) + abs(n.y) + abs(n.z), 1e-6);
    vec2 e = n.xy;
    if (n.z < 0.0) {
        e = (1.0 - abs(n.yx)) * vec2(n.x >= 0.0 ? 1.0 : -1.0, n.y >= 0.0 ? 1.0 : -1.0);
    }
    return e * 0.5 + 0.5;
}

vec3 decodeNormal(vec2 e) {
    vec2 f = e * 2.0 - 1.0;
    vec3 n = vec3(f, 1.0 - abs(f.x) - abs(f.y));
    float t = max(-n.z, 0.0);
    n.x += n.x >= 0.0 ? -t : t;
    n.y += n.y >= 0.0 ? -t : t;
    return normalize(n);
}

float encodeMaterial(float id) { return id * MAT_ENCODE; }
float decodeMaterial(float v)  { return floor(v * 255.0 + 0.5); }

#endif
