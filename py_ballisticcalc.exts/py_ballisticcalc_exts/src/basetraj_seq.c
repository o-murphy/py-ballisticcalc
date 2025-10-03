#include <stddef.h>
#include <math.h>
#include <sys/types.h> // For ssize_t
#include "basetraj_seq.h"
#include "interp.h"

/**
 * Retrieves a specific double value from a BaseTrajC struct using an InterpKey.
 * This function is defined as static inline for performance.
 *
 * @param p A pointer to the BaseTrajC struct.
 * @param key_kind The InterpKey indicating which value to retrieve.
 * @return The corresponding double value, or 0.0 if the key is unrecognized.
 */
double _key_val_from_kind_buf(const BaseTrajC* p, int key_kind) {
    // Note: In C, accessing a struct member via a pointer uses '->' instead of '.'
    switch (key_kind) {
        case KEY_TIME:
            return p->time;
        case KEY_MACH:
            return p->mach;
        case KEY_POS_X:
            return p->px;
        case KEY_POS_Y:
            return p->py;
        case KEY_POS_Z:
            return p->pz;
        case KEY_VEL_X:
            return p->vx;
        case KEY_VEL_Y:
            return p->vy;
        case KEY_VEL_Z:
            return p->vz;
        default:
            return 0.0;
    }
}

double _slant_val_buf(const BaseTrajC* p, double ca, double sa) {
    /* Computes the slant_height of a trajectory point 'p' given cosine 'ca' and sine 'sa' of look_angle. */
    return p->py * ca - p->px * sa;
}

