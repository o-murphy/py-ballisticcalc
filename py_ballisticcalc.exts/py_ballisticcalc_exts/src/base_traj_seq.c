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
static double BaseTraj_t_key_val_from_kind_buf(const BaseTraj_t *p, InterpKey key_kind)
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

/**
 * Computes the slant height of a trajectory point relative to a given look angle.
 *
 * This function calculates the slant height using the formula:
 * slant_height = py * cos(angle) - px * sin(angle),
 * where `ca` and `sa` are the cosine and sine of the look angle, respectively.
 *
 * @param p Pointer to the BaseTraj_t trajectory point.
 * @param ca Cosine of the look angle.
 * @param sa Sine of the look angle.
 * @return The computed slant height, or NAN if the input pointer is NULL.
 */
static double BaseTraj_t_slant_val_buf(const BaseTraj_t *p, double ca, double sa)
{
    if (p == NULL)
    {
        return NAN;
    }
    return p->py * ca - p->px * sa;
}

/**
 * Interpolates a trajectory point at a specific index using its neighbors.
 *
 * This function performs 3-point monotone-preserving PCHIP interpolation
 * (Hermite evaluation) for all components of a trajectory point.
 *
 * @param seq Pointer to the BaseTrajSeq_t sequence.
 * @param idx Index around which interpolation is performed (uses idx-1, idx, idx+1).
 *            Negative indices are counted from the end of the buffer.
 * @param key_kind The key to interpolate along (e.g., time, position, velocity, Mach).
 * @param key_value The target value of the key to interpolate at.
 * @param out Pointer to a BaseTraj_t struct where the interpolated result will be stored.
 * @return NO_ERROR on success, or an ErrorCode on failure.
 */
