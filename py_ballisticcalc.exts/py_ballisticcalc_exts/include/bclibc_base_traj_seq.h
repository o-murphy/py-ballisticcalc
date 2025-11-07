#ifndef BCLIBC_BASE_TRAJ_SEQ_H
#define BCLIBC_BASE_TRAJ_SEQ_H

#include <stddef.h>    // Required for size_t
#include <sys/types.h> // Required for ssize_t

#include "bclibc_bclib.h"

// --- START CROSS-PLATFORM FIX ---
// The manylinux build environment failed due to redefinition.
// We only need to manually define ssize_t for MSVC (Windows).
// For other platforms, we rely on the standard headers above.
#if defined(_MSC_VER)
// Robust definition for MSVC based on architecture
#if defined(_WIN64)
typedef __int64 ssize_t;
#else
typedef long ssize_t;
#endif
#endif
// --- END CROSS-PLATFORM FIX ---

#define BCLIBC_BASE_TRAJ_SEQ_INTERP_KEY_ACTIVE_COUNT 8

/**
 * Simple C struct for trajectory data points used in the contiguous buffer.
 */
typedef struct
{
    double time; /* Time of the data point */
    double px;   /* Position x-coordinate */
    double py;   /* Position y-coordinate */
    double pz;   /* Position z-coordinate */
    double vx;   /* Velocity x-component */
    double vy;   /* Velocity y-component */
    double vz;   /* Velocity z-component */
    double mach; /* Mach number */
} BCLIBC_BaseTraj;

/**
 * Internal view structure for a sequence (buffer) of BCLIBC_BaseTraj points.
 */
typedef struct
{
    BCLIBC_BaseTraj *buffer;
    size_t length;
    size_t capacity;
} BCLIBC_BaseTrajSeq;

#ifdef __cplusplus
extern "C"
{
#endif

    void BCLIBC_BaseTrajSeq_init(BCLIBC_BaseTrajSeq *seq);
    void BCLIBC_BaseTrajSeq_release(BCLIBC_BaseTrajSeq *seq);

    /**
     * @brief Appends a new element to the end of the sequence.
     * @param seq Pointer to the sequence structure.
     * @return int 0 on success, -1 on memory allocation error or NULL pointer.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_append(BCLIBC_BaseTrajSeq *seq, double time, double px, double py, double pz, double vx, double vy, double vz, double mach);

    /**
     * @brief Checks and ensures the minimum buffer capacity.
     *
     * @param seq Pointer to the sequence structure.
     * @param min_capacity The minimum required capacity.
     * @return int 0 on success, -1 on memory allocation error.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_ensureCapacity(BCLIBC_BaseTrajSeq *seq, size_t min_capacity);

    ssize_t BCLIBC_BaseTrajSeq_len(const BCLIBC_BaseTrajSeq *seq);

    /**
     * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
     *
     * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
     * @return 1 on success, 0 on failure.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_interpolateAt(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, BCLIBC_BaseTrajData *out);
    BCLIBC_BaseTraj *BCLIBC_BaseTrajSeq_getRawItem(const BCLIBC_BaseTrajSeq *seq, ssize_t idx);
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAtSlantHeight(const BCLIBC_BaseTrajSeq *seq, double look_angle_rad, double value, BCLIBC_BaseTrajData *out);
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getItem(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajData *out);
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAt(const BCLIBC_BaseTrajSeq *seq, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, double start_from_time, BCLIBC_BaseTrajData *out);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_BASE_TRAJ_SEQ_H