// Rewritten C function
ssize_t _bisect_center_idx_buf(
    const BaseTrajC* buf,
    size_t length,
    int key_kind,
    double key_value
) {
    // Cast size_t to ssize_t for consistency with Cython/Python indexing
    ssize_t n = (ssize_t)length;

    // Check for minimum required points (n < 3 is impossible for a center index)
    if (n < 3) {
        return (ssize_t)(-1);
    }

    // Get the first and last key values
    // Note: The C version simplifies pointer arithmetic compared to the Cython original
    double v0 = _key_val_from_kind_buf(&buf[0], key_kind);
    double vN = _key_val_from_kind_buf(&buf[n - 1], key_kind);

    // Determine sort order
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;
    ssize_t mid;
    double vm;

    // Binary search loop
    while (lo < hi) {
        // mid = lo + (hi - lo) / 2; (avoids overflow, same as original (hi - lo) >> 1)
        mid = lo + ((hi - lo) >> 1);

        // Get value at midpoint
        vm = _key_val_from_kind_buf(&buf[mid], key_kind);

        if (increasing) {
            if (vm < key_value) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        } else { // decreasing
            if (vm > key_value) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
    }

    // The result lo is the index of the first element >= key_value (if increasing)
    // or the first element <= key_value (if decreasing).
    // The result should be constrained to [1, n-2] to provide a center point
    // for a 3-point interpolation (p0, p1, p2).

    // Clamp lo to be at least 1 (to ensure p0 exists)
    if (lo < 1) {
        return (ssize_t)1;
    }
    // Clamp lo to be at most n - 2 (to ensure p2 exists)
    if (lo > n - 2) {
        return n - 2;
    }

    return lo;
}

// Implementation of the function declared in basetraj_seq.h
ssize_t _bisect_center_idx_slant_buf(
    const BaseTrajC* buf,
    size_t length,
    double ca,
    double sa,
    double value
) {
    // Cast size_t to ssize_t for bounds checking and signed return value
    ssize_t n = (ssize_t)length;

    // Check for minimum required points (p0, p1, p2 needed)
    if (n < 3) {
        return (ssize_t)(-1);
    }

    // Get the first and last slant values using array indexing
    double v0 = _slant_val_buf(&buf[0], ca, sa);
    double vN = _slant_val_buf(&buf[n - 1], ca, sa);

    // Determine sort order
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;
    ssize_t mid;
    double vm;

    // Binary search loop
    while (lo < hi) {
        // mid = lo + (hi - lo) / 2; (safer way to calculate midpoint)
        mid = lo + ((hi - lo) >> 1);

        // Get value at midpoint
        vm = _slant_val_buf(&buf[mid], ca, sa);

        if (increasing) {
            if (vm < value) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        } else { // decreasing
            if (vm > value) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
    }

    // Clamp the result to be a valid center index [1, n-2]
    if (lo < 1) {
        return (ssize_t)1;
    }
    if (lo > n - 2) {
        return n - 2;
    }

    return lo;
}

/**
 * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
 *
 * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
 * This is the C-equivalent of the Cython function _interpolate_raw.
 */
int _interpolate_raw(_CBaseTrajSeq_cview* seq, ssize_t idx, int key_kind, double key_value, BaseTrajC* out) {
    // Cast Cython's size_t to C's ssize_t for bounds checking
    BaseTrajC* buffer = seq->_buffer;
    ssize_t plength = (ssize_t)seq->_length;
    BaseTrajC *p0;
    BaseTrajC *p1;
    BaseTrajC *p2;
    double ox0, ox1, ox2;
    double x = key_value;
    double time, px, py, pz, vx, vy, vz, mach;

    // Handle negative index (Cython style) and check bounds
    if (idx < 0) {
        idx += plength;
    }
    if (idx <= 0 || idx >= plength - 1) {
        return 0;
    }

    // Use standard C array indexing instead of complex pointer arithmetic
    p0 = &buffer[idx - 1];
    p1 = &buffer[idx];
    p2 = &buffer[idx + 1];

    // Read x values from buffer points using switch/case
    switch (key_kind) {
        case KEY_TIME:
            ox0 = p0->time; ox1 = p1->time; ox2 = p2->time;
            break;
        case KEY_MACH:
            ox0 = p0->mach; ox1 = p1->mach; ox2 = p2->mach;
            break;
        case KEY_POS_X:
            ox0 = p0->px; ox1 = p1->px; ox2 = p2->px;
            break;
        case KEY_POS_Y:
            ox0 = p0->py; ox1 = p1->py; ox2 = p2->py;
            break;
        case KEY_POS_Z:
            ox0 = p0->pz; ox1 = p1->pz; ox2 = p2->pz;
            break;
        case KEY_VEL_X:
            ox0 = p0->vx; ox1 = p1->vx; ox2 = p2->vx;
            break;
        case KEY_VEL_Y:
            ox0 = p0->vy; ox1 = p1->vy; ox2 = p2->vy;
            break;
        case KEY_VEL_Z:
            ox0 = p0->vz; ox1 = p1->vz; ox2 = p2->vz;
            break;
        default:
            // If key_kind is not recognized, interpolation is impossible.
            return 0;
    }

    // Check for duplicate x values (zero division risk in PCHIP)
    if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2) {
        return 0;
    }

    // Interpolate all components using the external C function _interpolate_3_pt
    if (key_kind == KEY_TIME) {
        time = x;
    } else {
        time = _interpolate_3_pt(x, ox0, ox1, ox2, p0->time, p1->time, p2->time);
    }

    px = _interpolate_3_pt(x, ox0, ox1, ox2, p0->px, p1->px, p2->px);
    py = _interpolate_3_pt(x, ox0, ox1, ox2, p0->py, p1->py, p2->py);
    pz = _interpolate_3_pt(x, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz);
    vx = _interpolate_3_pt(x, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx);
    vy = _interpolate_3_pt(x, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy);
    vz = _interpolate_3_pt(x, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz);

    if (key_kind == KEY_MACH) {
        mach = x;
    } else {
        mach = _interpolate_3_pt(x, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);
    }

    // Write results to the output BaseTrajC struct (use -> for pointer access)
    out->time = time;
    out->px = px; out->py = py; out->pz = pz;
    out->vx = vx; out->vy = vy; out->vz = vz;
    out->mach = mach;
    return 1;
}