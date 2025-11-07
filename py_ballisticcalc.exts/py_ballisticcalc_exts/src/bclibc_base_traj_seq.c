#include <math.h>
#include <stdlib.h> // Required for calloc, malloc, free
#include <string.h> // Required for memcpy
#include "bclibc_interp.h"
#include "bclibc_bclib.h"
#include "bclibc_base_traj_seq.h"

/**
 * Retrieves a specific double value from a BCLIBC_BaseTraj struct using an BCLIBC_BaseTrajSeq_InterpKey.
 *
 * @param p A pointer to the BCLIBC_BaseTraj struct.
 * @param key_kind The BCLIBC_BaseTrajSeq_InterpKey indicating which value to retrieve.
 * @return The corresponding double value, or 0.0 if the key is unrecognized.
 */
static inline double BCLIBC_BaseTraj_keyValFromKindBuf(
    const BCLIBC_BaseTraj *p, BCLIBC_BaseTrajSeq_InterpKey key_kind)
{
    if (key_kind < 0 || key_kind > BCLIBC_BASE_TRAJ_SEQ_INTERP_KEY_ACTIVE_COUNT)
    {
        return 0.0;
    }

    switch (key_kind)
    {
    case BCLIBC_BASE_TRAJ_INTERP_KEY_TIME:
        return p->time;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_MACH:
        return p->mach;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X:
        return p->px;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y:
        return p->py;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z:
        return p->pz;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X:
        return p->vx;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y:
        return p->vy;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z:
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
 * @param p Pointer to the BCLIBC_BaseTraj trajectory point.
 * @param ca Cosine of the look angle.
 * @param sa Sine of the look angle.
 * @return The computed slant height, or NAN if the input pointer is NULL.
 */
static inline double BCLIBC_BaseTraj_slantValBuf(const BCLIBC_BaseTraj *p, double ca, double sa)
{
    if (p == NULL)
    {
        return NAN;
    }
    return p->py * ca - p->px * sa;
}

/**
 * Vectorized 3-point interpolation for all trajectory components.
 *
 * Performs PCHIP interpolation for all fields of BCLIBC_BaseTraj in a single pass.
 * When interpolating by BCLIBC_BASE_TRAJ_INTERP_KEY_TIME, the time field is set directly to x.
 * When interpolating by BCLIBC_BASE_TRAJ_INTERP_KEY_MACH, the mach field is set directly to x.
 *
 * @param x The target value to interpolate at.
 * @param ox0 Key value at point 0.
 * @param ox1 Key value at point 1.
 * @param ox2 Key value at point 2.
 * @param p0 Pointer to trajectory point 0.
 * @param p1 Pointer to trajectory point 1.
 * @param p2 Pointer to trajectory point 2.
 * @param out Pointer to output BCLIBC_BaseTraj where results will be stored.
 * @param skip_key BCLIBC_BaseTrajSeq_InterpKey indicating which field is the interpolation key.
 */
static void BCLIBC_interpolate3ptVectorized(
    double x, double ox0, double ox1, double ox2,
    const BCLIBC_BaseTraj *p0, const BCLIBC_BaseTraj *p1, const BCLIBC_BaseTraj *p2,
    BCLIBC_BaseTraj *out, BCLIBC_BaseTrajSeq_InterpKey skip_key)
{
    // Time: either use x directly (if interpolating by time) or interpolate
    out->time = (skip_key == BCLIBC_BASE_TRAJ_INTERP_KEY_TIME)
                    ? x
                    : BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->time, p1->time, p2->time);

    // Position components - always interpolate
    out->px = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->px, p1->px, p2->px);
    out->py = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->py, p1->py, p2->py);
    out->pz = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz);

    // Velocity components - always interpolate
    out->vx = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx);
    out->vy = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy);
    out->vz = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz);

    // Mach: either use x directly (if interpolating by mach) or interpolate
    out->mach = (skip_key == BCLIBC_BASE_TRAJ_INTERP_KEY_MACH)
                    ? x
                    : BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);
}

