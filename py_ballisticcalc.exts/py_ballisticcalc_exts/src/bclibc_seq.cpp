#include <math.h>
#include <stdlib.h> // Required for calloc, malloc, free
#include <string.h> // Required for memcpy
#include "bclibc_interp.h"
#include "bclibc_bclib.h"
#include "bclibc_seq.hpp"

namespace bclibc
{

    /**
     * @brief Get the key value of a BaseTraj element.
     *
     * @param key_kind Kind of key.
     * @return Value of the key.
     */
    double BCLIBC_BaseTraj::key_val(BCLIBC_BaseTrajSeq_InterpKey key_kind) const
    {
        if (key_kind < 0 || key_kind > BCLIBC_BASE_TRAJ_SEQ_INTERP_KEY_ACTIVE_COUNT)
        {
            return 0.0;
        }

        switch (key_kind)
        {
        case BCLIBC_BASE_TRAJ_INTERP_KEY_TIME:
            return this->time;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_MACH:
            return this->mach;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X:
            return this->px;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y:
            return this->py;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z:
            return this->pz;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X:
            return this->vx;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y:
            return this->vy;
        case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z:
            return this->vz;
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
     * @param ca Cosine of the look angle.
     * @param sa Sine of the look angle.
     * @return The computed slant height, or NAN if the input pointer is NULL.
     */
    double BCLIBC_BaseTraj::slant_val_buf(double ca, double sa) const
    {
        return this->py * ca - this->px * sa;
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
    void BCLIBC_BaseTraj::interpolate3pt_vectorized(
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
     * Initializes a BCLIBC_BaseTrajSeq structure.
     *
     * Sets the buffer to NULL and length/capacity to 0.
     *
     */

    BCLIBC_BaseTrajSeq::BCLIBC_BaseTrajSeq()
    {
        this->buffer = NULL;
        this->length = 0;
        this->capacity = 0;
    };

    /**
     * Releases resources used by a BCLIBC_BaseTrajSeq structure.
     *
     * Frees the internal buffer and resets all fields to default values.
     *
     */
    BCLIBC_BaseTrajSeq::~BCLIBC_BaseTrajSeq()
    {
        free(this->buffer); // safe even if buffer is NULL
        this->buffer = NULL;
        this->length = 0;
        this->capacity = 0;
    };

    /**
     * @brief Appends a new trajectory point to the end of the sequence.
     *
     * This function ensures that the sequence has enough capacity, then
     * writes the provided values into a new BCLIBC_BaseTraj element at the end.
     *
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
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::append(double time, double px, double py, double pz, double vx, double vy, double vz, double mach)
    {

        // Ensure enough capacity for the new element
        BCLIBC_ErrorType err = this->ensure_capacity(this->length + 1);
        if (err != BCLIBC_E_NO_ERROR)
        {
            return err;
        }

        // Append the new element at the end
        BCLIBC_BaseTraj *entry = &this->buffer[this->length];
        entry->time = time;
        entry->px = px;
        entry->py = py;
        entry->pz = pz;
        entry->vx = vx;
        entry->vy = vy;
        entry->vz = vz;
        entry->mach = mach;

        this->length += 1;

        return BCLIBC_E_NO_ERROR;
    };

    /**
     * @brief Ensure that the sequence has at least `min_capacity` slots.
     *
     * This function safely allocates a new buffer if the current capacity is insufficient,
     * copies existing elements to the new buffer, and frees the old buffer.
     *
     * It avoids using realloc to ensure that existing memory is not invalidated in case
     * of allocation failure.
     *
     * @param min_capacity Minimum required number of elements.
     * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR on success, BCLIBC_E_MEMORY_ERROR on allocation failure,
     *         BCLIBC_E_INPUT_ERROR if seq is NULL.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::ensure_capacity(size_t min_capacity)
    {
        // If current capacity is enough, do nothing
        if (min_capacity <= this->capacity)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Current capacity sufficient (%zu >= %zu).", this->capacity, min_capacity);
            return BCLIBC_E_NO_ERROR;
        }

        // Determine new capacity: ^2 current or start from 64
        size_t new_capacity = this->capacity > 0 ? this->capacity : BCLIBC_BASE_TRAJ_SEQ_MIN_CAPACITY;
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
        if (this->length > 0)
        {
            memcpy(new_buffer, this->buffer, this->length * sizeof(BCLIBC_BaseTraj));
        }

        // Free old buffer
        free(this->buffer);

        // Update sequence structure
        this->buffer = new_buffer;
        this->capacity = new_capacity;

        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Capacity increased to %zu.", new_capacity);
        return BCLIBC_E_NO_ERROR;
    };

    /**
     * Returns the length of the trajectory sequence.
     *
     * @return The number of elements in the sequence, or -1 if seq is NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::get_length() const
    {
        return (ssize_t)this->length;
    };

    /**
     * Returns the capacity of the trajectory sequence.
     *
     * @return capacity of the trajectory sequence, or -1 if seq is NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::get_capacity() const
    {
        return (ssize_t)this->capacity;
    };

    /**
     * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
     *
     * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
     * @return 1 on success, 0 on failure.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_at(
        ssize_t idx,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_E_INPUT_ERROR; // Invalid input
        }
        BCLIBC_BaseTraj raw_output;
        BCLIBC_ErrorType err = this->interpolate_raw(idx, key_kind, key_value, &raw_output);
        if (err != BCLIBC_E_NO_ERROR)
        {
            return err; // BCLIBC_E_INDEX_ERROR or BCLIBC_E_VALUE_ERROR or BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR
        }
        out->time = raw_output.time;
        out->position = (BCLIBC_V3dT){raw_output.px, raw_output.py, raw_output.pz};
        out->velocity = (BCLIBC_V3dT){raw_output.vx, raw_output.vy, raw_output.vz};
        out->mach = raw_output.mach;
        return BCLIBC_E_NO_ERROR;
    };

    /**
     * Retrieve a pointer to a trajectory element at the given index.
     * Supports negative indices: -1 = last element, -2 = second-to-last, etc.
     *
     * @param idx Index of the element to retrieve. Can be negative.
     * @return Pointer to the BCLIBC_BaseTraj element, or NULL if index is out of bounds.
     */
    BCLIBC_BaseTraj *BCLIBC_BaseTrajSeq::get_raw_item(ssize_t idx) const
    {
        if (!this->buffer || this->length == 0)
        {
            return NULL;
        }

        ssize_t len = (ssize_t)this->length;

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

        return &this->buffer[idx];
    };

    /**
     * @brief Retrieves trajectory data at a given index.
     *
     * Copies the values of time, position, velocity, and Mach number
     * from the sequence at the specified index into the provided output struct.
     *
     * @param idx Index of the trajectory point to retrieve.
     * @param out Pointer to BCLIBC_BaseTrajData where results will be stored.
     * @return BCLIBC_E_NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
     *         BCLIBC_E_INPUT_ERROR if seq or out is NULL,
     *         BCLIBC_E_INDEX_ERROR if idx is out of bounds.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_item(
        ssize_t idx,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_E_INPUT_ERROR;
        }

        const BCLIBC_BaseTraj *entry_ptr = this->get_raw_item(idx);
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
    };

    /**
     * @brief Get trajectory data at a given key value, with optional start time.
     *
     * @param key_kind Kind of key to search/interpolate.
     * @param key_value Key value to get.
     * @param start_from_time Optional start time (use -1 if not used).
     * @param out Output trajectory data.
     * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_at(
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        double start_from_time,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_E_INPUT_ERROR;
        }

        ssize_t n = this->length;
        if (n < 3)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
            return BCLIBC_E_VALUE_ERROR;
        }

        BCLIBC_BaseTraj *buf = this->buffer;
        ssize_t target_idx = -1;

        // Search from start_from_time if provided
        if (start_from_time > 0.0 && key_kind != BCLIBC_BASE_TRAJ_INTERP_KEY_TIME)
        {
            ssize_t start_idx = this->find_start_index(buf, n, start_from_time);

            // Try exact match at start index
            BCLIBC_ErrorType exact_err = this->try_get_exact(start_idx, key_kind, key_value, out);
            if (exact_err == BCLIBC_E_NO_ERROR)
                return BCLIBC_E_NO_ERROR;

            // Find target index for interpolation
            target_idx = this->find_target_index(buf, n, key_kind, key_value, start_idx);
        }

        // If not found, bisect the whole range
        if (target_idx < 0)
        {
            ssize_t center = this->bisect_center_idx_buf(key_kind, key_value);
            if (center < 0)
            {
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Bisecting failed; not enough data points.");
                return BCLIBC_E_VALUE_ERROR;
            }
            target_idx = center < n - 1 ? center : n - 2;
        }

        // Try exact match at target index
        BCLIBC_ErrorType exact_err = this->try_get_exact(target_idx, key_kind, key_value, out);
        if (exact_err == BCLIBC_E_NO_ERROR)
            return BCLIBC_E_NO_ERROR;

        // Otherwise interpolate at center
        ssize_t center_idx = target_idx < n - 1 ? target_idx : n - 2;
        return this->interpolate_at_center(center_idx, key_kind, key_value, out);
    };

    /**
     * @brief Interpolates trajectory data at a given slant height.
     *
     * Given a look angle (in radians) and a target slant height value,
     * this function finds a center index and performs monotone-preserving
     * 3-point Hermite (PCHIP) interpolation to compute time, position,
     * velocity, and Mach number at that slant height.
     *
     * @param look_angle_rad Look angle in radians.
     * @param value Target slant height for interpolation.
     * @param out Pointer to BCLIBC_BaseTrajData where interpolated results will be stored.
     * @return BCLIBC_E_NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
     *         BCLIBC_E_INPUT_ERROR if seq or out is NULL,
     *         BCLIBC_E_VALUE_ERROR if not enough points or interpolation fails.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_at_slant_height(
        double look_angle_rad,
        double value,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_E_INPUT_ERROR;
        }

        double ca = cos(look_angle_rad);
        double sa = sin(look_angle_rad);
        ssize_t n = this->length;

        if (n < 3)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
            return BCLIBC_E_VALUE_ERROR;
        }

        ssize_t center = this->bisect_center_idx_slant_buf(ca, sa, value);
        if (center < 0)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to find center index for interpolation.");
            return BCLIBC_E_VALUE_ERROR;
        }

        const BCLIBC_BaseTraj *buf = this->buffer;
        const BCLIBC_BaseTraj *p0 = &buf[center - 1];
        const BCLIBC_BaseTraj *p1 = &buf[center];
        const BCLIBC_BaseTraj *p2 = &buf[center + 1];

        double ox0 = p0->slant_val_buf(ca, sa);
        double ox1 = p1->slant_val_buf(ca, sa);
        double ox2 = p2->slant_val_buf(ca, sa);

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
    };

    /**
     * @brief Interpolate at center index with logging.
     *
     * @param idx Center index for interpolation.
     * @param key_kind Kind of interpolation key.
     * @param key_value Key value to interpolate at.
     * @param out Output trajectory data.
     * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_at_center(
        ssize_t idx,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        BCLIBC_ErrorType err = this->interpolate_at(idx, key_kind, key_value, out);
        if (err != BCLIBC_E_NO_ERROR)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Interpolation failed at center index %zd, error code: 0x%X", idx, err);
            return err; // BCLIBC_E_INDEX_ERROR or BCLIBC_E_VALUE_ERROR or BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR
        }
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Interpolation successful at center index %zd.", idx);
        return BCLIBC_E_NO_ERROR;
    };

    /**
     * Interpolates a trajectory point at a specific index using its neighbors.
     *
     * This function performs 3-point monotone-preserving PCHIP interpolation
     * (Hermite evaluation) for all components of a trajectory point.
     *
     * @param idx Index around which interpolation is performed (uses idx-1, idx, idx+1).
     *            Negative indices are counted from the end of the buffer.
     * @param key_kind The key to interpolate along (e.g., time, position, velocity, Mach).
     * @param key_value The target value of the key to interpolate at.
     * @param out Pointer to a BCLIBC_BaseTraj struct where the interpolated result will be stored.
     * @return BCLIBC_E_NO_ERROR on success, or an BCLIBC_ErrorType on failure.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_raw(
        ssize_t idx,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTraj *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_E_INPUT_ERROR;
        }

        BCLIBC_BaseTraj *buffer = this->buffer;
        ssize_t length = this->length;

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
        double ox0 = p0->key_val(key_kind);
        double ox1 = p1->key_val(key_kind);
        double ox2 = p2->key_val(key_kind);

        // Check for duplicate key values (would cause division by zero)
        if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Duplicate key values detected; cannot interpolate.");
            return BCLIBC_E_VALUE_ERROR;
        }

        // Interpolate all trajectory components
        // Vectorized interpolation
        // Store results
        BCLIBC_BaseTraj::interpolate3pt_vectorized(key_value, ox0, ox1, ox2, p0, p1, p2, out, key_kind);

        return BCLIBC_E_NO_ERROR;
    };

    /**
     * @brief Try to get exact value at index, return BCLIBC_E_NO_ERROR if successful.
     *
     * @param idx Index to check.
     * @param key_kind Kind of key.
     * @param key_value Key value to match.
     * @param out Output trajectory data.
     * @return BCLIBC_E_NO_ERROR if exact match found, otherwise BCLIBC_E_VALUE_ERROR.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::try_get_exact(
        ssize_t idx,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        double epsilon = 1e-9;

        if (this->is_close(this->buffer[idx].key_val(key_kind), key_value, epsilon))
        {
            BCLIBC_ErrorType err = this->get_item(idx, out);
            if (err != BCLIBC_E_NO_ERROR)
            {
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to get item at index %zd.", idx);
                return BCLIBC_E_INDEX_ERROR;
            }
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Exact match found at index %zd.", idx);
            return BCLIBC_E_NO_ERROR;
        }

        return BCLIBC_E_VALUE_ERROR; // not an exact match
    };

    /**
     * @brief Finds the center index for 3-point interpolation in a trajectory sequence.
     *
     * Performs a binary search to locate the index "lo" such that:
     * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
     * - the key value at buf[lo] is the first >= key_value (if increasing)
     *   or first <= key_value (if decreasing).
     *
     * @param key_kind The BCLIBC_BaseTrajSeq_InterpKey specifying which component to search by.
     * @param key_value The value to locate.
     * @return The center index for interpolation, or -1 if sequence is too short or NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_buf(
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value) const
    {
        if (this->length < 3)
        {
            return -1;
        }

        const BCLIBC_BaseTraj *buf = this->buffer;
        ssize_t n = this->length;

        double v0 = buf[0].key_val(key_kind);
        double vN = buf[n - 1].key_val(key_kind);
        int increasing = (vN >= v0) ? 1 : 0;

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        double vm;

        // Binary search loop
        while (lo < hi)
        {
            ssize_t mid = lo + ((hi - lo) >> 1);
            vm = buf[mid].key_val(key_kind);

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
    };

    /**
     * @brief Finds the center index for 3-point interpolation along slant height.
     *
     * Performs a binary search to locate an index "lo" such that:
     * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
     * - the slant value at buf[lo] is the first >= value (if increasing)
     *   or first <= value (if decreasing).
     *
     * @param ca Cosine of the look angle.
     * @param sa Sine of the look angle.
     * @param value Target slant value.
     * @return Center index suitable for 3-point interpolation [1, n-2],
     *         or -1 if sequence is NULL or too short.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_slant_buf(
        double ca,
        double sa,
        double value) const
    {
        if (this->length < 3)
            return -1;

        const BCLIBC_BaseTraj *buf = this->buffer;
        ssize_t n = this->length;

        double v0 = buf[0].slant_val_buf(ca, sa);
        double vN = buf[n - 1].slant_val_buf(ca, sa);
        int increasing = (vN >= v0) ? 1 : 0;

        ssize_t lo = 0;
        ssize_t hi = n - 1;
        double vm;

        while (lo < hi)
        {
            ssize_t mid = lo + ((hi - lo) >> 1);
            vm = buf[mid].slant_val_buf(ca, sa);

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
    };

    /**
     * @brief Find the starting index for a given start time.
     *
     * @param buf Buffer of trajectory points.
     * @param n Length of buffer.
     * @param start_time Start time to search from.
     * @return Index of the first element with time >= start_time.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_start_index(const BCLIBC_BaseTraj *buf, ssize_t n, double start_time)
    {
        // Binary search
        if (n > 10 && buf[0].time <= buf[n - 1].time)
        {
            ssize_t lo = 0, hi = n - 1;

            while (lo < hi)
            {
                ssize_t mid = lo + ((hi - lo) >> 1);

                if (buf[mid].time < start_time)
                    lo = mid + 1;
                else
                    hi = mid;
            }

            return lo;
        }

        // Fallback for small arrays
        for (ssize_t i = 0; i < n; i++)
        {
            if (buf[i].time >= start_time)
            {
                return i;
            }
        }
        return n - 1;
    };

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
    ssize_t BCLIBC_BaseTrajSeq::find_target_index(
        const BCLIBC_BaseTraj *buf,
        ssize_t n,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        ssize_t start_idx)
    {
        // Minimal requirement for 3-point interpolation is 3 points.
        if (n < 3)
        {
            return -1;
        }

        double v0 = buf[0].key_val(key_kind);
        double vN = buf[n - 1].key_val(key_kind);
        // Determine the array's monotonicity (increasing or decreasing)
        int increasing = (vN >= v0) ? 1 : 0;

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        // Handle extrapolation cases: if the value is outside the trajectory range,
        // we clamp the index to the nearest valid interpolation center (1 or n-2).
        if (increasing)
        {
            if (key_value <= v0)
                return 1;
            if (key_value >= vN)
                return n - 2;
        }
        else
        { // Decreasing
            if (key_value >= v0)
                return 1;
            if (key_value <= vN)
                return n - 2;
        }

        // ------------------------------------
        // Binary Search (O(log N))
        // ------------------------------------
        while (lo < hi)
        {
            // Calculate the midpoint: lo + (hi - lo) / 2
            ssize_t mid = lo + ((hi - lo) >> 1);
            double vm = buf[mid].key_val(key_kind);

            // Adjust the search bounds based on monotonicity and target value
            if ((increasing && vm < key_value) || (!increasing && vm > key_value))
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

        // 'lo' is now the index of the first element satisfying the search condition.

        // Clamp the index to the valid range [1, n-2] required for 3-point interpolation.
        if (lo < 1)
            return 1;
        if (lo > n - 2)
            return n - 2;

        return lo;
    };

    /**
     * @brief Check if two double values are approximately equal.
     *
     * @param a First value.
     * @param b Second value.
     * @param epsilon Tolerance.
     * @return 1 if close, 0 otherwise.
     */
    int BCLIBC_BaseTrajSeq::is_close(double a, double b, double epsilon)
    {
        return fabs(a - b) < epsilon;
    };
};
