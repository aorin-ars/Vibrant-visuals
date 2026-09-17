#ifndef PROGRAM_FULLSCREEN_VERTEX_GLSL
#define PROGRAM_FULLSCREEN_VERTEX_GLSL

/* Vertex stage shared by every deferred, composite and final program. */

out vec2 texcoord;

void main() {
    gl_Position = ftransform();
    texcoord = gl_MultiTexCoord0.xy;
}

#endif
