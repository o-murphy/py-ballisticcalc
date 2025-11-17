#include <cmath>
#include <cstdlib> // Required for calloc, malloc, free
#include <cstring> // Required for memcpy
#include <stdexcept>
#include "bclibc/traj_data.hpp"

namespace bclibc
{

    /**
     * @brief Lookup table helper to retrieve a specific scalar value from BCLIBC_BaseTrajData.
     *
     * Used internally by the interpolation function to get the correct 'x' values
     * for the interpolation key.
     *
     * @param p Pointer to the BCLIBC_BaseTrajData structure.
     * @param key_kind The BCLIBC_BaseTraj_InterpKey specifying which field to retrieve (e.g., BCLIBC_BaseTraj_InterpKey::TIME, BCLIBC_BaseTraj_InterpKey::MACH, BCLIBC_BaseTraj_InterpKey::POS_X).
     * @return The value of the requested field. Returns 0.0 for an unknown key.
     */
    static inline double get_key_value(const BCLIBC_BaseTrajData *p, BCLIBC_BaseTraj_InterpKey key_kind)
    {
        switch (key_kind)
        {
        case BCLIBC_BaseTraj_InterpKey::TIME:
            return p->time;
        case BCLIBC_BaseTraj_InterpKey::MACH:
            return p->mach;
        case BCLIBC_BaseTraj_InterpKey::POS_X:
            return p->position.x;
        case BCLIBC_BaseTraj_InterpKey::POS_Y:
            return p->position.y;
        case BCLIBC_BaseTraj_InterpKey::POS_Z:
            return p->position.z;
        case BCLIBC_BaseTraj_InterpKey::VEL_X:
            return p->velocity.x;
        case BCLIBC_BaseTraj_InterpKey::VEL_Y:
            return p->velocity.y;
        case BCLIBC_BaseTraj_InterpKey::VEL_Z:
            return p->velocity.z;
        default:
            return 0.0;
        }
    }

    BCLIBC_BaseTrajData::BCLIBC_BaseTrajData(
        double time,
        BCLIBC_V3dT position,
        BCLIBC_V3dT velocity,
        double mach)
        : time(time),
          position(position),
          velocity(velocity),
          mach(mach) {};

