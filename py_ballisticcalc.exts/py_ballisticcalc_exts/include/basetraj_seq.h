#ifndef BASETRAJ_SEQ_H
#define BASETRAJ_SEQ_H

#include <stddef.h>
#include <sys/types.h> // For ssize_t


// --- START CROSS-PLATFORM FIX ---
// MSVC (Windows) often lacks a definition for ssize_t.
#if defined(_MSC_VER)
    // On Windows, define ssize_t to be the signed equivalent of size_t.
    // For 64-bit builds, this is typically a signed 64-bit integer.
    // We use __int64 here, as it's a Microsoft-specific type guaranteed to be 64-bit.
    // If you are certain your build environment is always 64-bit, this is fine.
    // A more generic approach is often used:
    // typedef long ssize_t; // For compatibility if sizes are generally 32-bit or less

    // A robust, modern definition for MSVC:
    #if defined(_WIN64)
        typedef __int64 ssize_t;
    #else
        typedef long ssize_t;
    #endif

#elif !defined(ssize_t)
    // Fallback for non-MSVC, non-POSIX systems if sys/types.h failed
    typedef long ssize_t; 
#endif
// --- END CROSS-PLATFORM FIX ---


/**
 * Simple C struct for trajectory data points used in the contiguous buffer.
 */
typedef struct {
    double time;  /* Time of the data point */
    double px;    /* Position x-coordinate */
    double py;    /* Position y-coordinate */
    double pz;    /* Position z-coordinate */
    double vx;    /* Velocity x-component */
    double vy;    /* Velocity y-component */
    double vz;    /* Velocity z-component */
    double mach;  /* Mach number */
} BaseTrajC;

/**
 * Keys used to look up specific values within a BaseTrajC struct.
 */
typedef enum {
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
 * Internal view structure for a sequence (buffer) of BaseTrajC points.
 */
typedef struct {
    BaseTrajC* _buffer;
    size_t _length;
    size_t _capacity;
} _CBaseTrajSeq_cview;

/**
 * Retrieves a specific double value from a BaseTrajC struct using an InterpKey.
 * This function is defined as static inline for performance.
 *
 * @param p A pointer to the BaseTrajC struct.
 * @param key_kind The InterpKey indicating which value to retrieve.
 * @return The corresponding double value, or 0.0 if the key is unrecognized.
 */
double _key_val_from_kind_buf(const BaseTrajC* p, int key_kind);

double _slant_val_buf(const BaseTrajC* p, double ca, double sa);

// Rewritten C function
ssize_t _bisect_center_idx_buf(
    const BaseTrajC* buf,
    size_t length,
    int key_kind,
    double key_value
);

// Implementation of the function declared in basetraj_seq.h
ssize_t _bisect_center_idx_slant_buf(
    const BaseTrajC* buf,
    size_t length,
    double ca,
    double sa,
    double value
);

/**
 * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
 *
 * Uses monotone-preserving PCHIP with Hermite evaluation.
 * @return 1 on success, 0 on failure.
 */
int _interpolate_raw(_CBaseTrajSeq_cview* seq, ssize_t idx, int key_kind, double key_value, BaseTrajC* out);


#endif /* BASETRAJ_SEQ_H */