/**
 * Interpolates a trajectory point at a specific index using its neighbors.
 *
 * This function performs 3-point monotone-preserving PCHIP interpolation
 * (Hermite evaluation) for all components of a trajectory point.
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq sequence.
 * @param idx Index around which interpolation is performed (uses idx-1, idx, idx+1).
 *            Negative indices are counted from the end of the buffer.
 * @param key_kind The key to interpolate along (e.g., time, position, velocity, Mach).
 * @param key_value The target value of the key to interpolate at.
 * @param out Pointer to a BCLIBC_BaseTraj struct where the interpolated result will be stored.
 * @return BCLIBC_E_NO_ERROR on success, or an BCLIBC_ErrorType on failure.
 */
static BCLIBC_ErrorType BCLIBC_BaseTrajSeq_interpolateRaw(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, BCLIBC_BaseTraj *out)
{
    if (!seq || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    BCLIBC_BaseTraj *buffer = seq->buffer;
    ssize_t length = seq->length;

    // Handle negative indices
    if (idx < 0)
        idx += length;

    // Ensure we have valid points on both sides
    if (idx < 1 || idx >= length - 1)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Index out of bounds for interpolation.");
        return BCLIBC_E_VALUE_ERROR;
    }

    BCLIBC_BaseTraj *p0 = &buffer[idx - 1];
    BCLIBC_BaseTraj *p1 = &buffer[idx];
    BCLIBC_BaseTraj *p2 = &buffer[idx + 1];

    // Get key values from the three points using helper
    double ox0 = BCLIBC_BaseTraj_keyValFromKindBuf(p0, key_kind);
    double ox1 = BCLIBC_BaseTraj_keyValFromKindBuf(p1, key_kind);
    double ox2 = BCLIBC_BaseTraj_keyValFromKindBuf(p2, key_kind);

    // Check for duplicate key values (would cause division by zero)
    if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Duplicate key values detected; cannot interpolate.");
        return BCLIBC_E_VALUE_ERROR;
    }

    // Interpolate all trajectory components
    // Vectorized interpolation
    // Store results
    BCLIBC_interpolate3ptVectorized(key_value, ox0, ox1, ox2, p0, p1, p2, out, key_kind);

    return BCLIBC_E_NO_ERROR;
}

BCLIBC_ErrorType BCLIBC_BaseTrajSeq_interpolateAt(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, BCLIBC_BaseTrajData *out)
{
    if (!seq || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR; // Invalid input
    }
    BCLIBC_BaseTraj raw_output;
    int err = BCLIBC_BaseTrajSeq_interpolateRaw(seq, idx, key_kind, key_value, &raw_output);
    if (err != BCLIBC_E_NO_ERROR)
    {
        return err; // BCLIBC_E_INDEX_ERROR or BCLIBC_E_VALUE_ERROR or BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR
    }
    out->time = raw_output.time;
    out->position = (BCLIBC_V3dT){raw_output.px, raw_output.py, raw_output.pz};
    out->velocity = (BCLIBC_V3dT){raw_output.vx, raw_output.vy, raw_output.vz};
    out->mach = raw_output.mach;
    return BCLIBC_E_NO_ERROR;
}

/**
 * Initializes a BCLIBC_BaseTrajSeq structure.
 *
 * Sets the buffer to NULL and length/capacity to 0.
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq structure to initialize.
 */
void BCLIBC_BaseTrajSeq_init(BCLIBC_BaseTrajSeq *seq)
{
    if (seq == NULL)
        return; // safe guard

    seq->buffer = NULL;
    seq->length = 0;
    seq->capacity = 0;
}

/**
 * Releases resources used by a BCLIBC_BaseTrajSeq structure.
 *
 * Frees the internal buffer and resets all fields to default values.
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq structure to release.
 */
void BCLIBC_BaseTrajSeq_release(BCLIBC_BaseTrajSeq *seq)
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
 * @param seq Pointer to the BCLIBC_BaseTrajSeq structure.
 * @return The number of elements in the sequence, or -1 if seq is NULL.
 */
ssize_t BCLIBC_BaseTrajSeq_len(const BCLIBC_BaseTrajSeq *seq)
{
    return seq ? (ssize_t)seq->length : -1;
}

