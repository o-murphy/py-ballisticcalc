#include <math.h>
#include <stdlib.h> // Required for calloc, malloc, free
#include <string.h> // Required for memcpy
#include "interp.h"
#include "bclib.h"
#include "base_traj_seq.h"

/**
 * Retrieves a specific double value from a BaseTraj_t struct using an InterpKey.
 *
 * @param p A pointer to the BaseTraj_t struct.
 * @param key_kind The InterpKey indicating which value to retrieve.
 * @return The corresponding double value, or 0.0 if the key is unrecognized.
 */
double BaseTraj_t_key_val_from_kind_buf(const BaseTraj_t *p, InterpKey key_kind)
{
    // Note: In C, accessing a struct member via a pointer uses '->' instead of '.'
    switch (key_kind)
    {
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

double BaseTraj_t_slant_val_buf(const BaseTraj_t *p, double ca, double sa)
{
    /* Computes the slant_height of a trajectory point 'p' given cosine 'ca' and sine 'sa' of look_angle. */
    if (p == NULL)
    {
        return NAN;
    }
    return p->py * ca - p->px * sa;
}

/**
 * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
 *
 * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
 * @return 1 on success, 0 on failure.
 */
int BaseTrajSeq_t_interpolate_raw(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTraj_t *out)
{
    // Cast Cython's size_t to C's ssize_t for bounds checking
    BaseTraj_t *buffer = seq->buffer;
    ssize_t length = seq->length;
    BaseTraj_t *p0;
    BaseTraj_t *p1;
    BaseTraj_t *p2;
    double ox0, ox1, ox2;
    double x = key_value;
    double time, px, py, pz, vx, vy, vz, mach;

    // Handle negative index
    if (idx < 0)
    {
        idx += length;
    }

    // Check if we have valid points on both sides
    if (idx < 1 || idx >= length - 1)
    {
        return -1;
    }

    // Use standard C array indexing instead of complex pointer arithmetic
    p0 = &buffer[idx - 1];
    p1 = &buffer[idx];
    p2 = &buffer[idx + 1];

    // Read x values from buffer points using switch/case
    switch (key_kind)
    {
    case KEY_TIME:
        ox0 = p0->time;
        ox1 = p1->time;
        ox2 = p2->time;
        break;
    case KEY_MACH:
        ox0 = p0->mach;
        ox1 = p1->mach;
        ox2 = p2->mach;
        break;
    case KEY_POS_X:
        ox0 = p0->px;
        ox1 = p1->px;
        ox2 = p2->px;
        break;
    case KEY_POS_Y:
        ox0 = p0->py;
        ox1 = p1->py;
        ox2 = p2->py;
        break;
    case KEY_POS_Z:
        ox0 = p0->pz;
        ox1 = p1->pz;
        ox2 = p2->pz;
        break;
    case KEY_VEL_X:
        ox0 = p0->vx;
        ox1 = p1->vx;
        ox2 = p2->vx;
        break;
    case KEY_VEL_Y:
        ox0 = p0->vy;
        ox1 = p1->vy;
        ox2 = p2->vy;
        break;
    case KEY_VEL_Z:
        ox0 = p0->vz;
        ox1 = p1->vz;
        ox2 = p2->vz;
        break;
    default:
        // If key_kind is not recognized, interpolation is impossible.
        return -1;
    }

    // Check for duplicate x values (zero division risk in PCHIP)
    if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
    {
        return -1;
    }

    // Interpolate all components using the external C function interpolate_3_pt
    if (key_kind == KEY_TIME)
    {
        time = x;
    }
    else
    {
        time = interpolate_3_pt(x, ox0, ox1, ox2, p0->time, p1->time, p2->time);
    }

    px = interpolate_3_pt(x, ox0, ox1, ox2, p0->px, p1->px, p2->px);
    py = interpolate_3_pt(x, ox0, ox1, ox2, p0->py, p1->py, p2->py);
    pz = interpolate_3_pt(x, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz);
    vx = interpolate_3_pt(x, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx);
    vy = interpolate_3_pt(x, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy);
    vz = interpolate_3_pt(x, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz);

    if (key_kind == KEY_MACH)
    {
        mach = x;
    }
    else
    {
        mach = interpolate_3_pt(x, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);
    }

    // Write results to the output BaseTraj_t struct (use -> for pointer access)
    out->time = time;
    out->px = px;
    out->py = py;
    out->pz = pz;
    out->vx = vx;
    out->vy = vy;
    out->vz = vz;
    out->mach = mach;
    return 0;
}

BaseTrajSeq_t *BaseTrajSeq_t_create()
{
    BaseTrajSeq_t *ptr = (BaseTrajSeq_t *)calloc(1, sizeof(BaseTrajSeq_t));
    if (ptr == NULL)
    {
        // Optionally log error: fprintf(stderr, "Failed to allocate BaseTrajSeq_t\n");
        return NULL;
    }
    return ptr;
}

void BaseTrajSeq_t_destroy(BaseTrajSeq_t *seq)
{
    if (seq != NULL)
    {
        if (seq->buffer != NULL)
        {
            free(seq->buffer);
            seq->buffer = NULL;
        }
        free(seq);
    }
    return;
}

ssize_t BaseTrajSeq_t_len(const BaseTrajSeq_t *seq)
{
    if (seq != NULL)
    {
        return (ssize_t)seq->length;
    }
    return (ssize_t)-1;
}

BaseTraj_t *BaseTrajSeq_t_get_item(const BaseTrajSeq_t *seq, ssize_t idx)
{
    if (seq == NULL)
    {
        return NULL;
    }

    ssize_t len = (ssize_t)seq->length;
    if (len <= 0)
    {
        return NULL;
    }
    if (idx < 0)
    {
        idx += len;
    }
    if (idx < 0 || idx >= len)
    {
        return NULL;
    }
    return seq->buffer + idx;
}

/**
 * @brief Checks and ensures the minimum buffer capacity.
 *
 * @param seq Pointer to the sequence structure.
 * @param min_capacity The minimum required capacity.
 * @return int 0 on success, -1 on memory allocation error.
 */
int BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity)
{
    if (seq == NULL)
    {
        return -1;
    }

    size_t new_capacity;
    BaseTraj_t *new_buffer;
    size_t bytes_copy;

    if (min_capacity <= seq->capacity)
    {
        return 0;
    }

    if (seq->capacity > 0)
    {
        new_capacity = seq->capacity * 2;
    }
    else
    {
        new_capacity = 64;
    }

    if (new_capacity < min_capacity)
    {
        new_capacity = min_capacity;
    }

    new_buffer = (BaseTraj_t *)calloc(new_capacity, sizeof(BaseTraj_t));

    if (new_buffer == NULL)
    {
        return -1;
    }

    if (seq->length > 0)
    {
        bytes_copy = seq->length * sizeof(BaseTraj_t);
        memcpy(new_buffer, seq->buffer, bytes_copy);
    }
    free(seq->buffer);

    seq->buffer = new_buffer;
    seq->capacity = new_capacity;

    return 0;
}

/**
 * @brief Appends a new element to the end of the sequence.
 * @param seq Pointer to the sequence structure.
 * @return int 0 on success, -1 on memory allocation error or NULL pointer.
 */
int BaseTrajSeq_t_append(BaseTrajSeq_t *seq, double time, double px, double py, double pz, double vx, double vy, double vz, double mach)
{

    if (seq == NULL)
    {
        return -1;
    }

    if (BaseTrajSeq_t_ensure_capacity(seq, seq->length + 1) < 0)
    {
        return -1;
    }

    BaseTraj_t *entry_ptr = seq->buffer + seq->length;
    entry_ptr->time = time;
    entry_ptr->px = px;
    entry_ptr->py = py;
    entry_ptr->pz = pz;
    entry_ptr->vx = vx;
    entry_ptr->vy = vy;
    entry_ptr->vz = vz;
    entry_ptr->mach = mach;
    seq->length += 1;

    return 0;
}

ssize_t BaseTrajSeq_t_bisect_center_idx_buf(
    const BaseTrajSeq_t *seq,
    InterpKey key_kind,
    double key_value)
{
    if (seq == NULL)
    {
        return (ssize_t)(-1);
    }

    // Cast size_t to ssize_t for consistency with Cython/Python indexing
    ssize_t n = seq->length;
    BaseTraj_t *buf = seq->buffer;

    // Check for minimum required points (n < 3 is impossible for a center index)
    if (n < 3)
    {
        return (ssize_t)(-1);
    }

    // Get the first and last key values
    // Note: The C version simplifies pointer arithmetic compared to the Cython original
    double v0 = BaseTraj_t_key_val_from_kind_buf(&buf[0], key_kind);
    double vN = BaseTraj_t_key_val_from_kind_buf(&buf[n - 1], key_kind);

    // Determine sort order
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;
    ssize_t mid;
    double vm;

    // Binary search loop
    while (lo < hi)
    {
        // mid = lo + (hi - lo) / 2; (avoids overflow, same as original (hi - lo) >> 1)
        mid = lo + ((hi - lo) >> 1);

        // Get value at midpoint
        vm = BaseTraj_t_key_val_from_kind_buf(&buf[mid], key_kind);

        if (increasing)
        {
            if (vm < key_value)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }
        else
        { // decreasing
            if (vm > key_value)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }
    }

    // The result lo is the index of the first element >= key_value (if increasing)
    // or the first element <= key_value (if decreasing).
    // The result should be constrained to [1, n-2] to provide a center point
    // for a 3-point interpolation (p0, p1, p2).

    // Clamp lo to be at least 1 (to ensure p0 exists)
    if (lo < 1)
    {
        return (ssize_t)1;
    }
    // Clamp lo to be at most n - 2 (to ensure p2 exists)
    if (lo > n - 2)
    {
        return n - 2;
    }

    return lo;
}

// Implementation of the function declared in base_traj_seq.h
ssize_t BaseTrajSeq_t_bisect_center_idx_slant_buf(
    const BaseTrajSeq_t *seq,
    double ca,
    double sa,
    double value)
{

    if (seq == NULL)
    {
        return (ssize_t)(-1);
    }

    // Cast size_t to ssize_t for bounds checking and signed return value
    ssize_t n = seq->length;
    BaseTraj_t *buf = seq->buffer;

    // Check for minimum required points (p0, p1, p2 needed)
    if (n < 3)
    {
        return (ssize_t)(-1);
    }

    // Get the first and last slant values using array indexing
    double v0 = BaseTraj_t_slant_val_buf(&buf[0], ca, sa);
    double vN = BaseTraj_t_slant_val_buf(&buf[n - 1], ca, sa);

    // Determine sort order
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;
    ssize_t mid;
    double vm;

    // Binary search loop
    while (lo < hi)
    {
        // mid = lo + (hi - lo) / 2; (safer way to calculate midpoint)
        mid = lo + ((hi - lo) >> 1);

        // Get value at midpoint
        vm = BaseTraj_t_slant_val_buf(&buf[mid], ca, sa);

        if (increasing)
        {
            if (vm < value)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }
        else
        { // decreasing
            if (vm > value)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }
    }

    // Clamp the result to be a valid center index [1, n-2]
    if (lo < 1)
    {
        return (ssize_t)1;
    }
    if (lo > n - 2)
    {
        return n - 2;
    }

    return lo;
}
