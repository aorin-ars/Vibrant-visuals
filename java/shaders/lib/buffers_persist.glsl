#ifndef LIB_BUFFERS_PERSIST_GLSL
#define LIB_BUFFERS_PERSIST_GLSL

/*
    Buffers that must survive from one frame to the next.

    Clearing either of these would break the effect that depends on it: the
    exposure would jump to its target instantly every frame, and temporal
    anti-aliasing would have no history to accumulate into.  Only composite and
    deferred programs may declare these, which is why they live in their own
    header instead of in consts.glsl.
*/

const bool colortex4Clear = false;   /* auto exposure */
const bool colortex5Clear = false;   /* temporal AA history */

#endif
