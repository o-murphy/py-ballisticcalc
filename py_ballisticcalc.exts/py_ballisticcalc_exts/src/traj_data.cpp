#include <cmath>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include "bclibc/traj_data.hpp"

namespace bclibc
{
    /**
     * @brief Constructs trajectory data from individual scalar components.
     */
    BCLIBC_BaseTrajData::BCLIBC_BaseTrajData(
        double time,
        double px, double py, double pz,
        double vx, double vy, double vz,
        double mach)
        : time(time),
          px(px), py(py), pz(pz),
          vx(vx), vy(vy), vz(vz),
          mach(mach) {}

    /**
     * @brief Constructs trajectory data from position and velocity vectors.
     *
     * OPTIMIZATION: Takes vectors by const reference to avoid unnecessary copies.
     */
    BCLIBC_BaseTrajData::BCLIBC_BaseTrajData(
        double time,
        const BCLIBC_V3dT &position, // Changed to const&
        const BCLIBC_V3dT &velocity, // Changed to const&
        double mach)
        : time(time),
          px(position.x), py(position.y), pz(position.z),
          vx(velocity.x), vy(velocity.y), vz(velocity.z),
          mach(mach)
    {
    }

    /**
     * @brief Interpolates trajectory data using 3-point PCHIP method.
     *
     * Performs monotone-preserving cubic Hermite interpolation on all trajectory
     * components based on a specified key (independent variable).
     *
     * OPTIMIZATION: Caches key values and uses direct field access instead of
     * repeated get_key_val() calls.
     *
     * @param key_kind The field to use as independent variable.
     * @param key_value Target value for interpolation.
     * @param p0 First data point.
     * @param p1 Second data point.
     * @param p2 Third data point.
     * @param out Output parameter for interpolated result.
     */
    void BCLIBC_BaseTrajData::interpolate(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData &p0,
        const BCLIBC_BaseTrajData &p1,
        const BCLIBC_BaseTrajData &p2,
        BCLIBC_BaseTrajData &out)
    {
        // Cache key values - avoid repeated virtual function calls
        const double x0 = p0.get_key_val(key_kind);
        const double x1 = p1.get_key_val(key_kind);
        const double x2 = p2.get_key_val(key_kind);

        // Validate non-degenerate segments
        if (x0 == x1 || x0 == x2 || x1 == x2)
        {
            throw std::domain_error("Degenerate interpolation segment: duplicate key values");
        }

        // Interpolate all fields directly without creating intermediate vectors
        // This avoids 6 vector constructions compared to original code

        // Time: use key_value directly if interpolating by time
        out.time = (key_kind == BCLIBC_BaseTrajData_InterpKey::TIME)
                       ? key_value
                       : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.time, p1.time, p2.time);