static ErrorCode BaseTrajSeq_t_interpolate_raw(const BaseTrajSeq_t *seq, ssize_t idx, InterpKey key_kind, double key_value, BaseTraj_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    BaseTraj_t *buffer = seq->buffer;
    ssize_t length = seq->length;

    // Handle negative indices
    if (idx < 0)
        idx += length;

    // Ensure we have valid points on both sides
    if (idx < 1 || idx >= length - 1)
    {
        C_LOG(LOG_LEVEL_ERROR, "Index out of bounds for interpolation.");
        return SEQUENCE_VALUE_ERROR;
    }

    BaseTraj_t *p0 = &buffer[idx - 1];
    BaseTraj_t *p1 = &buffer[idx];
    BaseTraj_t *p2 = &buffer[idx + 1];

    // Get key values from the three points using helper
    double ox0 = BaseTraj_t_key_val_from_kind_buf(p0, key_kind);
    double ox1 = BaseTraj_t_key_val_from_kind_buf(p1, key_kind);
    double ox2 = BaseTraj_t_key_val_from_kind_buf(p2, key_kind);

    // Check for duplicate key values (would cause division by zero)
    if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
    {
        C_LOG(LOG_LEVEL_ERROR, "Duplicate key values detected; cannot interpolate.");
        return SEQUENCE_VALUE_ERROR;
    }

    // Interpolate all trajectory components
    double x = key_value;
    double time = (key_kind == KEY_TIME) ? x : interpolate_3_pt(x, ox0, ox1, ox2, p0->time, p1->time, p2->time);
    double px = interpolate_3_pt(x, ox0, ox1, ox2, p0->px, p1->px, p2->px);
    double py = interpolate_3_pt(x, ox0, ox1, ox2, p0->py, p1->py, p2->py);
    double pz = interpolate_3_pt(x, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz);
    double vx = interpolate_3_pt(x, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx);
    double vy = interpolate_3_pt(x, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy);
    double vz = interpolate_3_pt(x, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz);
    double mach = (key_kind == KEY_MACH) ? x : interpolate_3_pt(x, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);

    // Store results
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

/**
 * Initializes a BaseTrajSeq_t structure.
 *
 * Sets the buffer to NULL and length/capacity to 0.
 *
 * @param seq Pointer to the BaseTrajSeq_t structure to initialize.
 */
void BaseTrajSeq_t_init(BaseTrajSeq_t *seq)
{
    if (seq == NULL)
        return; // safe guard

    seq->buffer = NULL;
    seq->length = 0;
    seq->capacity = 0;
}

/**
 * Releases resources used by a BaseTrajSeq_t structure.
 *
 * Frees the internal buffer and resets all fields to default values.
 *
 * @param seq Pointer to the BaseTrajSeq_t structure to release.
 */
void BaseTrajSeq_t_release(BaseTrajSeq_t *seq)
{
    if (seq == NULL)
        return;

    free(seq->buffer); // safe even if buffer is NULL
    seq->buffer = NULL;
    seq->length = 0;
    seq->capacity = 0;
}

/**
 * Returns the length of the trajectory sequence.
 *
 * @param seq Pointer to the BaseTrajSeq_t structure.
 * @return The number of elements in the sequence, or -1 if seq is NULL.
 */
ssize_t BaseTrajSeq_t_len(const BaseTrajSeq_t *seq)
{
    return seq ? (ssize_t)seq->length : -1;
}

/**
 * Retrieve a pointer to a trajectory element at the given index.
 * Supports negative indices: -1 = last element, -2 = second-to-last, etc.
 *
 * @param seq Pointer to the trajectory sequence.
 * @param idx Index of the element to retrieve. Can be negative.
 * @return Pointer to the BaseTraj_t element, or NULL if index is out of bounds.
 */
inline BaseTraj_t *BaseTrajSeq_t_get_raw_item(const BaseTrajSeq_t *seq, ssize_t idx)
{
    if (!seq || !seq->buffer || seq->length == 0)
    {
        return NULL;
    }

    ssize_t len = (ssize_t)seq->length;

    // Adjust negative indices
    if (idx < 0)
    {
        idx += len;
    }

    // Out-of-bounds check
    if ((size_t)idx >= (size_t)len)
    {
        return NULL;
    }

    return &seq->buffer[idx];
}

/**
 * @brief Ensure that the sequence has at least `min_capacity` slots.
 *
 * This function safely allocates a new buffer if the current capacity is insufficient,
 * copies existing elements to the new buffer, and frees the old buffer.
 *
 * It avoids using realloc to ensure that existing memory is not invalidated in case
 * of allocation failure.
 *
 * @param seq Pointer to the BaseTrajSeq_t structure.
 * @param min_capacity Minimum required number of elements.
 * @return ErrorCode NO_ERROR on success, SEQUENCE_MEMORY_ERROR on allocation failure,
 *         SEQUENCE_INPUT_ERROR if seq is NULL.
 */
ErrorCode BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity)
{
    if (!seq)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    // If current capacity is enough, do nothing
    if (min_capacity <= seq->capacity)
    {
        C_LOG(LOG_LEVEL_DEBUG, "Current capacity sufficient (%zu >= %zu).", seq->capacity, min_capacity);
        return NO_ERROR;
    }

    // Determine new capacity: double current or start from 64
    size_t new_capacity = seq->capacity > 0 ? seq->capacity * 2 : 64;
    if (new_capacity < min_capacity)
        new_capacity = min_capacity;

    // Allocate a new buffer (zero-initialized)
    BaseTraj_t *new_buffer = (BaseTraj_t *)calloc(new_capacity, sizeof(BaseTraj_t));
    if (!new_buffer)
    {
        C_LOG(LOG_LEVEL_ERROR, "Memory allocation failed for capacity %zu.", new_capacity);
        return SEQUENCE_MEMORY_ERROR;
    }

    // Copy existing data safely
    if (seq->buffer && seq->length > 0)
    {
        memcpy(new_buffer, seq->buffer, seq->length * sizeof(BaseTraj_t));
    }

    // Free old buffer
    free(seq->buffer);

    // Update sequence structure
    seq->buffer = new_buffer;
    seq->capacity = new_capacity;

    C_LOG(LOG_LEVEL_DEBUG, "Capacity increased to %zu.", new_capacity);
    return NO_ERROR;
}

