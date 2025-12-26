#include <cmath>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include "bclibc/traj_data.hpp"
#include "bclibc/log.hpp"

namespace bclibc
{
    /**
     * @brief Constructs trajectory data from individual scalar components.
     *
     * Direct member initialization - most efficient for known scalar values.
     *
     * @param time Flight time in seconds.
     * @param px Position x-coordinate (downrange).
     * @param py Position y-coordinate (height).
     * @param pz Position z-coordinate (windage).
     * @param vx Velocity x-component.
     * @param vy Velocity y-component.
     * @param vz Velocity z-component.
     * @param mach Mach number.
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
     * Extracts vector components during initialization.
     *
     * @param time Flight time in seconds.
     * @param position Position vector (x=downrange, y=height, z=windage).
     * @param velocity Velocity vector (x, y, z components).
     * @param mach Mach number.
     */
    BCLIBC_BaseTrajData::BCLIBC_BaseTrajData(
        double time,
        const BCLIBC_V3dT &position,
        const BCLIBC_V3dT &velocity,
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
     * ALGORITHM:
     * 1. Extract and cache key values from p0, p1, p2
     * 2. Validate non-degenerate (no duplicate key values)
     * 3. For each field:
     *    - If field == key_kind: set directly to key_value
     *    - Otherwise: perform PCHIP interpolation
     *
     * OPTIMIZATION: Caches key values and uses direct field access instead of
     * repeated operator[]() calls. Avoids creating intermediate vector objects.
     *
     * @param key_kind The field to use as independent variable (TIME, MACH, POS_X, etc.).
     * @param key_value Target value for interpolation.
     * @param p0 First data point (before target).
     * @param p1 Second data point (center).
     * @param p2 Third data point (after target).
     * @param out Output parameter - populated with interpolated result.
     *
     * @throws std::domain_error if any two key values are equal (degenerate segment).
     *
     * @note This is equivalent to interpolate3pt_vectorized but with skip_key logic.
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
        const double x0 = p0[key_kind];
        const double x1 = p1[key_kind];
        const double x2 = p2[key_kind];

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
     * Maps enum keys to struct members via switch statement.
     *
     * PERFORMANCE: O(1) with compiler optimization (likely jump table).
     *
     * @param key_kind The field to retrieve (TIME, MACH, POS_X, etc.).
     * @return Value of the specified field, or 0.0 if key is invalid/out of range.
     *
     * @note Returns 0.0 for invalid keys rather than throwing to avoid exceptions in hot paths.
     */
    double BCLIBC_BaseTrajData::operator[](BCLIBC_BaseTrajData_InterpKey key_kind) const
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
     * Slant height represents the perpendicular distance from the line of sight.
     * This is used for ballistic calculations where the shooter is at an angle.
     *
     * Formula: slant_height = py * cos(angle) - px * sin(angle)
     *
     * OPTIMIZATION: Takes precomputed cos/sin to avoid repeated trig calculations.
     *
     * @param ca Cosine of look angle.
     * @param sa Sine of look angle.
     * @return Computed slant height value.
     *
     * @note Positive slant height means target is above line of sight.
     * @note This is projection onto line perpendicular to sight line.
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
     * All 8 trajectory components are interpolated in one pass.
     *
     * KEY DIFFERENCE vs interpolate(): The independent variable values (ox0, ox1, ox2)
     * are provided directly instead of being extracted via key_kind lookup.
     *
     * @param x Target interpolation value (on independent variable axis).
     * @param ox0 Independent variable value at point 0.
     * @param ox1 Independent variable value at point 1.
     * @param ox2 Independent variable value at point 2.
     * @param p0 Trajectory point 0.
     * @param p1 Trajectory point 1.
     * @param p2 Trajectory point 2.
     * @param out Output trajectory data - populated with interpolated values.
     * @param skip_key Key being used as independent variable - this field is set
     *                 directly to x instead of being interpolated (TIME or MACH typically).
     *
     * @note Static method - can be called without instance.
     * @note Assumes caller has validated non-degenerate segments (ox0 != ox1 != ox2).
     *
     * @example
     * // Interpolate at distance = 1000ft using cached distance values
     * BCLIBC_BaseTrajData::interpolate3pt_vectorized(
     *     1000.0, 900.0, 1000.0, 1100.0,  // x, ox0, ox1, ox2
     *     p0, p1, p2, result,
     *     BCLIBC_BaseTrajData_InterpKey::POS_X
     * );
     * // result.px will be 1000.0, other fields interpolated
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

    /**
     * @brief Distributes trajectory data to all registered handlers.
     *
     * Implements composite pattern for trajectory data processing.
     * Each handler receives the same data point.
     *
     * @param data Trajectory data to distribute.
     */
    void BCLIBC_BaseTrajDataHandlerCompositor::handle(const BCLIBC_BaseTrajData &data)
    {
        for (auto *handler : handlers)
        {
            handler->handle(data);
        }
    }

    // ============================================================================
    // Trajectory Sequence
    // ============================================================================

    /**
     * @brief Destructor - logs buffer statistics for debugging.
     *
     * Outputs final buffer size and memory usage to help with capacity planning.
     */
    BCLIBC_BaseTrajSeq::~BCLIBC_BaseTrajSeq()
    {
        BCLIBC_DEBUG("Dense buffer length/capacity: %zu/%zu, Size: %zu bytes",
                     this->get_length(), this->get_capacity(),
                     this->get_length() * sizeof(BCLIBC_BaseTrajData));
    }

    /**
     * @brief Handler interface implementation - appends data to sequence.
     *
     * Allows trajectory sequence to be used as a handler in data processing pipelines.
     *
     * @param data Trajectory data to append.
     */
    void BCLIBC_BaseTrajSeq::handle(const BCLIBC_BaseTrajData &data)
    {
        this->append(data);
    }

    /**
     * @brief Appends trajectory point to sequence.
     *
     * OPTIMIZATION: Uses std::vector::push_back for automatic memory management
     * and optimal reallocation strategy (typically 1.5x or 2x growth factor).
     *
     * AMORTIZED COMPLEXITY: O(1) - occasional reallocations are amortized.
     *
     * @param data Trajectory data to append (copied into internal buffer).
     */
    void BCLIBC_BaseTrajSeq::append(const BCLIBC_BaseTrajData &data)
    {
        this->buffer.push_back(data);
    }

    /**
     * @brief Returns the number of trajectory points in the sequence.
     *
     * @return Number of elements, always >= 0.
     */
    ssize_t BCLIBC_BaseTrajSeq::get_length() const
    {
        return this->buffer.size();
    }

    /**
     * @brief Returns the allocated capacity of the internal buffer.
     *
     * Capacity >= length. Capacity increases geometrically during growth.
     *
     * @return Current capacity (number of elements that can be stored without reallocation).
     */
    ssize_t BCLIBC_BaseTrajSeq::get_capacity() const
    {
        return this->buffer.capacity();
    }

    /**
     * @brief Retrieves trajectory element at index (supports negative indexing).
     *
     * Python-style indexing: -1 returns last element, -2 returns second-to-last, etc.
     *
     * COMPLEXITY: O(1) - direct array access after index normalization.
     *
     * @param idx Index to retrieve (negative indices count from end).
     * @return Const reference to trajectory data at index.
     * @throws std::out_of_range if index is out of bounds after normalization.
     */
    const BCLIBC_BaseTrajData &BCLIBC_BaseTrajSeq::operator[](ssize_t idx) const
    {
        const ssize_t len = static_cast<ssize_t>(this->buffer.size());

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
     * ALGORITHM:
     * 1. If start_from_time > 0 && key != TIME:
     *    a. Binary search for time >= start_from_time
     *    b. Check for exact match at start index
     *    c. Binary search from start_idx to find target
     * 2. Otherwise: Binary search entire sequence
     * 3. Check for exact match at target (within epsilon=1e-9)
     * 4. If no exact match: Interpolate using 3-point PCHIP
     *
     * OPTIMIZATION:
     * - Binary search: O(log n) instead of linear scan
     * - Exact match avoids expensive PCHIP computation
     * - Time filtering reduces search space for time-series queries
     *
     * @param key_kind Type of key to search by (TIME, MACH, POS_X, etc.).
     * @param key_value Target key value to retrieve/interpolate.
     * @param start_from_time Time threshold - only search data with time >= this value.
     *                        Use 0.0 or negative to disable time filtering.
     * @param out Output parameter - populated with exact or interpolated trajectory data.
     *
     * @throws std::domain_error if sequence has fewer than 3 points.
     * @throws std::logic_error if binary search fails.
     * @throws std::invalid_argument if interpolation encounters duplicate key values.
     *
     * @note For TIME key, start_from_time is ignored (would be circular).
     * @note Uses try_get_exact internally which throws on no-match (control flow exception pattern).
     */
    void BCLIBC_BaseTrajSeq::get_at(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        double start_from_time,
        BCLIBC_BaseTrajData &out) const
    {
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());

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
        this->interpolate_at(center_idx, key_kind, key_value, out);
    }

    /**
     * @brief Interpolates trajectory at specified slant height.
     *
     * Slant height formula: h_slant = py * cos(angle) - px * sin(angle)
     * Represents perpendicular distance from line of sight.
     *
     * ALGORITHM:
     * 1. Binary search to find 3-point bracket (uses slant values)
     * 2. Validate center is in safe range [1, n-2]
     * 3. Compute slant values for p0, p1, p2 using precomputed cos/sin
     * 4. Validate non-degenerate (no duplicate slant values)
     * 5. Perform vectorized 3-point PCHIP interpolation
     *
     * @param look_angle_rad Look angle in radians (angle of line of sight from horizontal).
     * @param value Target slant height value.
     * @param out Output parameter - populated with interpolated trajectory data.
     *
     * @throws std::domain_error if sequence has < 3 points or slant values are degenerate.
     * @throws std::runtime_error if binary search fails to find valid bracket.
     * @throws std::out_of_range if center index outside safe range [1, n-2].
     *
     * @note Slant height may be non-monotonic, binary search assumes local monotonicity.
     * @note Uses POS_Y as dummy skip_key (not actually relevant for slant interpolation).
     */
    void BCLIBC_BaseTrajSeq::get_at_slant_height(
        double look_angle_rad,
        double value,
        BCLIBC_BaseTrajData &out) const
    {
        const double ca = std::cos(look_angle_rad);
        const double sa = std::sin(look_angle_rad);
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());

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
        const BCLIBC_BaseTrajData &p0 = this->buffer[center - 1];
        const BCLIBC_BaseTrajData &p1 = this->buffer[center];
        const BCLIBC_BaseTrajData &p2 = this->buffer[center + 1];

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

    /**
     * @brief Performs 3-point PCHIP interpolation at specified index.
     *
     * Uses trajectory points at [idx-1, idx, idx+1] as interpolation bracket.
     * The "center" point is at idx, which should be close to the target value.
     *
     * VALID RANGE: idx must be in [1, n-2] to ensure all three points exist.
     *
     * @param idx Center index for interpolation (supports negative indexing).
     * @param key_kind Independent variable for interpolation (TIME, MACH, etc.).
     * @param key_value Target value of the independent variable.
     * @param out Output parameter - populated with interpolated trajectory data.
     *
     * @throws std::out_of_range if idx outside valid range [1, n-2] after normalization.
     * @throws std::invalid_argument if key values at three points are not distinct.
     *
     * @note All fields interpolated except key_kind, which is set directly to key_value.
     */
    void BCLIBC_BaseTrajSeq::interpolate_at(
        ssize_t idx,
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData &out) const
    {
        const ssize_t length = static_cast<ssize_t>(this->buffer.size());

        // Handle negative indices
        if (idx < 0)
            idx += length;

        // Validate interpolation range
        if (idx < 1 || idx >= length - 1)
        {
            throw std::out_of_range("Index outside valid interpolation range [1, n-2]");
        }

        // Cache point references
        const BCLIBC_BaseTrajData &p0 = this->buffer[idx - 1];
        const BCLIBC_BaseTrajData &p1 = this->buffer[idx];
        const BCLIBC_BaseTrajData &p2 = this->buffer[idx + 1];

        // Cache key values
        const double ox0 = p0[key_kind];
        const double ox1 = p1[key_kind];
        const double ox2 = p2[key_kind];

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
     * @brief Attempts to retrieve exact trajectory data at index if key matches.
     *
     * Checks if trajectory data at idx has key value matching key_value within
     * tolerance (epsilon = 1e-9). If match found, copies data to out.
     *
     * OPTIMIZATION: Avoids expensive PCHIP interpolation when exact data exists.
     * This is common when querying at measured data points.
     *
     * @param idx Index to check for exact match.
     * @param key_kind Type of key to compare.
     * @param key_value Target key value to match.
     * @param out Output parameter - populated only if exact match found.
     *
     * @throws std::out_of_range if idx is out of bounds.
     * @throws std::runtime_error if key value does not match within tolerance.
     *
     * @note Uses exception for control flow (try_get pattern).
     * @note Primarily used internally by get_at() to optimize exact lookups.
     * @note Consider refactoring to return bool instead of throwing for cleaner API.
     */
    void BCLIBC_BaseTrajSeq::try_get_exact(
        ssize_t idx,
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData &out) const
    {
        if (idx < 0 || idx >= static_cast<ssize_t>(this->buffer.size()))
        {
            throw std::out_of_range("Index out of bounds");
        }

        constexpr double epsilon = 1e-9;

        if (this->is_close(this->buffer[idx][key_kind], key_value, epsilon))
        {
            BCLIBC_DEBUG("Exact match found at index %zd", idx);
            out = (*this)[idx];
            return;
        }

        throw std::runtime_error("Not an exact match");
    }

    /**
     * @brief Binary search for 3-point interpolation bracket.
     *
     * Locates index 'center' such that:
     * - Points at [center-1, center, center+1] bracket the key_value
     * - center ∈ [1, n-2] (valid range for 3-point interpolation)
     * - Handles both monotonically increasing and decreasing sequences
     *
     * ALGORITHM:
     * 1. Determine sequence monotonicity (compare endpoints)
     * 2. Standard binary search: O(log n)
     * 3. Clamp result to [1, n-2]
     *
     * OPTIMIZATION: Uses bit shift (>> 1) for midpoint calculation.
     *
     * @param key_kind Type of key to search by.
     * @param key_value Target key value to bracket.
     * @return Center index for 3-point interpolation [1, n-2], or -1 if n < 3.
     *
     * @note Returns -1 if sequence too short for interpolation.
     * @note Assumes sequence is monotonic in key_kind (no validation).
     * @note For non-monotonic sequences, result is undefined.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_buf(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value) const
    {
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());
        if (n < 3)
        {
            return -1;
        }

        // Determine monotonicity
        const double v0 = this->buffer[0][key_kind];
        const double vN = this->buffer[n - 1][key_kind];
        const bool increasing = (vN >= v0);

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        // Binary search
        while (lo < hi)
        {
            const ssize_t mid = lo + ((hi - lo) >> 1); // Bit shift optimization
            const double vm = this->buffer[mid][key_kind];

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
     * @brief Binary search for slant height interpolation bracket.
     *
     * Similar to bisect_center_idx_buf but searches by computed slant height values.
     * Slant height = py * cos(angle) - px * sin(angle)
     *
     * OPTIMIZATION: Takes precomputed cos/sin to avoid repeated trig calculations
     * during binary search (would be O(n log n) otherwise).
     *
     * @param ca Cosine of look angle (precomputed).
     * @param sa Sine of look angle (precomputed).
     * @param value Target slant height value to bracket.
     * @return Center index in [1, n-2], or -1 if n < 3.
     *
     * @note Slant height computed on-the-fly during search.
     * @note Assumes slant values are locally monotonic.
     */
    ssize_t BCLIBC_BaseTrajSeq::bisect_center_idx_slant_buf(
        double ca, double sa, double value) const
    {
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());
        if (n < 3)
            return -1;

        // Determine monotonicity
        const double v0 = this->buffer[0].slant_val_buf(ca, sa);
        const double vN = this->buffer[n - 1].slant_val_buf(ca, sa);
        const bool increasing = (vN >= v0);

        ssize_t lo = 0;
        ssize_t hi = n - 1;

        // Binary search
        while (lo < hi)
        {
            const ssize_t mid = lo + ((hi - lo) >> 1);
            const double vm = this->buffer[mid].slant_val_buf(ca, sa);

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
     * @brief Finds first index where trajectory time >= start_time.
     *
     * OPTIMIZATION STRATEGY:
     * - Large arrays (n > 10) with monotonic time: Binary search O(log n)
     * - Small arrays or non-monotonic time: Linear search O(n)
     *
     * Rationale: Binary search overhead not worth it for small arrays.
     * Monotonicity check: buffer[0].time <= buffer[n-1].time
     *
     * @param start_time Time threshold to search for.
     * @return Index of first point with time >= start_time, or n-1 if none found.
     *
     * @note Returns n-1 (last index) if all points have time < start_time.
     * @note Linear search used for small/non-monotonic sequences for simplicity.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_start_index(double start_time) const
    {
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());
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
     * @brief Finds target index for interpolation within bounded search range.
     *
     * Similar to bisect_center_idx_buf but with additional edge case handling:
     * - If key_value outside sequence range, returns nearest valid interpolation index
     * - Handles both increasing and decreasing monotonic sequences
     *
     * EDGE CASES:
     * - key_value <= first value: returns 1 (minimum valid center)
     * - key_value >= last value: returns n-2 (maximum valid center)
     * - Otherwise: binary search for bracket
     *
     * @param key_kind Type of key to search by.
     * @param key_value Target key value.
     * @param start_idx Starting search index (currently unused - searches full range).
     * @return Target index in [1, n-2], or -1 if n < 3.
     *
     * @note start_idx parameter currently ignored (TODO: optimize to use it).
     * @note Extrapolation is clamped to valid interpolation range.
     */
    ssize_t BCLIBC_BaseTrajSeq::find_target_index(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double key_value,
        ssize_t start_idx) const
    {
        const ssize_t n = static_cast<ssize_t>(this->buffer.size());

        if (n < 3)
        {
            return -1;
        }

        const BCLIBC_BaseTrajData *buf = this->buffer.data();

        // Determine monotonicity
        const double v0 = buf[0][key_kind];
        const double vN = buf[n - 1][key_kind];
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
            const double vm = buf[mid][key_kind];

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
     * @brief Checks if two doubles are approximately equal within tolerance.
     *
     * Uses absolute difference comparison: |a - b| < epsilon
     *
     * LIMITATION: Only checks absolute error, not relative error.
     * This is appropriate for trajectory data where values have similar magnitudes.
     *
     * @param a First value.
     * @param b Second value.
     * @param epsilon Tolerance threshold (typically 1e-9).
     * @return 1 if |a - b| < epsilon, 0 otherwise.
     *
     * @note Static method - no instance required.
     * @note Does not handle special float values (NaN, infinity).
     */
    int BCLIBC_BaseTrajSeq::is_close(double a, double b, double epsilon)
    {
        return std::fabs(a - b) < epsilon;
    }

    // ============================================================================
    // BCLIBC_TrajectoryData
    // ============================================================================

    /**
     * @brief Constructs full trajectory data from ballistic state and shot properties.
     *
     * Computes all derived trajectory fields from basic state (position, velocity, time).
     * This includes:
     * - Atmospheric corrections (density, Mach, drag)
     * - Coriolis effect (range adjustment)
     * - Spin drift (windage correction)
     * - Angular measurements (drop angle, windage angle)
     * - Energy and optimal game weight
     *
     * ALGORITHM:
     * 1. Apply Coriolis correction to range vector
     * 2. Compute spin drift and add to windage
     * 3. Get atmospheric density and speed of sound at current altitude
     * 4. Compute slant range and angles relative to sight line
     * 5. Calculate energy and derived ballistic properties
     *
     * @param props Shot properties (atmosphere, Coriolis, drag model, etc.).
     * @param time Flight time in seconds.
     * @param range_vector Position vector (x=downrange, y=height, z=windage).
     * @param velocity_vector Velocity vector (x, y, z components).
     * @param mach_arg Mach number (or 0.0 to compute from altitude).
     * @param flag Trajectory point classification flag.
     */
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

    /**
     * @brief Constructs trajectory data from base trajectory data and shot properties.
     *
     * Convenience constructor that delegates to main constructor.
     *
     * @param props Shot properties.
     * @param data Base trajectory data (position, velocity, time, Mach).
     * @param flag Trajectory point classification flag.
     */
    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps &props,
        const BCLIBC_BaseTrajData &data,
        BCLIBC_TrajFlag flag)
        : BCLIBC_TrajectoryData(props, data.time, data.position(), data.velocity(), data.mach, flag) {}

    /**
     * @brief Constructs trajectory data from flagged data structure.
     *
     * Convenience constructor that extracts flag from flagged data.
     *
     * @param props Shot properties.
     * @param data Flagged trajectory data (includes flag field).
     */
    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps &props,
        const BCLIBC_FlaggedData &data)
        : BCLIBC_TrajectoryData(props, data.data, data.flag) {}

    /**
     * @brief Interpolates full trajectory data using 3-point method.
     *
     * ALGORITHM:
     * 1. Validate key is in valid range
     * 2. Cache independent variable values (x0, x1, x2)
     * 3. Initialize output with p0 as template
     * 4. For each field:
     *    - If field == key: set directly to value
     *    - Otherwise: interpolate using PCHIP or LINEAR method
     * 5. Set output flag
     *
     * OPTIMIZATION: Uses switch statement for field access instead of reflection.
     * Caches key values to avoid repeated operator[]() calls.
     *
     * METHOD COMPARISON:
     * - PCHIP: Monotone-preserving cubic, smooth, better for most trajectories
     * - LINEAR: Piecewise linear, faster but less accurate, segments chosen by x1
     *
     * @param key Independent variable for interpolation (TIME, DISTANCE, MACH, etc.).
     * @param value Target interpolation value.
     * @param p0 First trajectory point.
     * @param p1 Second trajectory point (center).
     * @param p2 Third trajectory point.
     * @param flag Output trajectory flag.
     * @param method Interpolation method (PCHIP or LINEAR).
     * @return Interpolated trajectory data with all fields populated.
     *
     * @throws std::logic_error if key is invalid/unsupported.
     * @throws std::domain_error if linear interpolation encounters zero division.
     * @throws std::invalid_argument if method is unknown.
     *
     * @note All 15 trajectory fields are interpolated independently.
     * @note For LINEAR method: uses [p0,p1] if value <= x1, else [p1,p2].
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
        const double x0 = p0[key];
        const double x1 = p1[key];
        const double x2 = p2[key];

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
                const double y0 = p0[field_key];
                const double y1 = p1[field_key];
                const double y2 = p2[field_key];

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
     *
     * Maps enum keys to trajectory data members via switch statement.
     *
     * PERFORMANCE: O(1) with compiler optimization (likely jump table).
     *
     * @param key Field identifier (TIME, DISTANCE, VELOCITY, etc.).
     * @return Value of specified field, or 0.0 if key invalid.
     */
    double BCLIBC_TrajectoryData::operator[](BCLIBC_TrajectoryData_InterpKey key) const
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
     *
     * Maps enum keys to trajectory data members for modification.
     * Used during interpolation to populate output structure.
     *
     * @param key Field identifier.
     * @param value New value to set.
     *
     * @note No-op for invalid keys (silently ignored).
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

}; // namespace bclibc