    /**
     * @brief Interpolates a BCLIBC_BaseTrajData structure using three surrounding data points.
     *
     * Performs a 3-point interpolation (likely PCHIP or similar cubic spline variant)
     * on all fields of the trajectory data (`time, position, velocity, mach`) based on
     * a specified `key_kind` (the independent variable for interpolation) and its target `key_value`.
     *
     * @param key_kind The field to use as the independent variable for interpolation (x-axis).
     * @param key_value The target value for the independent variable at which to interpolate.
     * @param p0 Pointer to the first data point (before or at the start of the segment).
     * @param p1 Pointer to the second data point.
     * @param p2 Pointer to the third data point (after or at the end of the segment).
     * @param out Pointer to the BCLIBC_BaseTrajData structure where the interpolated result will be stored.
     * @return BCLIBC_ErrorType::NO_ERROR on success, BCLIBC_ErrorType::INPUT_ERROR for NULL input, BCLIBC_ErrorType::ZERO_DIVISION_ERROR for degenerate segments (identical key values).
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajData::interpolate(
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData *p0,
        const BCLIBC_BaseTrajData *p1,
        const BCLIBC_BaseTrajData *p2,
        BCLIBC_BaseTrajData *out)
    {
        if (!p0 || !p1 || !p2 || !out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR;
        }

        // Get key values
        const double x0 = get_key_value(p0, key_kind);
        const double x1 = get_key_value(p1, key_kind);
        const double x2 = get_key_value(p2, key_kind);

        // Guard against degenerate segments
        if (x0 == x1 || x0 == x2 || x1 == x2)
        {
            return BCLIBC_ErrorType::ZERO_DIVISION_ERROR;
        }

        // Cache position and velocity
        const BCLIBC_V3dT vp0 = p0->position;
        const BCLIBC_V3dT vp1 = p1->position;
        const BCLIBC_V3dT vp2 = p2->position;
        const BCLIBC_V3dT vv0 = p0->velocity;
        const BCLIBC_V3dT vv1 = p1->velocity;
        const BCLIBC_V3dT vv2 = p2->velocity;

        // Scalar interpolation using PCHIP

        // Interpolate all scalar fields
        out->time = (key_kind == BCLIBC_BaseTraj_InterpKey::TIME) ? key_value : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0->time, p1->time, p2->time);
        out->position = BCLIBC_V3dT{
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.x, vp1.x, vp2.x),
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.y, vp1.y, vp2.y),
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.z, vp1.z, vp2.z)};
        out->velocity = BCLIBC_V3dT{
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.x, vv1.x, vv2.x),
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.y, vv1.y, vv2.y),
            BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.z, vv1.z, vv2.z)};

        out->mach = (key_kind == BCLIBC_BaseTraj_InterpKey::MACH) ? key_value : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0->mach, p1->mach, p2->mach);

        return BCLIBC_ErrorType::NO_ERROR;
    };

    BCLIBC_BaseTraj::BCLIBC_BaseTraj(
        double time,
        double px,
        double py,
        double pz,
        double vx,
        double vy,
        double vz,
        double mach)
        : time(time),
          px(px),
          py(py),
          pz(pz),
          vx(vx),
          vy(vy),
          vz(vz),
          mach(mach) {};

    /**
     * @brief Get the key value of a BaseTraj element.
     *
     * @param key_kind Kind of key.
     * @return Value of the key.
     */
    double BCLIBC_BaseTraj::key_val(BCLIBC_BaseTraj_InterpKey key_kind) const
    {
        int k = (int)key_kind;
        if ((int)key_kind < 0 || (int)key_kind > BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT)
        {
            return 0.0;
        }

        switch (key_kind)
        {
        case BCLIBC_BaseTraj_InterpKey::TIME:
            return this->time;
        case BCLIBC_BaseTraj_InterpKey::MACH:
            return this->mach;
        case BCLIBC_BaseTraj_InterpKey::POS_X:
            return this->px;
        case BCLIBC_BaseTraj_InterpKey::POS_Y:
            return this->py;
        case BCLIBC_BaseTraj_InterpKey::POS_Z:
            return this->pz;
        case BCLIBC_BaseTraj_InterpKey::VEL_X:
            return this->vx;
        case BCLIBC_BaseTraj_InterpKey::VEL_Y:
            return this->vy;
        case BCLIBC_BaseTraj_InterpKey::VEL_Z:
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
     * When interpolating by BCLIBC_BaseTraj_InterpKey::TIME, the time field is set directly to x.
     * When interpolating by BCLIBC_BaseTraj_InterpKey::MACH, the mach field is set directly to x.
     *
     * @param x The target value to interpolate at.
     * @param ox0 Key value at point 0.
     * @param ox1 Key value at point 1.
     * @param ox2 Key value at point 2.
     * @param p0 Pointer to trajectory point 0.
     * @param p1 Pointer to trajectory point 1.
     * @param p2 Pointer to trajectory point 2.
     * @param out Pointer to output BCLIBC_BaseTraj where results will be stored.
     * @param skip_key BCLIBC_BaseTraj_InterpKey indicating which field is the interpolation key.
     */
    void BCLIBC_BaseTraj::interpolate3pt_vectorized(
        double x, double ox0, double ox1, double ox2,
        const BCLIBC_BaseTraj *p0, const BCLIBC_BaseTraj *p1, const BCLIBC_BaseTraj *p2,
        BCLIBC_BaseTraj *out, BCLIBC_BaseTraj_InterpKey skip_key)
    {
        // Time: either use x directly (if interpolating by time) or interpolate
        out->time = (skip_key == BCLIBC_BaseTraj_InterpKey::TIME)
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
        out->mach = (skip_key == BCLIBC_BaseTraj_InterpKey::MACH)
                        ? x
                        : BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);
    }

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
     * @return BCLIBC_ErrorType BCLIBC_ErrorType::NO_ERROR on success, BCLIBC_ErrorType::MEMORY_ERROR if allocation fails,
     *         BCLIBC_ErrorType::INPUT_ERROR if seq is NULL.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::append(double time, double px, double py, double pz, double vx, double vy, double vz, double mach)
    {

        try
        {
            this->buffer.push_back(
                BCLIBC_BaseTraj(time, px, py, pz, vx, vy, vz, mach));
        }
        catch (...)
        {
            return BCLIBC_ErrorType::RUNTIME_ERROR;
        }
        return BCLIBC_ErrorType::NO_ERROR;
    };

    /**
     * Returns the length of the trajectory sequence.
     *
     * @return The number of elements in the sequence, or -1 if seq is NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::get_length() const
    {
        return this->buffer.size();
    };

    /**
     * Returns the capacity of the trajectory sequence.
     *
     * @return capacity of the trajectory sequence, or -1 if seq is NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::get_capacity() const
    {
        return this->buffer.capacity();
    };

    /**
     * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
     *
     * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
     * @return 1 on success, 0 on failure.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_at(
        ssize_t idx,
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR; // Invalid input
        }
        BCLIBC_BaseTraj raw_output;
        BCLIBC_ErrorType err = this->interpolate_raw(idx, key_kind, key_value, &raw_output);
        if (err != BCLIBC_ErrorType::NO_ERROR)
        {
            return err; // BCLIBC_ErrorType::INDEX_ERROR or BCLIBC_ErrorType::VALUE_ERROR or BCLIBC_ErrorType::BASE_TRAJ_INTERP_KEY_ERROR
        }
        out->time = raw_output.time;
        out->position = BCLIBC_V3dT{raw_output.px, raw_output.py, raw_output.pz};
        out->velocity = BCLIBC_V3dT{raw_output.vx, raw_output.vy, raw_output.vz};
        out->mach = raw_output.mach;
        return BCLIBC_ErrorType::NO_ERROR;
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
        ssize_t len = (ssize_t)this->buffer.size();
        if (len == 0)
        {
            return NULL;
        }

        // Adjust negative indices
        if (idx < 0)
        {
            idx += len;
        }

        // Out-of-bounds check
        if (idx < 0 || idx >= len)
        {
            return NULL;
        }
        return const_cast<BCLIBC_BaseTraj *>(&this->buffer[idx]);
    };

    /**
     * @brief Retrieves trajectory data at a given index.
     *
     * Copies the values of time, position, velocity, and Mach number
     * from the sequence at the specified index into the provided output struct.
     *
     * @param idx Index of the trajectory point to retrieve.
     * @param out Pointer to BCLIBC_BaseTrajData where results will be stored.
     * @return BCLIBC_ErrorType::NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
     *         BCLIBC_ErrorType::INPUT_ERROR if seq or out is NULL,
     *         BCLIBC_ErrorType::INDEX_ERROR if idx is out of bounds.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_item(
        ssize_t idx,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR;
        }

        const BCLIBC_BaseTraj *entry_ptr = this->get_raw_item(idx);
        if (!entry_ptr)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Index out of bounds.");
            return BCLIBC_ErrorType::INDEX_ERROR;
        }

        out->time = entry_ptr->time;
        out->position = BCLIBC_V3dT{entry_ptr->px, entry_ptr->py, entry_ptr->pz};
        out->velocity = BCLIBC_V3dT{entry_ptr->vx, entry_ptr->vy, entry_ptr->vz};
        out->mach = entry_ptr->mach;

        return BCLIBC_ErrorType::NO_ERROR;
    };

    /**
     * @brief Get trajectory data at a given key value, with optional start time.
     *
     * @param key_kind Kind of key to search/interpolate.
     * @param key_value Key value to get.
     * @param start_from_time Optional start time (use -1 if not used).
     * @param out Output trajectory data.
     * @return BCLIBC_ErrorType BCLIBC_ErrorType::NO_ERROR if successful, otherwise error code.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_at(
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        double start_from_time,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR;
        }

        ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        ssize_t target_idx = -1;

        // Search from start_from_time if provided
        if (start_from_time > 0.0 && key_kind != BCLIBC_BaseTraj_InterpKey::TIME)
        {
            ssize_t start_idx = this->find_start_index(start_from_time);

            // Try exact match at start index
            BCLIBC_ErrorType exact_err = this->try_get_exact(start_idx, key_kind, key_value, out);
            if (exact_err == BCLIBC_ErrorType::NO_ERROR)
                return BCLIBC_ErrorType::NO_ERROR;

            // Find target index for interpolation
            ssize_t target_idx = this->find_target_index(key_kind, key_value, start_idx);
        }

        // If not found, bisect the whole range
        if (target_idx < 0)
        {
            ssize_t center = this->bisect_center_idx_buf(key_kind, key_value);
            if (center < 0)
            {
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Bisecting failed; not enough data points.");
                return BCLIBC_ErrorType::VALUE_ERROR;
            }
            target_idx = center < n - 1 ? center : n - 2;
        }

        // Try exact match at target index
        BCLIBC_ErrorType exact_err = this->try_get_exact(target_idx, key_kind, key_value, out);
        if (exact_err == BCLIBC_ErrorType::NO_ERROR)
            return BCLIBC_ErrorType::NO_ERROR;

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
     * @return BCLIBC_ErrorType::NO_ERROR on success, or an appropriate BCLIBC_ErrorType on failure:
     *         BCLIBC_ErrorType::INPUT_ERROR if seq or out is NULL,
     *         BCLIBC_ErrorType::VALUE_ERROR if not enough points or interpolation fails.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::get_at_slant_height(
        double look_angle_rad,
        double value,
        BCLIBC_BaseTrajData *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR;
        }

        double ca = std::cos(look_angle_rad);
        double sa = std::sin(look_angle_rad);

        ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Not enough data points for interpolation.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        ssize_t center = this->bisect_center_idx_slant_buf(ca, sa, value);
        if (center < 0)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to find center index for interpolation.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        if (center < 1 || center >= n - 1)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Calculated center index out of safe interpolation range.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        const auto &data_vector = this->buffer;
        const BCLIBC_BaseTraj *p0 = &data_vector[center - 1];
        const BCLIBC_BaseTraj *p1 = &data_vector[center];
        const BCLIBC_BaseTraj *p2 = &data_vector[center + 1];

        double ox0 = p0->slant_val_buf(ca, sa);
        double ox1 = p1->slant_val_buf(ca, sa);
        double ox2 = p2->slant_val_buf(ca, sa);

        if (ox0 == ox1 || ox1 == ox2)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Duplicate slant key values detected; cannot interpolate.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        out->time = BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->time, p1->time, p2->time);
        out->position = BCLIBC_V3dT{
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->px, p1->px, p2->px),
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->py, p1->py, p2->py),
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->pz, p1->pz, p2->pz)};
        out->velocity = BCLIBC_V3dT{
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vx, p1->vx, p2->vx),
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vy, p1->vy, p2->vy),
            BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->vz, p1->vz, p2->vz)};
        out->mach = BCLIBC_interpolate3pt(value, ox0, ox1, ox2, p0->mach, p1->mach, p2->mach);

        return BCLIBC_ErrorType::NO_ERROR;
    };

    /**
     * @brief Interpolate at center index with logging.
     *
     * @param idx Center index for interpolation.
     * @param key_kind Kind of interpolation key.
     * @param key_value Key value to interpolate at.
     * @param out Output trajectory data.
     * @return BCLIBC_ErrorType BCLIBC_ErrorType::NO_ERROR if successful, otherwise error code.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_at_center(
        ssize_t idx,
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        BCLIBC_ErrorType err = this->interpolate_at(idx, key_kind, key_value, out);
        if (err != BCLIBC_ErrorType::NO_ERROR)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Interpolation failed at center index %zd, error code: 0x%X", idx, err);
            return err; // BCLIBC_ErrorType::INDEX_ERROR or BCLIBC_ErrorType::VALUE_ERROR or BCLIBC_ErrorType::BASE_TRAJ_INTERP_KEY_ERROR
        }
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Interpolation successful at center index %zd.", idx);
        return BCLIBC_ErrorType::NO_ERROR;
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
     * @return BCLIBC_ErrorType::NO_ERROR on success, or an BCLIBC_ErrorType on failure.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::interpolate_raw(
        ssize_t idx,
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTraj *out) const
    {
        if (!out)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
            return BCLIBC_ErrorType::INPUT_ERROR;
        }

        const auto &data_vector = this->buffer;
        ssize_t length = (ssize_t)data_vector.size();

        // Handle negative indices
        if (idx < 0)
            idx += length;

        // Ensure we have valid points on both sides (idx-1, idx, idx+1)
        if (idx < 1 || idx >= length - 1)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Index out of bounds for interpolation.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        const BCLIBC_BaseTraj *p0 = &data_vector[idx - 1];
        const BCLIBC_BaseTraj *p1 = &data_vector[idx];
        const BCLIBC_BaseTraj *p2 = &data_vector[idx + 1];

        // Get key values from the three points using helper
        double ox0 = p0->key_val(key_kind);
        double ox1 = p1->key_val(key_kind);
        double ox2 = p2->key_val(key_kind);

        // Check for duplicate key values (would cause division by zero)
        if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Duplicate key values detected; cannot interpolate.");
            return BCLIBC_ErrorType::VALUE_ERROR;
        }

        // Interpolate all trajectory components
        // Vectorized interpolation
        // Store results
        BCLIBC_BaseTraj::interpolate3pt_vectorized(key_value, ox0, ox1, ox2, p0, p1, p2, out, key_kind);

        return BCLIBC_ErrorType::NO_ERROR;
    };

    /**
     * @brief Try to get exact value at index, return BCLIBC_ErrorType::NO_ERROR if successful.
     *
     * @param idx Index to check.
     * @param key_kind Kind of key.
     * @param key_value Key value to match.
     * @param out Output trajectory data.
     * @return BCLIBC_ErrorType::NO_ERROR if exact match found, otherwise BCLIBC_ErrorType::VALUE_ERROR.
     */
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq::try_get_exact(
        ssize_t idx,
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out) const
    {
        if (idx < 0 || idx >= (ssize_t)this->buffer.size())
        {
            return BCLIBC_ErrorType::INDEX_ERROR;
        }

        double epsilon = 1e-9;

        if (this->is_close(this->buffer[idx].key_val(key_kind), key_value, epsilon))
        {
            BCLIBC_ErrorType err = this->get_item(idx, out);
            if (err != BCLIBC_ErrorType::NO_ERROR)
            {
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Failed to get item at index %zd.", idx);
                return BCLIBC_ErrorType::INDEX_ERROR;
            }
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Exact match found at index %zd.", idx);
            return BCLIBC_ErrorType::NO_ERROR;
        }

        return BCLIBC_ErrorType::VALUE_ERROR; // not an exact match
    };

    /**
     * @brief Finds the center index for 3-point interpolation in a trajectory sequence.
     *
     * Performs a binary search to locate the index "lo" such that:
     * - buf[lo-1], buf[lo], buf[lo+1] can be safely used for interpolation,
     * - the key value at buf[lo] is the first >= key_value (if increasing)
     *   or first <= key_value (if decreasing).
     *
     * @param key_kind The BCLIBC_BaseTraj_InterpKey specifying which component to search by.
     * @param key_value The value to locate.
     * @return The center index for interpolation, or -1 if sequence is too short or NULL.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_buf(
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value) const
    {
        ssize_t n = (ssize_t)this->buffer.size();
        if (n < 3)
        {
            return -1;
        }

        const auto &data_vector = this->buffer;

        double v0 = data_vector[0].key_val(key_kind);
        double vN = data_vector[n - 1].key_val(key_kind);

        int increasing = (vN >= v0) ? 1 : 0;

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        double vm;

        // Binary search loop
        while (lo < hi)
        {
            ssize_t mid = lo + ((hi - lo) >> 1);

            vm = data_vector[mid].key_val(key_kind);

            if ((increasing && vm < key_value) || (!increasing && vm > key_value))
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

        // Clamp to valid center index for 3-point interpolation (idx-1, idx, idx+1)
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
        ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
            return -1;

        const auto &data_vector = this->buffer;

        double v0 = data_vector[0].slant_val_buf(ca, sa);
        double vN = data_vector[n - 1].slant_val_buf(ca, sa);

        int increasing = (vN >= v0) ? 1 : 0;

        ssize_t lo = 0;
        ssize_t hi = n - 1;
        double vm;

        while (lo < hi)
        {
            ssize_t mid = lo + ((hi - lo) >> 1);

            vm = data_vector[mid].slant_val_buf(ca, sa);

            if ((increasing && vm < value) || (!increasing && vm > value))
                lo = mid + 1;
            else
                hi = mid;
        }

        // Clamp to valid center index for 3-point interpolation (range [1, n-2])
        if (lo < 1)
            lo = 1;
        if (lo > n - 2)
            lo = n - 2;

        return lo;
    };

    /**
     * @brief Find the starting index for a given start time.
     *
     * @param start_time Start time to search from.
     * @return Index of the first element with time >= start_time.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_start_index(double start_time) const
    {
        ssize_t n = (ssize_t)this->buffer.size();
        const BCLIBC_BaseTraj *buf = this->buffer.data();

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
     * @param key_kind Kind of key.
     * @param key_value Key value to interpolate.
     * @param start_idx Index to start searching from.
     * @return Target index for interpolation, -1 if not found.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_target_index(
        BCLIBC_BaseTraj_InterpKey key_kind,
        double key_value,
        ssize_t start_idx) const
    {
        ssize_t n = (ssize_t)this->buffer.size();
        const BCLIBC_BaseTraj *buf = this->buffer.data();

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
        return std::fabs(a - b) < epsilon;
    };

    // BCLIBC_TrajectoryData::BCLIBC_TrajectoryData() {};

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        double time,
        const BCLIBC_V3dT *range_vector,
        const BCLIBC_V3dT *velocity_vector,
        double mach_arg,
        BCLIBC_TrajFlag flag)
        : time(time), flag(flag)
    {
        // BCLIBC_Coriolis const *c = &props->coriolis;
        // fprintf(stderr,
        //     "%.10f %.10f %.10f %.10f %.10f %.10f %.10f %.10f %d %.10f\n",
        //     c->sin_lat,
        //     c->cos_lat,
        //     c->sin_az,
        //     c->cos_az,
        //     c->range_east,
        //     c->range_north,
        //     c->cross_east,
        //     c->cross_north,
        //     c->flat_fire_only,
        //     c->muzzle_velocity_fps
        // );

        BCLIBC_V3dT adjusted_range = props->coriolis.adjust_range(time, range_vector);
        double spin_drift = props->spin_drift(time);
        double velocity = velocity_vector->mag();

        this->windage_ft = adjusted_range.z + spin_drift;

        // fprintf(stderr,
        //         "DEBUG_WINDAGE: time=%.6f, InputZ=%.6f, AdjustedZ=%.6f, SpinDrift=%.6f\n",
        //         time, range_vector->z, adjusted_range.z, spin_drift);

        double density_ratio_out, mach_out;
        props->atmo.update_density_factor_and_mach_for_altitude(
            range_vector->y, &density_ratio_out, &mach_out);

        double trajectory_angle = std::atan2(velocity_vector->y, velocity_vector->x);
        double look_angle_cos = std::cos(props->look_angle);
        double look_angle_sin = std::sin(props->look_angle);

        this->distance_ft = adjusted_range.x;
        this->velocity_fps = velocity;

        this->mach = velocity / (mach_arg != 0.0 ? mach_arg : mach_out);

        this->height_ft = adjusted_range.y;
        this->slant_height_ft = adjusted_range.y * look_angle_cos - adjusted_range.x * look_angle_sin;
        this->drop_angle_rad = BCLIBC_getCorrection(adjusted_range.x, adjusted_range.y) -
                               (adjusted_range.x ? props->look_angle : 0.0);
        this->windage_angle_rad = BCLIBC_getCorrection(adjusted_range.x, this->windage_ft);
        this->slant_distance_ft = adjusted_range.x * look_angle_cos + adjusted_range.y * look_angle_sin;
        this->angle_rad = trajectory_angle;
        this->density_ratio = density_ratio_out;
        this->drag = props->drag_by_mach(this->mach);
        this->energy_ft_lb = BCLIBC_calculateEnergy(props->weight, velocity);
        this->ogw_lb = BCLIBC_calculateOgw(props->weight, velocity);
    };

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_BaseTrajData *data,
        BCLIBC_TrajFlag flag)
        : BCLIBC_TrajectoryData(props, data->time, &data->position, &data->velocity, data->mach, flag) {};

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_FlaggedData *data)
        : BCLIBC_TrajectoryData(props, &data->data, data->flag) {};

    BCLIBC_TrajectoryData BCLIBC_TrajectoryData::interpolate(
        BCLIBC_TrajectoryData_InterpKey key,
        double value,
        const BCLIBC_TrajectoryData *p0,
        const BCLIBC_TrajectoryData *p1,
        const BCLIBC_TrajectoryData *p2,
        BCLIBC_TrajFlag flag,
        BCLIBC_InterpMethod method)
    {
        if (p0 == nullptr || p1 == nullptr || p2 == nullptr)
        {
            throw std::invalid_argument("Interpolation points (p0, p1, p2) cannot be NULL.");
        }

        // The independent variable for interpolation (x-axis)
        double x_val = value;
        double x0 = p0->get_key_val(key);
        double x1 = p1->get_key_val(key);
        double x2 = p2->get_key_val(key);

        // Use reflection to build the new TrajectoryData object

        // // Better copy data from p0 to fill uninterpolated or derived fields
        // BCLIBC_TrajectoryData interpolated_data;  // = {} possibly can not work on MSVC, use memset;
        BCLIBC_TrajectoryData interpolated_data = *p0;

        if ((int)key < 0 || (int)key > BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT)
        {
            throw std::runtime_error("Can't interpolate by unsupported key");
        }

        for (int k = 0; k < BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT; k++)
        {
            BCLIBC_TrajectoryData_InterpKey field_key = (BCLIBC_TrajectoryData_InterpKey)k;
            double y0 = p0->get_key_val(field_key);
            double y1 = p1->get_key_val(field_key);
            double y2 = p2->get_key_val(field_key);

            double interpolated_value = 0.0;
            BCLIBC_ErrorType err = BCLIBC_ErrorType::NO_ERROR;

            if (field_key == key)
            {
                interpolated_value = x_val;
            }
            else
            {
                if (method == BCLIBC_InterpMethod::PCHIP)
                {
                    interpolated_value = BCLIBC_interpolate3pt(
                        x_val, x0, x1, x2, y0, y1, y2);
                }
                else if (method == BCLIBC_InterpMethod::LINEAR)
                {
                    if (x_val <= x1)
                    {
                        err = (BCLIBC_ErrorType)BCLIBC_interpolate2pt(x_val, x0, y0, x1, y1, &interpolated_value);
                    }
                    else
                    {
                        err = (BCLIBC_ErrorType)BCLIBC_interpolate2pt(x_val, x1, y1, x2, y2, &interpolated_value);
                    }
                    if (err != BCLIBC_ErrorType::NO_ERROR)
                    {
                        throw std::domain_error("Zero division error");
                    }
                }
                else
                {
                    throw std::invalid_argument("Invalid interpolation method provided.");
                }
            }

            interpolated_data.set_key_val(field_key, interpolated_value);
        }
        interpolated_data.flag = flag;
        return interpolated_data;
    };

    double BCLIBC_TrajectoryData::get_key_val(BCLIBC_TrajectoryData_InterpKey key) const
    {
        switch (key)
        {
        case BCLIBC_TrajectoryData_InterpKey::TIME:
            return this->time;
        case BCLIBC_TrajectoryData_InterpKey::DISTANCE:
            return this->distance_ft;
        case BCLIBC_TrajectoryData_InterpKey::VELOCITY:
            return this->velocity_fps;
        case BCLIBC_TrajectoryData_InterpKey::MACH:
            return this->mach;
        case BCLIBC_TrajectoryData_InterpKey::HEIGHT:
            return this->height_ft;
        case BCLIBC_TrajectoryData_InterpKey::SLANT_HEIGHT:
            return this->slant_height_ft;
        case BCLIBC_TrajectoryData_InterpKey::DROP_ANGLE:
            return this->drop_angle_rad;
        case BCLIBC_TrajectoryData_InterpKey::WINDAGE:
            return this->windage_ft;
        case BCLIBC_TrajectoryData_InterpKey::WINDAGE_ANGLE:
            return this->windage_angle_rad;
        case BCLIBC_TrajectoryData_InterpKey::SLANT_DISTANCE:
            return this->slant_distance_ft;
        case BCLIBC_TrajectoryData_InterpKey::ANGLE:
            return this->angle_rad;
        case BCLIBC_TrajectoryData_InterpKey::DENSITY_RATIO:
            return this->density_ratio;
        case BCLIBC_TrajectoryData_InterpKey::DRAG:
            return this->drag;
        case BCLIBC_TrajectoryData_InterpKey::ENERGY:
            return this->energy_ft_lb;
        case BCLIBC_TrajectoryData_InterpKey::OGW:
            return this->ogw_lb;
        default:
            return 0.0; // Error or unexpected key
        }
    };

    void BCLIBC_TrajectoryData::set_key_val(BCLIBC_TrajectoryData_InterpKey key, double value)
    {
        switch (key)
        {
        case BCLIBC_TrajectoryData_InterpKey::TIME:
            this->time = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::DISTANCE:
            this->distance_ft = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::VELOCITY:
            this->velocity_fps = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::MACH:
            this->mach = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::HEIGHT:
            this->height_ft = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::SLANT_HEIGHT:
            this->slant_height_ft = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::DROP_ANGLE:
            this->drop_angle_rad = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::WINDAGE:
            this->windage_ft = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::WINDAGE_ANGLE:
            this->windage_angle_rad = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::SLANT_DISTANCE:
            this->slant_distance_ft = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::ANGLE:
            this->angle_rad = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::DENSITY_RATIO:
            this->density_ratio = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::DRAG:
            this->drag = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::ENERGY:
            this->energy_ft_lb = value;
            break;
        case BCLIBC_TrajectoryData_InterpKey::OGW:
            this->ogw_lb = value;
            break;
            // No default needed
        }
    };
};
