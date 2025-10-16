#ifndef BASETRAJ_SEQ_H
#define BASETRAJ_SEQ_H

#include <stddef.h>    // Required for size_t
#include <sys/types.h> // Required for ssize_t

#include "bclib.h"

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
} BaseTraj_t;

/**
 * Keys used to look up specific values within a BaseTraj_t struct.
 */
typedef enum
{
    KEY_TIME,
    KEY_MACH,
    KEY_POS_X,
    KEY_POS_Y,
    KEY_POS_Z,
    KEY_VEL_X,
    KEY_VEL_Y,
    KEY_VEL_Z
} InterpKey;

/**
 * Internal view structure for a sequence (buffer) of BaseTraj_t points.
 */
typedef struct
{
    BaseTraj_t *buffer;
    size_t length;
    size_t capacity;
} BaseTrajSeq_t;

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * Retrieves a specific double value from a BaseTraj_t struct using an InterpKey.
     *
     * @param p A pointer to the BaseTraj_t struct.
     * @param key_kind The InterpKey indicating which value to retrieve.
     * @return The corresponding double value, or 0.0 if the key is unrecognized.
     */
    double BaseTraj_t_key_val_from_kind_buf(const BaseTraj_t *p, InterpKey key_kind);

    double BaseTraj_t_slant_val_buf(const BaseTraj_t *p, double ca, double sa);

    BaseTrajSeq_t *BaseTrajSeq_t_create();
    void BaseTrajSeq_t_destroy(BaseTrajSeq_t *seq);

    /**
     * @brief Appends a new element to the end of the sequence.
     * @param seq Pointer to the sequence structure.
     * @return int 0 on success, -1 on memory allocation error or NULL pointer.
     */
    int BaseTrajSeq_t_append(BaseTrajSeq_t *seq, double time, double px, double py, double pz, double vx, double vy, double vz, double mach);

    /**
     * @brief Checks and ensures the minimum buffer capacity.
     *
     * @param seq Pointer to the sequence structure.
     * @param min_capacity The minimum required capacity.
     * @return int 0 on success, -1 on memory allocation error.
     */
    int BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity);

    ssize_t BaseTrajSeq_t_len(const BaseTrajSeq_t *seq);

    /**
     * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
     *
     * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
     * @return 1 on success, 0 on failure.
     */
    int BaseTrajSeq_t_interpolate_raw(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTraj_t *out);

    BaseTraj_t *BaseTrajSeq_t_get_item(const BaseTrajSeq_t *seq, ssize_t idx);
    ssize_t BaseTrajSeq_t_bisect_center_idx_buf(const BaseTrajSeq_t *seq, InterpKey key_kind, double key_value);
    ssize_t BaseTrajSeq_t_bisect_center_idx_slant_buf(const BaseTrajSeq_t *seq, double ca, double sa, double value);

#ifdef __cplusplus
}
#endif

#endif /* BASETRAJ_SEQ_H */