        // Position components
        out.px = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.px, p1.px, p2.px);
        out.py = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.py, p1.py, p2.py);
        out.pz = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.pz, p1.pz, p2.pz);

        // Velocity components
        out.vx = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.vx, p1.vx, p2.vx);
        out.vy = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.vy, p1.vy, p2.vy);
        out.vz = BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.vz, p1.vz, p2.vz);

        // Mach: use key_value directly if interpolating by mach
        out.mach = (key_kind == BCLIBC_BaseTrajData_InterpKey::MACH)
                       ? key_value
                       : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0.mach, p1.mach, p2.mach);
    }

    /**
     * @brief Retrieves the value of a specified key field.
     *
     * @param key_kind The field to retrieve.
     * @return Value of the specified field.
     */
    double BCLIBC_BaseTrajData::get_key_val(BCLIBC_BaseTrajData_InterpKey key_kind) const
    {
        // Bounds check
        if ((int)key_kind < 0 || (int)key_kind > BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT)
        {
            return 0.0;
        }

        switch (key_kind)
        {
        case BCLIBC_BaseTrajData_InterpKey::TIME:
            return this->time;
        case BCLIBC_BaseTrajData_InterpKey::MACH:
            return this->mach;
        case BCLIBC_BaseTrajData_InterpKey::POS_X:
            return this->px;
        case BCLIBC_BaseTrajData_InterpKey::POS_Y:
            return this->py;
        case BCLIBC_BaseTrajData_InterpKey::POS_Z:
            return this->pz;
        case BCLIBC_BaseTrajData_InterpKey::VEL_X:
            return this->vx;
        case BCLIBC_BaseTrajData_InterpKey::VEL_Y:
            return this->vy;
        case BCLIBC_BaseTrajData_InterpKey::VEL_Z:
            return this->vz;
        default:
            return 0.0;
        }
    }

    /**
     * @brief Computes slant height relative to a look angle.
     *
     * Formula: slant_height = py * cos(angle) - px * sin(angle)
     *
     * @param ca Cosine of look angle.
     * @param sa Sine of look angle.
     * @return Computed slant height.
     */
    double BCLIBC_BaseTrajData::slant_val_buf(double ca, double sa) const
    {
        return this->py * ca - this->px * sa;
    }

    /**
     * @brief Vectorized 3-point interpolation for all trajectory fields.
     *
     * OPTIMIZATION: Performs all interpolations in a single function call,
     * avoiding overhead of multiple function calls and improving cache locality.
     *
     * @param x Target interpolation value.
     * @param ox0 Key value at point 0.
     * @param ox1 Key value at point 1.
     * @param ox2 Key value at point 2.
     * @param p0 Trajectory point 0.
     * @param p1 Trajectory point 1.
     * @param p2 Trajectory point 2.
     * @param out Output trajectory data.
     * @param skip_key Key being used for interpolation (set directly instead of interpolating).
     */
    void BCLIBC_BaseTrajData::interpolate3pt_vectorized(
        double x, double ox0, double ox1, double ox2,
        const BCLIBC_BaseTrajData &p0,
        const BCLIBC_BaseTrajData &p1,
        const BCLIBC_BaseTrajData &p2,
        BCLIBC_BaseTrajData &out,
        BCLIBC_BaseTrajData_InterpKey skip_key)
    {
        // Time: set directly if interpolating by time, otherwise interpolate
        out.time = (skip_key == BCLIBC_BaseTrajData_InterpKey::TIME)
                       ? x
                       : BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.time, p1.time, p2.time);

        // Position components - always interpolate
        out.px = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.px, p1.px, p2.px);
        out.py = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.py, p1.py, p2.py);
        out.pz = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.pz, p1.pz, p2.pz);

        // Velocity components - always interpolate
        out.vx = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.vx, p1.vx, p2.vx);
        out.vy = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.vy, p1.vy, p2.vy);
        out.vz = BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.vz, p1.vz, p2.vz);

        // Mach: set directly if interpolating by mach, otherwise interpolate
        out.mach = (skip_key == BCLIBC_BaseTrajData_InterpKey::MACH)
                       ? x
                       : BCLIBC_interpolate3pt(x, ox0, ox1, ox2, p0.mach, p1.mach, p2.mach);
    }

    // ============================================================================
    // Handler Compositor
    // ============================================================================

    BCLIBC_BaseTrajDataHandlerCompositor::~BCLIBC_BaseTrajDataHandlerCompositor() {}

    void BCLIBC_BaseTrajDataHandlerCompositor::handle(const BCLIBC_BaseTrajData &data)
    {
        for (auto *handler : handlers_)
        {
            handler->handle(data);
        }
    }

    // ============================================================================
    // Trajectory Sequence
    // ============================================================================

    BCLIBC_BaseTrajSeq::~BCLIBC_BaseTrajSeq()
    {
        BCLIBC_DEBUG("Dense buffer length/capacity: %zu/%zu, Size: %zu bytes",
                     this->get_length(), this->get_capacity(),
                     this->get_length() * sizeof(BCLIBC_BaseTrajData));
    }

    void BCLIBC_BaseTrajSeq::handle(const BCLIBC_BaseTrajData &data)
    {
        this->append(data);
    }

    /**
     * @brief Appends trajectory point to sequence.
     *
     * OPTIMIZATION: Uses std::vector::push_back for automatic memory management
     * and optimal reallocation strategy.
     */
    void BCLIBC_BaseTrajSeq::append(const BCLIBC_BaseTrajData &data)
    {
        this->buffer.push_back(data);
    }

    ssize_t BCLIBC_BaseTrajSeq::get_length() const
    {
        return this->buffer.size();
    }

    ssize_t BCLIBC_BaseTrajSeq::get_capacity() const
    {
        return this->buffer.capacity();
    }

    /**
     * @brief Retrieves trajectory element at index (supports negative indexing).
     *
     * @param idx Index (-1 for last element, etc.).
     * @return Pointer to element, or nullptr if out of bounds.
     */
    const BCLIBC_BaseTrajData &BCLIBC_BaseTrajSeq::get_item(ssize_t idx) const
    {
        ssize_t len = (ssize_t)this->buffer.size();

        // Handle negative indices
        if (idx < 0)
        {
            idx += len;
        }

        // Bounds check
        if (idx < 0 || idx >= len)
        {
            throw std::out_of_range("Index out of bounds");
        }
        return this->buffer[idx];
    }

    /**
     * @brief Retrieves trajectory data at specified key value with optional time filtering.
     *
     * OPTIMIZATION: Uses binary search for efficient lookup in large datasets.
     * Attempts exact match before falling back to interpolation.
     *
     * @param key_kind Type of key to search by.
     * @param key_value Target key value.
     * @param start_from_time Optional time threshold for search start.
     * @param out Output trajectory data.
     */
    void BCLIBC_BaseTrajSeq::get_at(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        double start_from_time,
        BCLIBC_BaseTrajData &out) const
    {
        const ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
        {
            throw std::domain_error("Insufficient data points for interpolation (need >= 3)");
        }

        ssize_t target_idx = -1;

        // Apply time-based filtering if requested
        if (start_from_time > 0.0 && key_kind != BCLIBC_BaseTrajData_InterpKey::TIME)
        {
            const ssize_t start_idx = this->find_start_index(start_from_time);

            // Try exact match at start
            try
            {
                this->try_get_exact(start_idx, key_kind, key_value, out);
                return;
            }
            catch (const std::exception &)
            {
                // Not an exact match, continue to interpolation
            }

            // Find interpolation target
            target_idx = this->find_target_index(key_kind, key_value, start_idx);
        }

        // If no time filtering or target not found, search entire range
        if (target_idx < 0)
        {
            const ssize_t center = this->bisect_center_idx_buf(key_kind, key_value);
            if (center < 0)
            {
                throw std::logic_error("Binary search failed");
            }
            target_idx = (center < n - 1) ? center : n - 2;
        }

        // Try exact match at target
        try
        {
            this->try_get_exact(target_idx, key_kind, key_value, out);
            return;
        }
        catch (const std::exception &)
        {
            // Not exact, proceed to interpolation
        }

        // Interpolate at center point
        const ssize_t center_idx = (target_idx < n - 1) ? target_idx : n - 2;
        this->interpolate_at_center(center_idx, key_kind, key_value, out);
    }

    /**
     * @brief Interpolates trajectory at specified slant height.
     *
     * Slant height is computed as: py * cos(angle) - px * sin(angle)
     *
     * @param look_angle_rad Look angle in radians.
     * @param value Target slant height.
     * @param out Output interpolated data.
     */
    void BCLIBC_BaseTrajSeq::get_at_slant_height(
        double look_angle_rad,
        double value,
        BCLIBC_BaseTrajData &out) const
    {
        const double ca = std::cos(look_angle_rad);
        const double sa = std::sin(look_angle_rad);
        const ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
        {
            throw std::domain_error("Insufficient data points for interpolation");
        }

        const ssize_t center = this->bisect_center_idx_slant_buf(ca, sa, value);
        if (center < 0)
        {
            throw std::runtime_error("Failed to locate interpolation center");
        }

        if (center < 1 || center >= n - 1)
        {
            throw std::out_of_range("Center index outside safe interpolation range");
        }

        // Cache data access
        const auto &data_vector = this->buffer;
        const BCLIBC_BaseTrajData &p0 = data_vector[center - 1];
        const BCLIBC_BaseTrajData &p1 = data_vector[center];
        const BCLIBC_BaseTrajData &p2 = data_vector[center + 1];

        // Compute slant key values
        const double ox0 = p0.slant_val_buf(ca, sa);
        const double ox1 = p1.slant_val_buf(ca, sa);
        const double ox2 = p2.slant_val_buf(ca, sa);

        if (ox0 == ox1 || ox1 == ox2)
        {
            throw std::domain_error("Degenerate slant values: cannot interpolate");
        }

        // Perform vectorized interpolation
        BCLIBC_BaseTrajData::interpolate3pt_vectorized(
            value, ox0, ox1, ox2, p0, p1, p2, out,
            BCLIBC_BaseTrajData_InterpKey::POS_Y); // Dummy skip key
    }

    void BCLIBC_BaseTrajSeq::interpolate_at_center(
        ssize_t idx,
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData &out) const
    {
        this->interpolate_at(idx, key_kind, key_value, out);
    }

    /**
     * @brief Performs 3-point PCHIP interpolation at specified index.
     *
     * Uses points at idx-1, idx, and idx+1 for interpolation.
     *
     * @param idx Center index for interpolation.
     * @param key_kind Independent variable for interpolation.
     * @param key_value Target value.
     * @param out Output interpolated data.
     */
    void BCLIBC_BaseTrajSeq::interpolate_at(
        ssize_t idx,
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData &out) const
    {
        const auto &data_vector = this->buffer;
        ssize_t length = (ssize_t)data_vector.size();

        // Handle negative indices
        if (idx < 0)
            idx += length;

        // Validate interpolation range
        if (idx < 1 || idx >= length - 1)
        {
            throw std::out_of_range("Index outside valid interpolation range [1, n-2]");
        }

        // Cache point references
        const BCLIBC_BaseTrajData &p0 = data_vector[idx - 1];
        const BCLIBC_BaseTrajData &p1 = data_vector[idx];
        const BCLIBC_BaseTrajData &p2 = data_vector[idx + 1];

        // Cache key values
        const double ox0 = p0.get_key_val(key_kind);
        const double ox1 = p1.get_key_val(key_kind);
        const double ox2 = p2.get_key_val(key_kind);

        // Validate non-degenerate
        if (ox0 == ox1 || ox0 == ox2 || ox1 == ox2)
        {
            throw std::invalid_argument("Duplicate key values: cannot interpolate");
        }

        // Perform vectorized interpolation
        BCLIBC_BaseTrajData::interpolate3pt_vectorized(
            key_value, ox0, ox1, ox2, p0, p1, p2, out, key_kind);
    }

    /**
     * @brief Attempts exact match at specified index.
     *
     * @throws std::runtime_error if not an exact match.
     */
    void BCLIBC_BaseTrajSeq::try_get_exact(
        ssize_t idx,
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData &out) const
    {
        if (idx < 0 || idx >= (ssize_t)this->buffer.size())
        {
            throw std::out_of_range("Index out of bounds");
        }

        constexpr double epsilon = 1e-9;

        if (this->is_close(this->buffer[idx].get_key_val(key_kind), key_value, epsilon))
        {
            out = this->get_item(idx);
            BCLIBC_DEBUG("Exact match found at index %zd", idx);
            return;
        }

        throw std::runtime_error("Not an exact match");
    }

    /**
     * @brief Binary search for interpolation center index.
     *
     * OPTIMIZATION: Uses bit shift for division and caches sequence properties.
     *
     * @param key_kind Key to search by.
     * @param key_value Target value.
     * @return Center index for 3-point interpolation [1, n-2], or -1 if insufficient data.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_buf(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value) const
    {
        const ssize_t n = (ssize_t)this->buffer.size();
        if (n < 3)
        {
            return -1;
        }

        const auto &data_vector = this->buffer;

        // Determine monotonicity
        const double v0 = data_vector[0].get_key_val(key_kind);
        const double vN = data_vector[n - 1].get_key_val(key_kind);
        const bool increasing = (vN >= v0);

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        // Binary search
        while (lo < hi)
        {
            const ssize_t mid = lo + ((hi - lo) >> 1); // Bit shift optimization
            const double vm = data_vector[mid].get_key_val(key_kind);

            if ((increasing && vm < key_value) || (!increasing && vm > key_value))
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

        // Clamp to valid interpolation range [1, n-2]
        if (lo < 1)
            lo = 1;
        if (lo > n - 2)
            lo = n - 2;

        return lo;
    }

    /**
     * @brief Binary search for slant height interpolation.
     *
     * @param ca Cosine of look angle.
     * @param sa Sine of look angle.
     * @param value Target slant value.
     * @return Center index [1, n-2], or -1 if insufficient data.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_slant_buf(
        double ca, double sa, double value) const
    {
        const ssize_t n = (ssize_t)this->buffer.size();
        if (n < 3)
            return -1;

        const auto &data_vector = this->buffer;

        // Determine monotonicity
        const double v0 = data_vector[0].slant_val_buf(ca, sa);
        const double vN = data_vector[n - 1].slant_val_buf(ca, sa);
        const bool increasing = (vN >= v0);

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        // Binary search
        while (lo < hi)
        {
            const ssize_t mid = lo + ((hi - lo) >> 1);
            const double vm = data_vector[mid].slant_val_buf(ca, sa);

            if ((increasing && vm < value) || (!increasing && vm > value))
                lo = mid + 1;
            else
                hi = mid;
        }

        // Clamp to [1, n-2]
        if (lo < 1)
            lo = 1;
        if (lo > n - 2)
            lo = n - 2;

        return lo;
    }

    /**
     * @brief Finds first index with time >= start_time.
     *
     * OPTIMIZATION: Uses binary search for large arrays (n > 10),
     * falls back to linear search for small arrays.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_start_index(double start_time) const
    {
        const ssize_t n = (ssize_t)this->buffer.size();
        const BCLIBC_BaseTrajData *buf = this->buffer.data();

        // Binary search for large arrays with monotonic time
        if (n > 10 && buf[0].time <= buf[n - 1].time)
        {
            ssize_t lo = 0, hi = n - 1;

            while (lo < hi)
            {
                const ssize_t mid = lo + ((hi - lo) >> 1);

                if (buf[mid].time < start_time)
                    lo = mid + 1;
                else
                    hi = mid;
            }

            return lo;
        }

        // Linear search for small arrays
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
     * @brief Finds target index for interpolation starting from start_idx.
     *
     * @param key_kind Type of key.
     * @param key_value Target key value.
     * @param start_idx Starting search index.
     * @return Target index, or -1 if not found.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_target_index(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        ssize_t start_idx) const
    {
        const ssize_t n = (ssize_t)this->buffer.size();

        if (n < 3)
        {
            return -1;
        }

        const BCLIBC_BaseTrajData *buf = this->buffer.data();

        // Determine monotonicity
        const double v0 = buf[0].get_key_val(key_kind);
        const double vN = buf[n - 1].get_key_val(key_kind);
        const bool increasing = (vN >= v0);

        // Handle extrapolation
        if (increasing)
        {
            if (key_value <= v0)
                return 1;
            if (key_value >= vN)
                return n - 2;
        }
        else
        {
            if (key_value >= v0)
                return 1;
            if (key_value <= vN)
                return n - 2;
        }

        // Binary search
        ssize_t lo = 0;
        ssize_t hi = n - 1;

        while (lo < hi)
        {
            const ssize_t mid = lo + ((hi - lo) >> 1);
            const double vm = buf[mid].get_key_val(key_kind);

            if ((increasing && vm < key_value) || (!increasing && vm > key_value))
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid;
            }
        }

        // Clamp to [1, n-2]
        if (lo < 1)
            return 1;
        if (lo > n - 2)
            return n - 2;

        return lo;
    }

    /**
     * @brief Checks if two doubles are approximately equal.
     */
    int BCLIBC_BaseTrajSeq::is_close(double a, double b, double epsilon)
    {
        return std::fabs(a - b) < epsilon;
    }

    // ============================================================================
    // BCLIBC_TrajectoryData
    // ============================================================================

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps &props,
        double time,
        const BCLIBC_V3dT &range_vector,
        const BCLIBC_V3dT &velocity_vector,
        double mach_arg,
        BCLIBC_TrajFlag flag)
        : time(time), flag(flag)
    {
        // Compute adjusted range with Coriolis correction
        const BCLIBC_V3dT adjusted_range = props.coriolis.adjust_range(time, range_vector);
        const double spin_drift = props.spin_drift(time);
        const double velocity = velocity_vector.mag();

        this->windage_ft = adjusted_range.z + spin_drift;

        // Get atmospheric conditions at current altitude
        double density_ratio_out, mach_out;
        props.atmo.update_density_factor_and_mach_for_altitude(
            range_vector.y, density_ratio_out, mach_out);

        // Precompute trigonometric values
        const double trajectory_angle = std::atan2(velocity_vector.y, velocity_vector.x);
        const double look_angle_cos = std::cos(props.look_angle);
        const double look_angle_sin = std::sin(props.look_angle);

        // Populate trajectory fields
        this->distance_ft = adjusted_range.x;
        this->velocity_fps = velocity;
        this->mach = velocity / (mach_arg != 0.0 ? mach_arg : mach_out);
        this->height_ft = adjusted_range.y;
        this->slant_height_ft = adjusted_range.y * look_angle_cos - adjusted_range.x * look_angle_sin;

        // Compute angles
        this->drop_angle_rad = BCLIBC_getCorrection(adjusted_range.x, adjusted_range.y) -
                               (adjusted_range.x ? props.look_angle : 0.0);
        this->windage_angle_rad = BCLIBC_getCorrection(adjusted_range.x, this->windage_ft);
        this->slant_distance_ft = adjusted_range.x * look_angle_cos + adjusted_range.y * look_angle_sin;
        this->angle_rad = trajectory_angle;

        // Physical properties
        this->density_ratio = density_ratio_out;
        this->drag = props.drag_by_mach(this->mach);
        this->energy_ft_lb = BCLIBC_calculateEnergy(props.weight, velocity);
        this->ogw_lb = BCLIBC_calculateOgw(props.weight, velocity);
    }

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps &props,
        const BCLIBC_BaseTrajData &data,
        BCLIBC_TrajFlag flag)
        : BCLIBC_TrajectoryData(props, data.time, data.position(), data.velocity(), data.mach, flag) {}

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps &props,
        const BCLIBC_FlaggedData &data)
        : BCLIBC_TrajectoryData(props, data.data, data.flag) {}

    /**
     * @brief Interpolates trajectory data using 3-point method.
     *
     * OPTIMIZATION: Uses switch statement for field access instead of reflection.
     * Minimizes repeated function calls by caching key values.
     *
     * @param key Independent variable for interpolation.
     * @param value Target interpolation value.
     * @param p0 First data point.
     * @param p1 Second data point.
     * @param p2 Third data point.
     * @param flag Output flag.
     * @param method Interpolation method (PCHIP or LINEAR).
     * @return Interpolated trajectory data.
     */
    BCLIBC_TrajectoryData BCLIBC_TrajectoryData::interpolate(
        BCLIBC_TrajectoryData_InterpKey key,
        double value,
        const BCLIBC_TrajectoryData &p0,
        const BCLIBC_TrajectoryData &p1,
        const BCLIBC_TrajectoryData &p2,
        BCLIBC_TrajFlag flag,
        BCLIBC_InterpMethod method)
    {
        // Validate key
        if ((int)key < 0 || (int)key > BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT)
        {
            throw std::logic_error("Cannot interpolate by unsupported key");
        }

        // Cache independent variable values
        const double x_val = value;
        const double x0 = p0.get_key_val(key);
        const double x1 = p1.get_key_val(key);
        const double x2 = p2.get_key_val(key);

        // Initialize output with p0 as base (fills derived fields)
        BCLIBC_TrajectoryData interpolated_data = p0;

        // Interpolate all fields
        for (int k = 0; k < BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT; k++)
        {
            const BCLIBC_TrajectoryData_InterpKey field_key = (BCLIBC_TrajectoryData_InterpKey)k;

            double interpolated_value;

            // If this is the independent variable, use target value directly
            if (field_key == key)
            {
                interpolated_value = x_val;
            }
            else
            {
                // Cache dependent variable values
                const double y0 = p0.get_key_val(field_key);
                const double y1 = p1.get_key_val(field_key);
                const double y2 = p2.get_key_val(field_key);

                if (method == BCLIBC_InterpMethod::PCHIP)
                {
                    interpolated_value = BCLIBC_interpolate3pt(x_val, x0, x1, x2, y0, y1, y2);
                }
                else if (method == BCLIBC_InterpMethod::LINEAR)
                {
                    BCLIBC_InterpStatus interp_status;

                    // Choose segment based on which side of x1 the target falls
                    if (x_val <= x1)
                    {
                        interp_status = BCLIBC_interpolate2pt(x_val, x0, y0, x1, y1, interpolated_value);
                    }
                    else
                    {
                        interp_status = BCLIBC_interpolate2pt(x_val, x1, y1, x2, y2, interpolated_value);
                    }

                    if (interp_status != BCLIBC_InterpStatus::SUCCESS)
                    {
                        throw std::domain_error("Linear interpolation failed: zero division");
                    }
                }
                else
                {
                    throw std::invalid_argument("Invalid interpolation method");
                }
            }

            // Set interpolated value
            interpolated_data.set_key_val(field_key, interpolated_value);
        }

        interpolated_data.flag = flag;
        return interpolated_data;
    }

    /**
     * @brief Retrieves field value by key.
     */
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
            return 0.0;
        }
    }

    /**
     * @brief Sets field value by key.
     */
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
        }
    }

} // namespace bclibc