/*
 * What the C ABI of bclibc (bclibc_ffi.h) lacks and the C++ API has (BCLIBC_BaseTrajSeq, BCLIBC_BaseTrajData::interpolate),
 * written as the same kind of C functions, so that a binding does not have to: a growable buffer of base trajectory points,
 * and the three-point interpolation of BCLIBCFFI_BaseTrajData, alone and over the points around an index.
 *
 * `key` is BCLIBCFFI_BaseTrajInterpKey. Errors are filled the way bclibc_ffi.h does: BCLIBCFFI_ERR_OUT_OF_RANGE for an index
 * outside the buffer, BCLIBCFFI_ERR_GENERIC for a degenerate segment (two equal keys) or no memory. Meant to move into bclibc.
 */
#ifndef BCLIBC_FFI_EXT_H
#define BCLIBC_FFI_EXT_H

#include "bclibc/ffi/bclibc_ffi.h"

#ifdef __cplusplus
extern "C"
{
#endif

    /** A growing array of points (what BCLIBC_BaseTrajSeq keeps in a std::vector). Zero-initialised is empty. */
    typedef struct BCLIBCFFI_BaseTrajBuf
    {
        BCLIBCFFI_BaseTrajData *data;
        int32_t count;
        int32_t capacity;
    } BCLIBCFFI_BaseTrajBuf;

    /** Releases the memory; the buffer is empty again. */
    BCLIBC_API void BCLIBCFFI_base_traj_buf_free(BCLIBCFFI_BaseTrajBuf *buf);

    /** Appends a copy of *item; the capacity doubles when full. */
    BCLIBC_API int32_t BCLIBCFFI_base_traj_buf_append(BCLIBCFFI_BaseTrajBuf *buf, const BCLIBCFFI_BaseTrajData *item, BCLIBCFFI_Error *err);

    /**
     * The point where `key` is `value`, through three points (BCLIBC_BaseTrajData::interpolate): every field is
     * interpolated with PCHIP, except time and mach, which are set to `value` when they are the key.
     */
    BCLIBC_API int32_t BCLIBCFFI_base_traj_interpolate(
        int32_t key,
        double value,
        const BCLIBCFFI_BaseTrajData *p0,
        const BCLIBCFFI_BaseTrajData *p1,
        const BCLIBCFFI_BaseTrajData *p2,
        BCLIBCFFI_BaseTrajData *out,
        BCLIBCFFI_Error *err);

    /**
     * The same through the points idx-1, idx, idx+1 of `steps` (BCLIBC_BaseTrajSeq::interpolate_at). A negative idx counts
     * from the end; the valid range is [1, count-2].
     */
    BCLIBC_API int32_t BCLIBCFFI_base_traj_interpolate_at(
        const BCLIBCFFI_BaseTrajData *steps,
        int32_t count,
        int64_t idx,
        int32_t key,
        double value,
        BCLIBCFFI_BaseTrajData *out,
        BCLIBCFFI_Error *err);

#ifdef __cplusplus
} // extern "C"
#endif

#endif