/**
 * @brief Appends a new trajectory point to the end of the sequence.
 *
 * This function ensures that the sequence has enough capacity, then
 * writes the provided values into a new BaseTraj_t element at the end.
 *
 * @param seq Pointer to the BaseTrajSeq_t structure.
 * @param time Time of the trajectory point.
 * @param px X position.
 * @param py Y position.
 * @param pz Z position.
 * @param vx X velocity.
 * @param vy Y velocity.
 * @param vz Z velocity.
 * @param mach Mach number.
 * @return ErrorCode NO_ERROR on success, SEQUENCE_MEMORY_ERROR if allocation fails,
 *         SEQUENCE_INPUT_ERROR if seq is NULL.
 */
ErrorCode BaseTrajSeq_t_append(BaseTrajSeq_t *seq, double time, double px, double py, double pz,
                               double vx, double vy, double vz, double mach)
{
    if (!seq)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    // Ensure enough capacity for the new element
    ErrorCode err = BaseTrajSeq_t_ensure_capacity(seq, seq->length + 1);
    if (err != NO_ERROR)
    {
        return err;
    }

    // Append the new element at the end
    BaseTraj_t *entry = &seq->buffer[seq->length];
    entry->time = time;
    entry->px = px;
    entry->py = py;
    entry->pz = pz;
    entry->vx = vx;
    entry->vy = vy;
    entry->vz = vz;
    entry->mach = mach;

    seq->length += 1;

    return NO_ERROR;
}

/**
 * @brief Finds the center index for 3-point interpolation in a trajectory sequence.
 *
 * Performs a binary search to locate the index "lo" such that:
 * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
 * - the key value at buf[lo] is the first >= key_value (if increasing)
 *   or first <= key_value (if decreasing).
 *
 * @param seq Pointer to the BaseTrajSeq_t sequence.
 * @param key_kind The InterpKey specifying which component to search by.
 * @param key_value The value to locate.
 * @return The center index for interpolation, or -1 if sequence is too short or NULL.
 */
