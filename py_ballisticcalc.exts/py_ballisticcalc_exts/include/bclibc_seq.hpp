#ifndef BCLIBC_BASE_TRAJ_SEQ_HPP
#define BCLIBC_BASE_TRAJ_SEQ_HPP

#include <stddef.h>    // Required for size_t
#include <sys/types.h> // Required for ssize_t

#include "bclibc_bclib.hpp"
#include "bclibc_interp.hpp"

// --- START CROSS-PLATFORM FIX ---
// The manylinux build environment failed due to redefinition.
// We only need to manually define ssize_t for MSVC (Windows).
// For other platforms, we rely on the standard headers above.
#if defined(_MSC_VER)
// Robust definition for MSVC based on architecture
#if defined(_WIN64)
typedef __int64 ssize_t;
#else
typedef long ssize_t;
#endif
#endif
// --- END CROSS-PLATFORM FIX ---

// Min capacity starts from 64
// maybe beter to use at least 192 byte min capacity as a 3-point buffer required for interpolation
#define BCLIBC_BASE_TRAJ_SEQ_MIN_CAPACITY 256 // 64
#define BCLIBC_BASE_TRAJ_SEQ_INTERP_KEY_ACTIVE_COUNT 8

namespace bclibc
{
    /**
     * Simple C struct for trajectory data points used in the contiguous buffer.
     */
    struct BCLIBC_BaseTraj
    {
    public:
        double time; /* Time of the data point */
        double px;   /* Position x-coordinate */
        double py;   /* Position y-coordinate */
        double pz;   /* Position z-coordinate */
        double vx;   /* Velocity x-component */
        double vy;   /* Velocity y-component */
        double vz;   /* Velocity z-component */
        double mach; /* Mach number */

        double key_val(BCLIBC_BaseTrajSeq_InterpKey key_kind) const;
        double slant_val_buf(double ca, double sa) const;

        static void interpolate3pt_vectorized(
            double x, double ox0, double ox1, double ox2,
            const BCLIBC_BaseTraj *p0, const BCLIBC_BaseTraj *p1, const BCLIBC_BaseTraj *p2,
            BCLIBC_BaseTraj *out, BCLIBC_BaseTrajSeq_InterpKey skip_key);
    };

    /**
     * Internal view structure for a sequence (buffer) of BCLIBC_BaseTraj points.
     */
    class BCLIBC_BaseTrajSeq
    {
    private:
        BCLIBC_BaseTraj *buffer;
        size_t length;
        size_t capacity;

    public:
        BCLIBC_BaseTrajSeq();

        ~BCLIBC_BaseTrajSeq();

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
        BCLIBC_ErrorType append(double time, double px, double py, double pz, double vx, double vy, double vz, double mach);

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
        BCLIBC_ErrorType ensure_capacity(size_t min_capacity);

        /**
         * Returns the length of the trajectory sequence.
         *
         * @return The number of elements in the sequence, or -1 if seq is NULL.
         */
        ssize_t get_length() const;

        /**
         * Returns the capacity of the trajectory sequence.
         *
         * @return capacity of the trajectory sequence, or -1 if seq is NULL.
         */
        ssize_t get_capacity() const;

        /**
         * Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.
         *
         * Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
         * @return 1 on success, 0 on failure.
         */
        BCLIBC_ErrorType interpolate_at(
            ssize_t idx,
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData *out) const;

        /**
         * Retrieve a pointer to a trajectory element at the given index.
         * Supports negative indices: -1 = last element, -2 = second-to-last, etc.
         *
         * @param idx Index of the element to retrieve. Can be negative.
         * @return Pointer to the BCLIBC_BaseTraj element, or NULL if index is out of bounds.
         */
        BCLIBC_BaseTraj *get_raw_item(ssize_t idx) const;

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
        BCLIBC_ErrorType get_item(
            ssize_t idx,
            BCLIBC_BaseTrajData *out) const;

        /**
         * @brief Get trajectory data at a given key value, with optional start time.
         *
         * @param key_kind Kind of key to search/interpolate.
         * @param key_value Key value to get.
         * @param start_from_time Optional start time (use -1 if not used).
         * @param out Output trajectory data.
         * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
         */
        BCLIBC_ErrorType get_at(
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            double start_from_time,
            BCLIBC_BaseTrajData *out) const;

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
        BCLIBC_ErrorType get_at_slant_height(
            double look_angle_rad,
            double value,
            BCLIBC_BaseTrajData *out) const;

    private:
        /**
         * @brief Interpolate at center index with logging.
         *
         * @param idx Center index for interpolation.
         * @param key_kind Kind of interpolation key.
         * @param key_value Key value to interpolate at.
         * @param out Output trajectory data.
         * @return BCLIBC_ErrorType BCLIBC_E_NO_ERROR if successful, otherwise error code.
         */
        BCLIBC_ErrorType interpolate_at_center(
            ssize_t idx,
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData *out) const;

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
        BCLIBC_ErrorType interpolate_raw(
            ssize_t idx,
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTraj *out) const;

        /**
         * @brief Try to get exact value at index, return BCLIBC_E_NO_ERROR if successful.
         *
         * @param idx Index to check.
         * @param key_kind Kind of key.
         * @param key_value Key value to match.
         * @param out Output trajectory data.
         * @return BCLIBC_E_NO_ERROR if exact match found, otherwise BCLIBC_E_VALUE_ERROR.
         */
        BCLIBC_ErrorType try_get_exact(
            ssize_t idx,
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData *out) const;

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
        ssize_t bisect_center_idx_buf(
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value) const;

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
        ssize_t bisect_center_idx_slant_buf(
            double ca,
            double sa,
            double value) const;

        /**
         * @brief Find the starting index for a given start time.
         *
         * @param buf Buffer of trajectory points.
         * @param n Length of buffer.
         * @param start_time Start time to search from.
         * @return Index of the first element with time >= start_time.
         */
        static ssize_t find_start_index(const BCLIBC_BaseTraj *buf, ssize_t n, double start_time);

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
        static ssize_t find_target_index(
            const BCLIBC_BaseTraj *buf,
            ssize_t n,
            BCLIBC_BaseTrajSeq_InterpKey key_kind,
            double key_value,
            ssize_t start_idx);

        /**
         * @brief Check if two double values are approximately equal.
         *
         * @param a First value.
         * @param b Second value.
         * @param epsilon Tolerance.
         * @return 1 if close, 0 otherwise.
         */
        static int is_close(double a, double b, double epsilon);
    };
};

#endif // BCLIBC_BASE_TRAJ_SEQ_HPP
