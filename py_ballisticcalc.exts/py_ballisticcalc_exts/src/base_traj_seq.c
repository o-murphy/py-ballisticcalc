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
static ErrorCode BaseTrajSeq_t_interpolate_raw(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTraj_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR; // Invalid input
    }

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
        C_LOG(LOG_LEVEL_ERROR, "Index out of bounds for interpolation.");
        return SEQUENCE_VALUE_ERROR;
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
        C_LOG(LOG_LEVEL_ERROR, "Unrecognized InterpKey.");
        return SEQUENCE_KEY_ERROR;
    }

    // Check for duplicate x values (zero division risk in PCHIP)
    if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
    {
        C_LOG(LOG_LEVEL_ERROR, "Duplicate x values detected; cannot interpolate.");
        return SEQUENCE_VALUE_ERROR;
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
    return NO_ERROR;
}

ErrorCode BaseTrajSeq_t_interpolate_at(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTrajData_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR; // Invalid input
    }
    BaseTraj_t raw_output;
    int err = BaseTrajSeq_t_interpolate_raw(seq, idx, key_kind, key_value, &raw_output);
    if (err != NO_ERROR)
    {
        return err; // SEQUENCE_INDEX_ERROR or SEQUENCE_VALUE_ERROR or SEQUENCE_KEY_ERROR
    }
    out->time = raw_output.time;
    out->position = (V3dT){raw_output.px, raw_output.py, raw_output.pz};
    out->velocity = (V3dT){raw_output.vx, raw_output.vy, raw_output.vz};
    out->mach = raw_output.mach;
    return NO_ERROR;
}

void BaseTrajSeq_t_init(BaseTrajSeq_t *seq)
{
    seq->buffer = NULL;
    seq->length = 0;
    seq->capacity = 0;
}