static ssize_t BaseTrajSeq_t_bisect_center_idx_buf(
    const BaseTrajSeq_t *seq,
    InterpKey key_kind,
    double key_value)
{
    if (!seq || seq->length < 3)
    {
        return -1;
    }

    const BaseTraj_t *buf = seq->buffer;
    ssize_t n = seq->length;

    double v0 = BaseTraj_t_key_val_from_kind_buf(&buf[0], key_kind);
    double vN = BaseTraj_t_key_val_from_kind_buf(&buf[n - 1], key_kind);
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;

    // Binary search loop
    while (lo < hi)
        while (lo < hi)
        {
            ssize_t mid = lo + ((hi - lo) >> 1);
            double vm = BaseTraj_t_key_val_from_kind_buf(&buf[mid], key_kind);

            if ((increasing && vm < key_value) || (!increasing && vm > key_value))
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

    // Clamp to valid center index for 3-point interpolation
    if (lo < 1)
        lo = 1;
    if (lo > n - 2)
        lo = n - 2;

    return lo;
}

/**
 * @brief Finds the center index for 3-point interpolation along slant height.
 *
 * Performs a binary search to locate an index "lo" such that:
 * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
 * - the slant value at buf[lo] is the first >= value (if increasing)
 *   or first <= value (if decreasing).
 *
 * @param seq Pointer to the BaseTrajSeq_t sequence.
 * @param ca Cosine of the look angle.
 * @param sa Sine of the look angle.
 * @param value Target slant value.
 * @return Center index suitable for 3-point interpolation [1, n-2],
 *         or -1 if sequence is NULL or too short.
 */
static ssize_t BaseTrajSeq_t_bisect_center_idx_slant_buf(
    const BaseTrajSeq_t *seq,
    double ca,
    double sa,
    double value)
{
    if (!seq || seq->length < 3)
        return -1;

    const BaseTraj_t *buf = seq->buffer;
    ssize_t n = seq->length;

    double v0 = BaseTraj_t_slant_val_buf(&buf[0], ca, sa);
    double vN = BaseTraj_t_slant_val_buf(&buf[n - 1], ca, sa);
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;

    while (lo < hi)
    {
        ssize_t mid = lo + ((hi - lo) >> 1);
        double vm = BaseTraj_t_slant_val_buf(&buf[mid], ca, sa);

        if ((increasing && vm < value) || (!increasing && vm > value))
            lo = mid + 1;
        else
            hi = mid;
    }

    // Clamp to valid center index for 3-point interpolation
    if (lo < 1)
        lo = 1;
    if (lo > n - 2)
        lo = n - 2;

    return lo;
}

/**
 * @brief Interpolates trajectory data at a given slant height.
 *
 * Given a look angle (in radians) and a target slant height value,
 * this function finds a center index and performs monotone-preserving
 * 3-point Hermite (PCHIP) interpolation to compute time, position,
 * velocity, and Mach number at that slant height.
 *
 * @param seq Pointer to the BaseTrajSeq_t sequence.
 * @param look_angle_rad Look angle in radians.
 * @param value Target slant height for interpolation.
 * @param out Pointer to BaseTrajData_t where interpolated results will be stored.
 * @return NO_ERROR on success, or an appropriate ErrorCode on failure:
 *         SEQUENCE_INPUT_ERROR if seq or out is NULL,
 *         SEQUENCE_VALUE_ERROR if not enough points or interpolation fails.
 */
ErrorCode BaseTrajSeq_t_get_at_slant_height(
    const BaseTrajSeq_t *seq,
    double look_angle_rad,
    double value,
    BaseTrajData_t *out)
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
    if (center < 0)
    {
        C_LOG(LOG_LEVEL_ERROR, "Failed to find center index for interpolation.");
        return SEQUENCE_VALUE_ERROR;
    }

    const BaseTraj_t *buf = seq->buffer;
    const BaseTraj_t *p0 = &buf[center - 1];
    const BaseTraj_t *p1 = &buf[center];
    const BaseTraj_t *p2 = &buf[center + 1];

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

/**
 * @brief Retrieves trajectory data at a given index.
 *
 * Copies the values of time, position, velocity, and Mach number
 * from the sequence at the specified index into the provided output struct.
 *
 * @param seq Pointer to the BaseTrajSeq_t sequence.
 * @param idx Index of the trajectory point to retrieve.
 * @param out Pointer to BaseTrajData_t where results will be stored.
 * @return NO_ERROR on success, or an appropriate ErrorCode on failure:
 *         SEQUENCE_INPUT_ERROR if seq or out is NULL,
 *         SEQUENCE_INDEX_ERROR if idx is out of bounds.
 */
ErrorCode BaseTrajSeq_t_get_item(const BaseTrajSeq_t *seq, ssize_t idx, BaseTrajData_t *out)
{
    if (!seq || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return SEQUENCE_INPUT_ERROR;
    }

    const BaseTraj_t *entry_ptr = BaseTrajSeq_t_get_raw_item(seq, idx);
    if (!entry_ptr)
    {
        C_LOG(LOG_LEVEL_ERROR, "Index out of bounds.");
        return SEQUENCE_INDEX_ERROR;
    }

    out->time = entry_ptr->time;
    out->position = (V3dT){entry_ptr->px, entry_ptr->py, entry_ptr->pz};
    out->velocity = (V3dT){entry_ptr->vx, entry_ptr->vy, entry_ptr->vz};
    out->mach = entry_ptr->mach;

    return NO_ERROR;
}

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
static ErrorCode BaseTrajSeq_t_interpolate_at_center_with_log(
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
