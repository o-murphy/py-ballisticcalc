#ifndef BCLIBC_BASE_TRAJ_SEQ_HPP
#define BCLIBC_BASE_TRAJ_SEQ_HPP

#include <cstddef> // Required for std::ptrdiff_t
#include "bclibc/base_types.hpp"
#include "bclibc/interp.hpp"

// --- START CROSS-PLATFORM FIX ---
// ssize_t is a standard POSIX type. It must be defined manually only for MSVC.
#if defined(_MSC_VER)
// MSVC does not define ssize_t by default, but it defines specific types based on architecture.
// Use ptrdiff_t as the closest standard C++ type for signed size difference,
// which correctly resolves to __int64 on x64 and long on x86/ARM32.
// However, for maximum compatibility with C/POSIX APIs, an explicit definition is safer.

// Robust definition based on architecture:
#if defined(_WIN64) // For 64-bit platforms (x64, ARM64)
typedef __int64 ssize_t;
#else // For 32-bit platforms (x86, ARM32)
typedef long ssize_t;
#endif

#else
// For POSIX-compliant systems (Linux, macOS, etc.) and other compilers (GCC, Clang),
// ssize_t is included via standard headers like <sys/types.h> or <unistd.h>.
// To ensure full POSIX compatibility without redundancy, explicitly include the required header:
#include <unistd.h>
#endif
// --- END CROSS-PLATFORM FIX ---

namespace bclibc
{
    constexpr int BASE_TRAJ_SEQ_INTERP_KEY_ACTIVE_COUNT = 8;
    constexpr int BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT = 15;

    /**
     * @brief Keys for accessing specific fields within BCLIBC_BaseTrajData.
     *
     * Used as independent variable for interpolation or as field selector.
     */
    enum class BCLIBC_BaseTrajData_InterpKey
    {
        TIME,  ///< Flight time in seconds
        MACH,  ///< Mach number (velocity / speed of sound)
        POS_X, ///< Position x-coordinate (downrange distance)
        POS_Y, ///< Position y-coordinate (height/altitude)
        POS_Z, ///< Position z-coordinate (windage/crossrange)
        VEL_X, ///< Velocity x-component
        VEL_Y, ///< Velocity y-component
        VEL_Z, ///< Velocity z-component
    };

    /**
     * @brief Keys for accessing fields within BCLIBC_TrajectoryData.
     *
     * Includes all base trajectory fields plus derived ballistic properties.
     */
    enum class BCLIBC_TrajectoryData_InterpKey
    {
        TIME,           ///< Flight time in seconds
        DISTANCE,       ///< Downrange distance in feet
        VELOCITY,       ///< Total velocity magnitude in fps
        MACH,           ///< Mach number
        HEIGHT,         ///< Height/altitude in feet
        SLANT_HEIGHT,   ///< Perpendicular distance from sight line in feet
        DROP_ANGLE,     ///< Vertical angle correction in radians
        WINDAGE,        ///< Crossrange deflection in feet
        WINDAGE_ANGLE,  ///< Horizontal angle correction in radians
        SLANT_DISTANCE, ///< Distance along sight line in feet
        ANGLE,          ///< Trajectory angle (velocity vector angle) in radians
        DENSITY_RATIO,  ///< Air density ratio (current / standard)
        DRAG,           ///< Drag coefficient at current conditions
        ENERGY,         ///< Kinetic energy in ft-lb
        OGW,            ///< Optimal game weight in pounds
        FLAG            ///< Trajectory point classification
    };

    /**
     * @brief Minimal trajectory data point structure.
     *
     * Contains only essential ballistic state: position, velocity, time, and Mach.
     * Used for efficient storage in dense trajectory buffers.
     *
     * MEMORY LAYOUT: 8 doubles = 64 bytes (assuming 8-byte alignment)
     */
    struct BCLIBC_BaseTrajData
    {
    public:
        double time; ///< Flight time in seconds
        double px;   ///< Position x-coordinate (downrange)
        double py;   ///< Position y-coordinate (height)
        double pz;   ///< Position z-coordinate (windage)
        double vx;   ///< Velocity x-component
        double vy;   ///< Velocity y-component
        double vz;   ///< Velocity z-component
        double mach; ///< Mach number

        BCLIBC_BaseTrajData() = default;

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
        BCLIBC_BaseTrajData(
            double time,
            double px,
            double py,
            double pz,
            double vx,
            double vy,
            double vz,
            double mach);

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
        BCLIBC_BaseTrajData(
            double time,
            const BCLIBC_V3dT &position,
            const BCLIBC_V3dT &velocity,
            double mach);

        /**
         * @brief Returns position as 3D vector.
         * @return Position vector (px, py, pz).
         */
        BCLIBC_V3dT position() const { return {px, py, pz}; };