/**
 * Retrieve a pointer to a trajectory element at the given index.
 * Supports negative indices: -1 = last element, -2 = second-to-last, etc.
 *
 * @param seq Pointer to the trajectory sequence.
 * @param idx Index of the element to retrieve. Can be negative.
 * @return Pointer to the BCLIBC_BaseTraj element, or NULL if index is out of bounds.
 */
inline BCLIBC_BaseTraj *BCLIBC_BaseTrajSeq_getRawItem(const BCLIBC_BaseTrajSeq *seq, ssize_t idx)
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
 * @param seq Pointer to the BCLIBC_BaseTrajSeq structure.
 * @param min_capacity Minimum required number of elements.
 * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR on success, BCLIBC_E_MEMORY_ERROR on allocation failure,
 *         BCLIBC_E_INPUT_ERROR if seq is NULL.
 */
BCLIBC_ErrorType BCLIBC_BaseTrajSeq_ensureCapacity(BCLIBC_BaseTrajSeq *seq, size_t min_capacity)
{
    if (!seq)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    // If current capacity is enough, do nothing
    if (min_capacity <= seq->capacity)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Current capacity sufficient (%zu >= %zu).", seq->capacity, min_capacity);
        return BCLIBC_E_NO_ERROR;
    }

    // Determine new capacity: ^2 current or start from 64
    size_t new_capacity = seq->capacity > 0 ? seq->capacity : 64;
    while (new_capacity < min_capacity)
    {
        new_capacity <<= 1; // Faster than *= 2
    }

    // Allocate a new buffer (zero-initialized)
    BCLIBC_BaseTraj *new_buffer = (BCLIBC_BaseTraj *)malloc(new_capacity * sizeof(BCLIBC_BaseTraj));
    if (!new_buffer)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Memory allocation failed for capacity %zu.", new_capacity);
        return BCLIBC_E_MEMORY_ERROR;
    }

    // Copy existing data safely
    if (seq->length > 0)
    {
        memcpy(new_buffer, seq->buffer, seq->length * sizeof(BCLIBC_BaseTraj));
    }

    // Free old buffer
    free(seq->buffer);

    // Update sequence structure
    seq->buffer = new_buffer;
    seq->capacity = new_capacity;

    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Capacity increased to %zu.", new_capacity);
    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Appends a new trajectory point to the end of the sequence.
 *
 * This function ensures that the sequence has enough capacity, then
 * writes the provided values into a new BCLIBC_BaseTraj element at the end.
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq structure.
 * @param time Time of the trajectory point.
 * @param px X position.
 * @param py Y position.
 * @param pz Z position.
 * @param vx X velocity.
 * @param vy Y velocity.
 * @param vz Z velocity.
 * @param mach Mach number.
 * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR on success, BCLIBC_E_MEMORY_ERROR if allocation fails,
 *         BCLIBC_E_INPUT_ERROR if seq is NULL.
 */
