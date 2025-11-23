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
         * @brief Constructs from individual scalar components.
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
         * @brief Constructs from position and velocity vectors.
         * @param time Flight time in seconds.
         * @param position Position vector (x, y, z).
         * @param velocity Velocity vector (x, y, z).
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
         * @brief Retrieves value of specified field.
         * @param key_kind Field to retrieve.
         * @return Field value, or 0.0 if invalid key.
         */
        double get_key_val(BCLIBC_BaseTrajData_InterpKey key_kind) const;

        /**
         * @brief Computes slant height using precomputed trig values.
         * @param ca Cosine of look angle.
         * @param sa Sine of look angle.
         * @return Slant height = py*cos(angle) - px*sin(angle).
         */
        double slant_val_buf(double ca, double sa) const;

        /**
         * @brief Interpolates trajectory data using 3-point PCHIP method.
         *
         * All fields are interpolated based on the specified key as independent variable.
         *
         * @param key_kind Independent variable (TIME, MACH, etc.).
         * @param key_value Target value of independent variable.
         * @param p0 First data point.
         * @param p1 Second data point (center).
         * @param p2 Third data point.
         * @param out Output parameter for interpolated result.
         * @throws std::domain_error if key values are degenerate (duplicates).
         */
        static void interpolate(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            const BCLIBC_BaseTrajData &p0,
            const BCLIBC_BaseTrajData &p1,
            const BCLIBC_BaseTrajData &p2,
            BCLIBC_BaseTrajData &out);

        /**
         * @brief Vectorized 3-point interpolation with explicit key values.
         *
         * Optimized version that avoids repeated get_key_val() calls.
         * All 8 trajectory components interpolated in single pass.
         *
         * @param x Target interpolation value.
         * @param ox0 Independent variable at point 0.
         * @param ox1 Independent variable at point 1.
         * @param ox2 Independent variable at point 2.
         * @param p0 Trajectory point 0.
         * @param p1 Trajectory point 1.
         * @param p2 Trajectory point 2.
         * @param out Output trajectory data.
         * @param skip_key Field to set directly instead of interpolating.
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
         * @brief Processes a single trajectory data point.
         * @param data Trajectory data to handle.
         */
        virtual void handle(const BCLIBC_BaseTrajData &data) = 0;
    };

    /**
     * @brief Composite handler that distributes data to multiple handlers.
     *
     * Implements composite pattern for trajectory data processing pipelines.
     * Each registered handler receives every data point.
     */
    class BCLIBC_BaseTrajDataHandlerCompositor : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        std::vector<BCLIBC_BaseTrajDataHandlerInterface *> handlers_;

    public:
        /**
         * @brief Constructs compositor with variadic list of handlers.
         * @param args Pointers to handler objects (not owned by compositor).
         */
        template <typename... Handlers>
        BCLIBC_BaseTrajDataHandlerCompositor(Handlers *...args)
            : handlers_{args...} {}

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
                handlers_.push_back(handler);
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
        ~BCLIBC_BaseTrajSeq();

        /**
         * @brief Handler interface implementation - appends data to sequence.
         * @param data Trajectory data to append.
         */
        void handle(const BCLIBC_BaseTrajData &data) override;

        /**
         * @brief Appends trajectory point to sequence.
         *
         * Uses std::vector::push_back with automatic geometric growth.
         *
         * @param data Trajectory data to append (copied).
         */
        void append(const BCLIBC_BaseTrajData &data);

        /**
         * @brief Returns number of trajectory points in sequence.
         * @return Number of elements (>= 0).
         */
        ssize_t get_length() const;

        /**
         * @brief Returns allocated capacity of internal buffer.
         * @return Capacity (number of elements before reallocation needed).
         */
        ssize_t get_capacity() const;

        /**
         * @brief Retrieves trajectory element at index (supports negative indexing).
         *
         * Python-style indexing: -1 returns last element, -2 second-to-last, etc.
         *
         * @param idx Index (-1 for last, etc.).
         * @return Const reference to trajectory data.
         * @throws std::out_of_range if index out of bounds.
         */
        const BCLIBC_BaseTrajData &get_item(ssize_t idx) const;

        /**
         * @brief Retrieves/interpolates trajectory at specified key value.
         *
         * ALGORITHM:
         * 1. Optional time-based filtering (if start_from_time > 0)
         * 2. Binary search for exact match (epsilon = 1e-9)
         * 3. If no exact match: 3-point PCHIP interpolation
         *
         * @param key_kind Type of key to search by.
         * @param key_value Target key value.
         * @param start_from_time Optional time threshold (0.0 to disable).
         * @param out Output trajectory data.
         * @throws std::domain_error if fewer than 3 points.
         */
        void get_at(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            double start_from_time,
            BCLIBC_BaseTrajData &out) const;

        /**
         * @brief Interpolates trajectory at specified slant height.
         *
         * Slant height = py*cos(angle) - px*sin(angle)
         *
         * @param look_angle_rad Look angle in radians.
         * @param value Target slant height.
         * @param out Output trajectory data.
         * @throws std::domain_error if insufficient data or degenerate.
         */
        void get_at_slant_height(
            double look_angle_rad,
            double value,
            BCLIBC_BaseTrajData &out) const;

        /**
         * @brief Performs 3-point PCHIP interpolation at specified index.
         *
         * Uses points [idx-1, idx, idx+1] as interpolation bracket.
         *
         * @param idx Center index (must be in [1, n-2]).
         * @param key_kind Independent variable for interpolation.
         * @param key_value Target value.
         * @param out Output trajectory data.
         * @throws std::out_of_range if idx outside valid range.
         */
        void interpolate_at(
            ssize_t idx,
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData &out) const;

    private:
        /**
         * @brief Attempts exact match at index (throws if not exact).
         *
         * Used internally by get_at() to optimize exact lookups.
         *
         * @param idx Index to check.
         * @param key_kind Type of key.
         * @param key_value Target value.
         * @param out Output (populated only if exact match).
         * @throws std::out_of_range if idx invalid.
         * @throws std::runtime_error if not exact match.
         */
        void try_get_exact(
            ssize_t idx,
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData &out) const;

        /**
         * @brief Binary search for 3-point interpolation bracket.
         *
         * Returns center index in [1, n-2] suitable for 3-point interpolation.
         *
         * @param key_kind Key to search by.
         * @param key_value Target value.
         * @return Center index, or -1 if n < 3.
         */
        ssize_t bisect_center_idx_buf(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value) const;

        /**
         * @brief Binary search for slant height interpolation bracket.
         *
         * @param ca Cosine of look angle.
         * @param sa Sine of look angle.
         * @param value Target slant value.
         * @return Center index [1, n-2], or -1 if n < 3.
         */
        ssize_t bisect_center_idx_slant_buf(
            double ca,
            double sa,
            double value) const;

        /**
         * @brief Finds first index with time >= start_time.
         *
         * Uses binary search for large arrays, linear for small.
         *
         * @param start_time Time threshold.
         * @return Index of first point with time >= start_time.
         */
        ssize_t find_start_index(double start_time) const;

        /**
         * @brief Finds target index for interpolation (with extrapolation handling).
         *
         * @param key_kind Type of key.
         * @param key_value Target value.
         * @param start_idx Starting search index (currently unused).
         * @return Target index [1, n-2], or -1 if n < 3.
         */
        ssize_t find_target_index(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            ssize_t start_idx) const;

        /**
         * @brief Checks if two doubles are approximately equal.
         *
         * Uses absolute difference: |a - b| < epsilon
         *
         * @param a First value.
         * @param b Second value.
         * @param epsilon Tolerance.
         * @return 1 if close, 0 otherwise.
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
         * @brief Constructs from ballistic state and shot properties.
         *
         * Computes all derived fields (angles, energy, drag, etc.).
         *
         * @param props Shot properties (atmosphere, Coriolis, drag model).
         * @param time Flight time.
         * @param range_vector Position vector.
         * @param velocity_vector Velocity vector.
         * @param mach Mach number (or 0.0 to compute from altitude).
         * @param flag Classification flag.
         */
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            double time,
            const BCLIBC_V3dT &range_vector,
            const BCLIBC_V3dT &velocity_vector,
            double mach,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        /**
         * @brief Constructs from base trajectory data and shot properties.
         */
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_BaseTrajData &data,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        /**
         * @brief Constructs from flagged data.
         */
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_FlaggedData &data);

        /**
         * @brief Interpolates full trajectory data using 3-point method.
         *
         * All 15 trajectory fields are interpolated independently.
         * Supports both PCHIP (cubic) and LINEAR interpolation methods.
         *
         * @param key Independent variable.
         * @param value Target value.
         * @param t0 First trajectory point.
         * @param t1 Second trajectory point.
         * @param t2 Third trajectory point.
         * @param flag Output flag.
         * @param method Interpolation method (PCHIP or LINEAR).
         * @return Interpolated trajectory data.
         * @throws std::logic_error if key invalid.
         * @throws std::domain_error if linear interpolation fails.
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
         * @param key Field identifier.
         * @return Field value, or 0.0 if invalid key.
         */
        double get_key_val(BCLIBC_TrajectoryData_InterpKey key) const;

        /**
         * @brief Sets field value by key.
         * @param key Field identifier.
         * @param value New value.
         */
        void set_key_val(BCLIBC_TrajectoryData_InterpKey key, double value);
    };

};

#endif // BCLIBC_BASE_TRAJ_SEQ_HPP