void BaseTrajSeq_t_release(BaseTrajSeq_t *seq)
{
    if (seq != NULL)
    {
        if (seq->buffer != NULL)
        {
            free(seq->buffer);
            seq->buffer = NULL;
        }
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

BaseTraj_t *BaseTrajSeq_t_get_raw_item(const BaseTrajSeq_t *seq, ssize_t idx)
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
ErrorCode BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity)
{
    if (seq == NULL)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    size_t new_capacity;
    BaseTraj_t *new_buffer;
    size_t bytes_copy;

    if (min_capacity <= seq->capacity)
    {
        C_LOG(LOG_LEVEL_DEBUG, "Current capacity sufficient (%zu >= %zu).", seq->capacity, min_capacity);
        return NO_ERROR;
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
        C_LOG(LOG_LEVEL_ERROR, "Memory (re)allocation failed.");
        return SEQUENCE_MEMORY_ERROR;
    }

    if (seq->length > 0)
    {
        bytes_copy = seq->length * sizeof(BaseTraj_t);
        memcpy(new_buffer, seq->buffer, bytes_copy);
    }
    free(seq->buffer);

    seq->buffer = new_buffer;
    seq->capacity = new_capacity;

    return NO_ERROR;
}

/**
 * @brief Appends a new element to the end of the sequence.
 * @param seq Pointer to the sequence structure.
 * @return int 0 on success, -1 on memory allocation error or NULL pointer.
 */
ErrorCode BaseTrajSeq_t_append(BaseTrajSeq_t *seq, double time, double px, double py, double pz, double vx, double vy, double vz, double mach)
{

    if (seq == NULL)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    ErrorCode err = BaseTrajSeq_t_ensure_capacity(seq, seq->length + 1);
    if (err != NO_ERROR)
    {
        return err;
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

    return NO_ERROR;
}

static ssize_t BaseTrajSeq_t_bisect_center_idx_buf(
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
static ssize_t BaseTrajSeq_t_bisect_center_idx_slant_buf(
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

ErrorCode BaseTrajSeq_t_get_at_slant_height(const BaseTrajSeq_t *seq, double look_angle_rad, double value, BaseTrajData_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }
    double ca = cos(look_angle_rad);
    double sa = sin(look_angle_rad);
    ssize_t n = seq->length;
    if (n < 3)
    {
        C_LOG(LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
        return SEQUENCE_VALUE_ERROR;
    }
    ssize_t center = BaseTrajSeq_t_bisect_center_idx_slant_buf(seq, ca, sa, value);
    // Use three consecutive points around center to perform
    // monotone PCHIP interpolation keyed on slant height
    BaseTraj_t *buf = seq->buffer;
    BaseTraj_t *p0 = &buf[center - 1];
    BaseTraj_t *p1 = &buf[center];
    BaseTraj_t *p2 = &buf[center + 1];

    double ox0 = BaseTraj_t_slant_val_buf(p0, ca, sa);
    double ox1 = BaseTraj_t_slant_val_buf(p1, ca, sa);
    double ox2 = BaseTraj_t_slant_val_buf(p2, ca, sa);

    out->time = interpolate_3_pt(value, ox0, ox1, ox2, p0->time, p1->time, p2->time);
    out->position = (V3dT){
        interpolate_3_pt(value, ox0, ox1, ox2, p0->px, p1->px, p2->px),
        interpolate_3_pt(value, ox0, ox1, ox2, p0->py, p1->py, p2->py),
        interpolate_3_pt(value, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz)};
    out->velocity = (V3dT){
        interpolate_3_pt(value, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx),
        interpolate_3_pt(value, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy),
        interpolate_3_pt(value, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz)};
    out->mach = interpolate_3_pt(value, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);

    return NO_ERROR;
}

ErrorCode BaseTrajSeq_t_get_item(const BaseTrajSeq_t *seq, ssize_t idx, BaseTrajData_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    BaseTraj_t *entry_ptr = BaseTrajSeq_t_get_raw_item(seq, idx);
    if (!entry_ptr)
    {
        C_LOG(LOG_LEVEL_ERROR, "Index out of bounds.");
        return SEQUENCE_INDEX_ERROR;
    }
    out->time = entry_ptr->time;
    out->position = (V3dT){
        entry_ptr->px,
        entry_ptr->py,
        entry_ptr->pz};
    out->velocity = (V3dT){
        entry_ptr->vx,
        entry_ptr->vy,
        entry_ptr->vz};
    out->mach = entry_ptr->mach;
    return NO_ERROR;
}

/**
 * @file base_traj_seq_helpers.c
 * @brief Helper functions for BaseTrajSeq interpolation and access.
 */

#include <math.h>
#include "base_traj_seq.h"

/**
 * @brief Interpolate at center index with logging.
 *
 * @param seq Pointer to the trajectory sequence.
 * @param idx Center index for interpolation.
 * @param key_kind Kind of interpolation key.
 * @param key_value Key value to interpolate at.
 * @param out Output trajectory data.
 * @return ErrorCode NO_ERROR if successful, otherwise error code.
 */
ErrorCode BaseTrajSeq_t_interpolate_at_center_with_log(
    const BaseTrajSeq_t *seq,
    ssize_t idx,
    InterpKey key_kind,
    double key_value,
    BaseTrajData_t *out)
{
    ErrorCode err = BaseTrajSeq_t_interpolate_at(seq, idx, key_kind, key_value, out);
    if (err != NO_ERROR)
    {
        C_LOG(LOG_LEVEL_ERROR, "Interpolation failed at center index %zd, error code: 0x%X", idx, err);
        return err; // SEQUENCE_INDEX_ERROR or SEQUENCE_VALUE_ERROR or SEQUENCE_KEY_ERROR
    }
    C_LOG(LOG_LEVEL_DEBUG, "Interpolation successful at center index %zd.", idx);
    return NO_ERROR;
}

/**
 * @brief Check if two double values are approximately equal.
 *
 * @param a First value.
 * @param b Second value.
 * @param epsilon Tolerance.
 * @return 1 if close, 0 otherwise.
 */
static int BaseTrajSeq_t_is_close(double a, double b, double epsilon)
{
    return fabs(a - b) < epsilon;
}

/**
 * @brief Get the key value of a BaseTraj element.
 *
 * @param elem Pointer to BaseTraj element.
 * @param key_kind Kind of key.
 * @return Value of the key.
 */
static double BaseTraj_t_key_val(const BaseTraj_t *elem, InterpKey key_kind)
{
    return BaseTraj_t_key_val_from_kind_buf(elem, key_kind);
}

/**
 * @brief Find the starting index for a given start time.
 *
 * @param buf Buffer of trajectory points.
 * @param n Length of buffer.
 * @param start_time Start time to search from.
 * @return Index of the first element with time >= start_time.
 */
static ssize_t BaseTrajSeq_t_find_start_index(const BaseTraj_t *buf, ssize_t n, double start_time)
{
    for (ssize_t i = 0; i < n; i++)
    {
        if (buf[i].time >= start_time)
        {
            return i;
        }
    }
    return n - 1;
}

/**
 * @brief Find the target index covering key_value for interpolation.
 *
 * @param buf Buffer of trajectory points.
 * @param n Length of buffer.
 * @param key_kind Kind of key.
 * @param key_value Key value to interpolate.
 * @param start_idx Index to start searching from.
 * @return Target index for interpolation, -1 if not found.
 */
static ssize_t BaseTrajSeq_t_find_target_index(const BaseTraj_t *buf, ssize_t n, InterpKey key_kind, double key_value, ssize_t start_idx)
{
    double a, b;

    // Forward search
    for (ssize_t i = start_idx; i < n - 1; i++)
    {
        a = BaseTraj_t_key_val(&buf[i], key_kind);
        b = BaseTraj_t_key_val(&buf[i + 1], key_kind);
        if ((a <= key_value && key_value <= b) || (b <= key_value && key_value <= a))
        {
            return i + 1;
        }
    }

    // Backward search
    for (ssize_t i = start_idx; i > 0; i--)
    {
        a = BaseTraj_t_key_val(&buf[i], key_kind);
        b = BaseTraj_t_key_val(&buf[i - 1], key_kind);
        if ((b <= key_value && key_value <= a) || (a <= key_value && key_value <= b))
        {
            return i;
        }
    }

    return -1; // not found
}

/**
 * @brief Try to get exact value at index, return NO_ERROR if successful.
 *
 * @param seq Pointer to trajectory sequence.
 * @param idx Index to check.
 * @param key_kind Kind of key.
 * @param key_value Key value to match.
 * @param out Output trajectory data.
 * @return NO_ERROR if exact match found, otherwise SEQUENCE_VALUE_ERROR.
 */
static ErrorCode BaseTrajSeq_t_try_get_exact(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTrajData_t *out)
{
    const BaseTraj_t *buf = seq->buffer;
    double epsilon = 1e-9;

    if (BaseTrajSeq_t_is_close(BaseTraj_t_key_val(&buf[idx], key_kind), key_value, epsilon))
    {
        ErrorCode err = BaseTrajSeq_t_get_item(seq, idx, out);
        if (err != NO_ERROR)
        {
            C_LOG(LOG_LEVEL_ERROR, "Failed to get item at index %zd.", idx);
            return SEQUENCE_INDEX_ERROR;
        }
        C_LOG(LOG_LEVEL_DEBUG, "Exact match found at index %zd.", idx);
        return NO_ERROR;
    }

    return SEQUENCE_VALUE_ERROR; // not an exact match
}

/**
 * @brief Get trajectory data at a given key value, with optional start time.
 *
 * @param seq Pointer to trajectory sequence.
 * @param key_kind Kind of key to search/interpolate.
 * @param key_value Key value to get.
 * @param start_from_time Optional start time (use -1 if not used).
 * @param out Output trajectory data.
 * @return ErrorCode NO_ERROR if successful, otherwise error code.
 */
ErrorCode BaseTrajSeq_t_get_at(
    const BaseTrajSeq_t *seq,
    InterpKey key_kind,
    double key_value,
    double start_from_time,
    BaseTrajData_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    ssize_t n = seq->length;
    if (n < 3)
    {
        C_LOG(LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
        return SEQUENCE_VALUE_ERROR;
    }

    BaseTraj_t *buf = seq->buffer;
    ssize_t target_idx = -1;

    // Search from start_from_time if provided
    if (start_from_time > 0.0 && key_kind != KEY_TIME)
    {
        ssize_t start_idx = BaseTrajSeq_t_find_start_index(buf, n, start_from_time);

        // Try exact match at start index
        ErrorCode exact_err = BaseTrajSeq_t_try_get_exact(seq, start_idx, key_kind, key_value, out);
        if (exact_err == NO_ERROR)
            return NO_ERROR;

        // Find target index for interpolation
        target_idx = BaseTrajSeq_t_find_target_index(buf, n, key_kind, key_value, start_idx);
    }

    // If not found, bisect the whole range
    if (target_idx < 0)
    {
        ssize_t center = BaseTrajSeq_t_bisect_center_idx_buf(seq, key_kind, key_value);
        if (center < 0)
        {
            C_LOG(LOG_LEVEL_ERROR, "Bisecting failed; not enough data points.");
            return SEQUENCE_VALUE_ERROR;
        }
        target_idx = center < n - 1 ? center : n - 2;
    }

    // Try exact match at target index
    ErrorCode exact_err = BaseTrajSeq_t_try_get_exact(seq, target_idx, key_kind, key_value, out);
    if (exact_err == NO_ERROR)
        return NO_ERROR;

    // Otherwise interpolate at center
    ssize_t center_idx = target_idx < n - 1 ? target_idx : n - 2;
    return BaseTrajSeq_t_interpolate_at_center_with_log(seq, center_idx, key_kind, key_value, out);
}