        /**
         * @brief Returns velocity as 3D vector.
         * @return Velocity vector (vx, vy, vz).
         */
        BCLIBC_V3dT velocity() const { return {vx, vy, vz}; };

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
        double operator[](BCLIBC_BaseTrajData_InterpKey key_kind) const;

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
        double slant_val_buf(double ca, double sa) const;

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
        static void interpolate(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            const BCLIBC_BaseTrajData &p0,
            const BCLIBC_BaseTrajData &p1,
            const BCLIBC_BaseTrajData &p2,
            BCLIBC_BaseTrajData &out);

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
        static void interpolate3pt_vectorized(
            double x, double ox0, double ox1, double ox2,
            const BCLIBC_BaseTrajData &p0, const BCLIBC_BaseTrajData &p1, const BCLIBC_BaseTrajData &p2,
            BCLIBC_BaseTrajData &out, BCLIBC_BaseTrajData_InterpKey skip_key);
    };

    /**
     * @brief Interface for handling trajectory data points.
     *
     * Allows implementing custom trajectory processors, loggers, or filters.
     */
    struct BCLIBC_BaseTrajDataHandlerInterface
    {
        virtual ~BCLIBC_BaseTrajDataHandlerInterface() = default;

        /**
         * @brief Distributes trajectory data to all registered handlers.
         *
         * Implements composite pattern for trajectory data processing.
         * Each handler receives the same data point.
         *
         * @param data Trajectory data to distribute.
         */
        virtual void handle(const BCLIBC_BaseTrajData &data) = 0;
    };

    using BCLIBC_BaseTrajDataHandlerCompositorIterator = std::vector<BCLIBC_BaseTrajDataHandlerInterface *>::iterator;

    /**
     * @brief Composite handler that distributes data to multiple handlers.
     *
     * Implements composite pattern for trajectory data processing pipelines.
     * Each registered handler receives every data point.
     */
    class BCLIBC_BaseTrajDataHandlerCompositor : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        std::vector<BCLIBC_BaseTrajDataHandlerInterface *> handlers;

    public:
        /**
         * @brief Constructs compositor with variadic list of handlers.
         * @param args Pointers to handler objects (not owned by compositor).
         */
        template <typename... Handlers>
        BCLIBC_BaseTrajDataHandlerCompositor(Handlers *...args)
            : handlers{args...} {}

        /**
         * @brief Distributes data point to all registered handlers.
         * @param data Trajectory data to distribute.
         */
        void handle(const BCLIBC_BaseTrajData &data) override;

        /**
         * @brief Adds a handler to the distribution list.
         * @param handler Pointer to handler (nullptr ignored).
         */
        void add_handler(BCLIBC_BaseTrajDataHandlerInterface *handler)
        {
            if (handler != nullptr)
            {
                handlers.push_back(handler);
            }
        }

        BCLIBC_BaseTrajDataHandlerCompositorIterator begin() { return handlers.begin(); }

        BCLIBC_BaseTrajDataHandlerCompositorIterator end() { return handlers.end(); }

        /**
         * @brief Inserts a new trajectory data handler at a specified position.
         *
         * This function inserts the specified handler into the internal container
         * 'handlers_' immediately BEFORE the element pointed to by the 'position' iterator.
         * If the provided 'handler' is nullptr, the insertion operation is ignored.
         *
         * @param position An iterator specifying the position before which the handler will be inserted.
         * Use handlers_.end() to insert the element at the end of the container.
         * @param handler A pointer to the trajectory data handler (BCLIBC_BaseTrajDataHandlerInterface*)
         * to be added.
         */
        void insert_handler(BCLIBC_BaseTrajDataHandlerCompositorIterator position, BCLIBC_BaseTrajDataHandlerInterface *handler)
        {
            if (handler != nullptr)
            {
                handlers.insert(position, handler);
            }
        }