BCLIBC_ErrorType BCLIBC_BaseTrajSeq_append(BCLIBC_BaseTrajSeq *seq, double time, double px, double py, double pz,
                                           double vx, double vy, double vz, double mach)
{
    if (!seq)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    // Ensure enough capacity for the new element
    BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_ensureCapacity(seq, seq->length + 1);
    if (err != BCLIBC_E_NO_ERROR)
    {
        return err;
    }

    // Append the new element at the end
    BCLIBC_BaseTraj *entry = &seq->buffer[seq->length];
    entry->time = time;
    entry->px = px;
    entry->py = py;
    entry->pz = pz;
    entry->vx = vx;
    entry->vy = vy;
    entry->vz = vz;
    entry->mach = mach;

    seq->length += 1;

    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Finds the center index for 3-point interpolation in a trajectory sequence.
 *
 * Performs a binary search to locate the index "lo" such that:
 * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
 * - the key value at buf[lo] is the first >= key_value (if increasing)
 *   or first <= key_value (if decreasing).
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq sequence.
 * @param key_kind The BCLIBC_BaseTrajSeq_InterpKey specifying which component to search by.
 * @param key_value The value to locate.
 * @return The center index for interpolation, or -1 if sequence is too short or NULL.
 */
static ssize_t BCLIBC_BaseTrajSeq_bisectCenterIdxBuf(
    const BCLIBC_BaseTrajSeq *seq,
    BCLIBC_BaseTrajSeq_InterpKey key_kind,
    double key_value)
{
    if (!seq || seq->length < 3)
    {
        return -1;
    }

    const BCLIBC_BaseTraj *buf = seq->buffer;
    ssize_t n = seq->length;

    double v0 = BCLIBC_BaseTraj_keyValFromKindBuf(&buf[0], key_kind);
    double vN = BCLIBC_BaseTraj_keyValFromKindBuf(&buf[n - 1], key_kind);
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;

    double vm;

    // Binary search loop
    while (lo < hi)
    {
        ssize_t mid = lo + ((hi - lo) >> 1);
        vm = BCLIBC_BaseTraj_keyValFromKindBuf(&buf[mid], key_kind);

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
 * @param seq Pointer to the BCLIBC_BaseTrajSeq sequence.
 * @param ca Cosine of the look angle.
 * @param sa Sine of the look angle.
 * @param value Target slant value.
 * @return Center index suitable for 3-point interpolation [1, n-2],
 *         or -1 if sequence is NULL or too short.
 */
static ssize_t BCLIBC_BaseTrajSeq_bisectCenterIdxSlantBuf(
    const BCLIBC_BaseTrajSeq *seq,
    double ca,
    double sa,
    double value)
{
    if (!seq || seq->length < 3)
        return -1;

    const BCLIBC_BaseTraj *buf = seq->buffer;
    ssize_t n = seq->length;

    double v0 = BCLIBC_BaseTraj_slantValBuf(&buf[0], ca, sa);
    double vN = BCLIBC_BaseTraj_slantValBuf(&buf[n - 1], ca, sa);
    int increasing = (vN >= v0) ? 1 : 0;

    ssize_t lo = 0;
    ssize_t hi = n - 1;
    double vm;

    while (lo < hi)
    {
        ssize_t mid = lo + ((hi - lo) >> 1);
        vm = BCLIBC_BaseTraj_slantValBuf(&buf[mid], ca, sa);

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
 * @param seq Pointer to the BCLIBC_BaseTrajSeq sequence.
 * @param look_angle_rad Look angle in radians.
 * @param value Target slant height for interpolation.
 * @param out Pointer to BCLIBC_BaseTrajData where interpolated results will be stored.
 * @return BCLIBC_E_NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
 *         BCLIBC_E_INPUT_ERROR if seq or out is NULL,
 *         BCLIBC_E_VALUE_ERROR if not enough points or interpolation fails.
 */
BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAtSlantHeight(
    const BCLIBC_BaseTrajSeq *seq,
    double look_angle_rad,
    double value,
    BCLIBC_BaseTrajData *out)
{
    if (!seq || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    double ca = cos(look_angle_rad);
    double sa = sin(look_angle_rad);
    ssize_t n = seq->length;

    if (n < 3)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
        return BCLIBC_E_VALUE_ERROR;
    }

    ssize_t center = BCLIBC_BaseTrajSeq_bisectCenterIdxSlantBuf(seq, ca, sa, value);
    if (center < 0)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to find center index for interpolation.");
        return BCLIBC_E_VALUE_ERROR;
    }

    const BCLIBC_BaseTraj *buf = seq->buffer;
    const BCLIBC_BaseTraj *p0 = &buf[center - 1];
    const BCLIBC_BaseTraj *p1 = &buf[center];
    const BCLIBC_BaseTraj *p2 = &buf[center + 1];

    double ox0 = BCLIBC_BaseTraj_slantValBuf(p0, ca, sa);
    double ox1 = BCLIBC_BaseTraj_slantValBuf(p1, ca, sa);
    double ox2 = BCLIBC_BaseTraj_slantValBuf(p2, ca, sa);

    out->time = BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->time, p1->time, p2->time);
    out->position = (BCLIBC_V3dT){
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->px, p1->px, p2->px),
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->py, p1->py, p2->py),
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz)};
    out->velocity = (BCLIBC_V3dT){
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx),
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy),
        BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz)};
    out->mach = BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);

    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Retrieves trajectory data at a given index.
 *
 * Copies the values of time, position, velocity, and Mach number
 * from the sequence at the specified index into the provided output struct.
 *
 * @param seq Pointer to the BCLIBC_BaseTrajSeq sequence.
 * @param idx Index of the trajectory point to retrieve.
 * @param out Pointer to BCLIBC_BaseTrajData where results will be stored.
 * @return BCLIBC_E_NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
 *         BCLIBC_E_INPUT_ERROR if seq or out is NULL,
 *         BCLIBC_E_INDEX_ERROR if idx is out of bounds.
 */
BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getItem(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajData *out)
{
    if (!seq || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    const BCLIBC_BaseTraj *entry_ptr = BCLIBC_BaseTrajSeq_getRawItem(seq, idx);
    if (!entry_ptr)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Index out of bounds.");
        return BCLIBC_E_INDEX_ERROR;
    }

    out->time = entry_ptr->time;
    out->position = (BCLIBC_V3dT){entry_ptr->px, entry_ptr->py, entry_ptr->pz};
    out->velocity = (BCLIBC_V3dT){entry_ptr->vx, entry_ptr->vy, entry_ptr->vz};
    out->mach = entry_ptr->mach;

    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Interpolate at center index with logging.
 *
 * @param seq Pointer to the trajectory sequence.
 * @param idx Center index for interpolation.
 * @param key_kind Kind of interpolation key.
 * @param key_value Key value to interpolate at.
 * @param out Output trajectory data.
 * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
 */
static BCLIBC_ErrorType BCLIBC_BaseTrajSeq_interpolateAtCenterWithLog(
    const BCLIBC_BaseTrajSeq *seq,
    ssize_t idx,
    BCLIBC_BaseTrajSeq_InterpKey key_kind,
    double key_value,
    BCLIBC_BaseTrajData *out)
{
    BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_interpolateAt(seq, idx, key_kind, key_value, out);
    if (err != BCLIBC_E_NO_ERROR)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Interpolation failed at center index %zd, error code: 0x%X", idx, err);
        return err; // BCLIBC_E_INDEX_ERROR or BCLIBC_E_VALUE_ERROR or BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR
    }
    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Interpolation successful at center index %zd.", idx);
    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Check if two double values are approximately equal.
 *
 * @param a First value.
 * @param b Second value.
 * @param epsilon Tolerance.
 * @return 1 if close, 0 otherwise.
 */
static int BCLIBC_BaseTrajSeq_isClose(double a, double b, double epsilon)
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
static double BCLIBC_BaseTraj_keyVal(const BCLIBC_BaseTraj *elem, BCLIBC_BaseTrajSeq_InterpKey key_kind)
{
    return BCLIBC_BaseTraj_keyValFromKindBuf(elem, key_kind);
}

/**
 * @brief Find the starting index for a given start time.
 *
 * @param buf Buffer of trajectory points.
 * @param n Length of buffer.
 * @param start_time Start time to search from.
 * @return Index of the first element with time >= start_time.
 */
static ssize_t BCLIBC_BaseTrajSeq_findStartIndex(const BCLIBC_BaseTraj *buf, ssize_t n, double start_time)
{
    // // FIXME: possibly use Binary search
    // if (n > 10 && buf[0].time <= buf[n-1].time)
    // {
    //     ssize_t lo = 0, hi = n - 1;

    //     while (lo < hi)
    //     {
    //         ssize_t mid = lo + ((hi - lo) >> 1);

    //         if (buf[mid].time < start_time)
    //             lo = mid + 1;
    //         else
    //             hi = mid;
    //     }

    //     return lo;
    // }

    // Fallback for small arrays
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
static ssize_t BCLIBC_BaseTrajSeq_findTargetIndex(const BCLIBC_BaseTraj *buf, ssize_t n, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, ssize_t start_idx)
{
    double a, b;

    // Forward search
    for (ssize_t i = start_idx; i < n - 1; i++)
    {
        a = BCLIBC_BaseTraj_keyVal(&buf[i], key_kind);
        b = BCLIBC_BaseTraj_keyVal(&buf[i + 1], key_kind);
        if ((a <= key_value && key_value <= b) || (b <= key_value && key_value <= a))
        {
            return i + 1;
        }
    }

    // Backward search
    for (ssize_t i = start_idx; i > 0; i--)
    {
        a = BCLIBC_BaseTraj_keyVal(&buf[i], key_kind);
        b = BCLIBC_BaseTraj_keyVal(&buf[i - 1], key_kind);
        if ((b <= key_value && key_value <= a) || (a <= key_value && key_value <= b))
        {
            return i;
        }
    }

    return -1; // not found
}

/**
 * @brief Try to get exact value at index, return BCLIBC_E_NO_ERROR if successful.
 *
 * @param seq Pointer to trajectory sequence.
 * @param idx Index to check.
 * @param key_kind Kind of key.
 * @param key_value Key value to match.
 * @param out Output trajectory data.
 * @return BCLIBC_E_NO_ERROR if exact match found, otherwise BCLIBC_E_VALUE_ERROR.
 */
static BCLIBC_ErrorType BCLIBC_BaseTrajSeq_tryGetExact(const BCLIBC_BaseTrajSeq *seq, ssize_t idx, BCLIBC_BaseTrajSeq_InterpKey key_kind, double key_value, BCLIBC_BaseTrajData *out)
{
    const BCLIBC_BaseTraj *buf = seq->buffer;
    double epsilon = 1e-9;

    if (BCLIBC_BaseTrajSeq_isClose(BCLIBC_BaseTraj_keyVal(&buf[idx], key_kind), key_value, epsilon))
    {
        BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_getItem(seq, idx, out);
        if (err != BCLIBC_E_NO_ERROR)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to get item at index %zd.", idx);
            return BCLIBC_E_INDEX_ERROR;
        }
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Exact match found at index %zd.", idx);
        return BCLIBC_E_NO_ERROR;
    }

    return BCLIBC_E_VALUE_ERROR; // not an exact match
}

/**
 * @brief Get trajectory data at a given key value, with optional start time.
 *
 * @param seq Pointer to trajectory sequence.
 * @param key_kind Kind of key to search/interpolate.
 * @param key_value Key value to get.
 * @param start_from_time Optional start time (use -1 if not used).
 * @param out Output trajectory data.
 * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
 */
BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAt(
    const BCLIBC_BaseTrajSeq *seq,
    BCLIBC_BaseTrajSeq_InterpKey key_kind,
    double key_value,
    double start_from_time,
    BCLIBC_BaseTrajData *out)
{
    if (!seq || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    ssize_t n = seq->length;
    if (n < 3)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
        return BCLIBC_E_VALUE_ERROR;
    }

    BCLIBC_BaseTraj *buf = seq->buffer;
    ssize_t target_idx = -1;

    // Search from start_from_time if provided
    if (start_from_time > 0.0 && key_kind != BCLIBC_BASE_TRAJ_INTERP_KEY_TIME)
    {
        ssize_t start_idx = BCLIBC_BaseTrajSeq_findStartIndex(buf, n, start_from_time);

        // Try exact match at start index
        BCLIBC_ErrorType exact_err = BCLIBC_BaseTrajSeq_tryGetExact(seq, start_idx, key_kind, key_value, out);
        if (exact_err == BCLIBC_E_NO_ERROR)
            return BCLIBC_E_NO_ERROR;

        // Find target index for interpolation
        target_idx = BCLIBC_BaseTrajSeq_findTargetIndex(buf, n, key_kind, key_value, start_idx);
    }

    // If not found, bisect the whole range
    if (target_idx < 0)
    {
        ssize_t center = BCLIBC_BaseTrajSeq_bisectCenterIdxBuf(seq, key_kind, key_value);
        if (center < 0)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Bisecting failed; not enough data points.");
            return BCLIBC_E_VALUE_ERROR;
        }
        target_idx = center < n - 1 ? center : n - 2;
    }

    // Try exact match at target index
    BCLIBC_ErrorType exact_err = BCLIBC_BaseTrajSeq_tryGetExact(seq, target_idx, key_kind, key_value, out);
    if (exact_err == BCLIBC_E_NO_ERROR)
        return BCLIBC_E_NO_ERROR;

    // Otherwise interpolate at center
    ssize_t center_idx = target_idx < n - 1 ? target_idx : n - 2;
    return BCLIBC_BaseTrajSeq_interpolateAtCenterWithLog(seq, center_idx, key_kind, key_value, out);
}