        ~BCLIBC_BaseTrajDataHandlerCompositor() override;
    };

    /**
     * @brief Dense sequence of trajectory data points with interpolation support.
     *
     * Stores trajectory points in contiguous memory (std::vector) for efficient access.
     * Provides binary search, exact matching, and 3-point PCHIP interpolation.
     *
     * TYPICAL USAGE:
     * 1. Append points during trajectory simulation
     * 2. Query specific values using get_at() or get_at_slant_height()
     * 3. Points automatically retrieved via exact match or interpolation
     */
    class BCLIBC_BaseTrajSeq : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        std::vector<BCLIBC_BaseTrajData> buffer;

    public:
        BCLIBC_BaseTrajSeq() = default;

        /**
         * @brief Destructor - logs buffer statistics for debugging.
         *
         * Outputs final buffer size and memory usage to help with capacity planning.
         */
        ~BCLIBC_BaseTrajSeq();

        /**
         * @brief Handler interface implementation - appends data to sequence.
         *
         * Allows trajectory sequence to be used as a handler in data processing pipelines.
         *
         * @param data Trajectory data to append.
         */
        void handle(const BCLIBC_BaseTrajData &data) override;

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
        void append(const BCLIBC_BaseTrajData &data);

        /**
         * @brief Returns the number of trajectory points in the sequence.
         *
         * @return Number of elements, always >= 0.
         */
        ssize_t get_length() const;

        /**
         * @brief Returns the allocated capacity of the internal buffer.
         *
         * Capacity >= length. Capacity increases geometrically during growth.
         *
         * @return Current capacity (number of elements that can be stored without reallocation).
         */
        ssize_t get_capacity() const;

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
        const BCLIBC_BaseTrajData &operator[](ssize_t idx) const;

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
        void get_at(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            double start_from_time,
            BCLIBC_BaseTrajData &out) const;

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
        void get_at_slant_height(
            double look_angle_rad,
            double value,
            BCLIBC_BaseTrajData &out) const;

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
        void interpolate_at(
            ssize_t idx,
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData &out) const;

    private:
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
        void try_get_exact(
            ssize_t idx,
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData &out) const;

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
        ssize_t bisect_center_idx_buf(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value) const;

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
        ssize_t bisect_center_idx_slant_buf(
            double ca,
            double sa,
            double value) const;

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
        ssize_t find_start_index(double start_time) const;

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
        ssize_t find_target_index(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            ssize_t start_idx) const;

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
        static int is_close(double a, double b, double epsilon);
    };

    /**
     * @brief Base trajectory data with associated flag.
     *
     * Used to tag trajectory points with classification (e.g., zero crossing, apex).
     */
    struct BCLIBC_FlaggedData
    {
        BCLIBC_BaseTrajData data; ///< Trajectory data
        BCLIBC_TrajFlag flag;     ///< Classification flag
    };

    /**
     * @brief Complete trajectory data with all derived ballistic properties.
     *
     * Extends base trajectory data with:
     * - Atmospheric corrections (density, drag)
     * - Coriolis and spin drift effects
     * - Angular measurements (drop, windage angles)
     * - Energy and optimal game weight
     *
     * MEMORY: 16 doubles + 1 flag = ~136 bytes (with padding)
     */
    struct BCLIBC_TrajectoryData
    {
    public:
        // Core trajectory fields
        double time = 0.0;                            ///< Flight time in seconds
        double distance_ft = 0.0;                     ///< Downrange distance (x-axis)
        double velocity_fps = 0.0;                    ///< Total velocity magnitude
        double mach = 0.0;                            ///< Mach number
        double height_ft = 0.0;                       ///< Height/altitude (y-axis)
        double slant_height_ft = 0.0;                 ///< Distance perpendicular to sight line
        double drop_angle_rad = 0.0;                  ///< Vertical angle correction
        double windage_ft = 0.0;                      ///< Crossrange deflection (z-axis)
        double windage_angle_rad = 0.0;               ///< Horizontal angle correction
        double slant_distance_ft = 0.0;               ///< Distance along sight line
        double angle_rad = 0.0;                       ///< Trajectory angle (velocity vector)
        double density_ratio = 0.0;                   ///< Air density / standard density
        double drag = 0.0;                            ///< Drag coefficient
        double energy_ft_lb = 0.0;                    ///< Kinetic energy
        double ogw_lb = 0.0;                          ///< Optimal game weight
        BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE; ///< Point classification

        // Constructors
        BCLIBC_TrajectoryData() = default;
        BCLIBC_TrajectoryData(const BCLIBC_TrajectoryData &) = default;
        BCLIBC_TrajectoryData &operator=(const BCLIBC_TrajectoryData &) = default;
        BCLIBC_TrajectoryData(BCLIBC_TrajectoryData &&) = default;
        BCLIBC_TrajectoryData &operator=(BCLIBC_TrajectoryData &&) = default;
        ~BCLIBC_TrajectoryData() = default;

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
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            double time,
            const BCLIBC_V3dT &range_vector,
            const BCLIBC_V3dT &velocity_vector,
            double mach,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        /**
         * @brief Constructs trajectory data from base trajectory data and shot properties.
         *
         * Convenience constructor that delegates to main constructor.
         *
         * @param props Shot properties.
         * @param data Base trajectory data (position, velocity, time, Mach).
         * @param flag Trajectory point classification flag.
         */
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_BaseTrajData &data,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        /**
         * @brief Constructs trajectory data from flagged data structure.
         *
         * Convenience constructor that extracts flag from flagged data.
         *
         * @param props Shot properties.
         * @param data Flagged trajectory data (includes flag field).
         */
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_FlaggedData &data);

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
        static BCLIBC_TrajectoryData interpolate(
            BCLIBC_TrajectoryData_InterpKey key,
            double value,
            const BCLIBC_TrajectoryData &t0,
            const BCLIBC_TrajectoryData &t1,
            const BCLIBC_TrajectoryData &t2,
            BCLIBC_TrajFlag flag,
            BCLIBC_InterpMethod method = BCLIBC_InterpMethod::PCHIP);

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
        double operator[](BCLIBC_TrajectoryData_InterpKey key) const;

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
        void set_key_val(BCLIBC_TrajectoryData_InterpKey key, double value);
    };

}; // namespace bclibc

#endif // BCLIBC_BASE_TRAJ_SEQ_HPP
