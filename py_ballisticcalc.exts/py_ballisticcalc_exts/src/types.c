#include "types.h"
#include <stddef.h>
#include <stddef.h>



/**
 * @brief Calculates a component of the drag equation for a given Mach number.
 *
 * This function computes: Cd * (StandardDensity * PI / (4 * 2 * 144)) / BC
 * where the constant (StandardDensity * PI / (4 * 2 * 144)) is 2.08551e-04.
 *
 * @param shot_data_ptr A pointer to a ShotData_t structure containing ballistic data.
 * @param mach The current Mach number.
 * @return The calculated drag component (dimensionless or with specific units
 * depending on the full drag equation usage, but effectively Cd * K / BC).
 */
double drag_by_mach(const ShotData_t *shot_data_ptr, double mach) {
    // Call the C function to get the coefficient of drag (Cd)
    double cd = calculate_by_curve_and_mach_list(&shot_data_ptr->mach_list, &shot_data_ptr->curve, mach);

    // The magic constant derived from: StandardDensity * pi / (4 * 2 * 144)
    // StandardDensity = 0.076474 lb/ft^3
    // pi / (4 * 2 * 144) = pi / 1152
    // 0.076474 * 3.1415926535 / 1152 = 0.0002085518...
    const double MAGIC_DRAG_CONSTANT = 2.08551e-04;

    // Calculate and return the drag component
    // Check for division by zero if bc can potentially be zero,
    // though for physical ballistic coefficients, this shouldn't be an issue.
    if (shot_data_ptr->bc == 0.0) {
        // Handle error: ballistic coefficient cannot be zero
        // You might return an error code, NaN, or a very large number,
        // depending on how you want to handle this edge case.
        // For now, return 0.0 which might indicate an issue.
        return 0.0; // Or INFINITY, or raise an error, depending on context
    }

    return cd * MAGIC_DRAG_CONSTANT / shot_data_ptr->bc;
}


/**
 * @brief Calculates a value based on a Mach list and a curve using interpolation.
 *
 * This function performs a binary search on the `mach_list_ptr` to find the
 * closest Mach values to the input `mach`. It then uses the corresponding
 * coefficients from `curve_ptr` to calculate a value.
 *
 * @param mach_list_ptr A pointer to a MachList_t structure containing Mach values.
 * @param curve_ptr A pointer to a Curve_t structure containing curve points (coefficients).
 * @param mach The input Mach value for which to calculate the result.
 * @return The calculated double value.
 */
double calculate_by_curve_and_mach_list(const MachList_t *mach_list_ptr, const Curve_t *curve_ptr, double mach) {
    int num_points;
    int mlo, mhi, mid, m;
    CurvePoint_t curve_m;

    // Get the number of points in the curve (and implicitly in the mach_list for lookup)
    // We assume curve_ptr->length and mach_list_ptr->length are consistent for valid operation.
    num_points = (int)curve_ptr->length;

    //    // Handle edge case: if there are fewer than 2 points, we can't perform binary search
    //    // or the intended interpolation. This implementation assumes at least 2 points
    //    // as per the original Python comment "Assuming we have at least 2 points".
    //    if (num_points < 2) {
    //        // Depending on requirements, you might want to:
    //        // 1. Return an error code.
    //        // 2. Return a specific default value (e.g., 0.0, NaN).
    //        // 3. Print an error and exit.
    //        // For now, we'll return 0.0, but this should be handled carefully in a real application.
    //        fprintf(stderr, "Error: Curve must have at least 2 points for calculation.\n");
    //        return 0.0;
    //    }

    // Set the initial range for binary search
    mlo = 0;
    mhi = num_points - 2; // Adjusted for 0-based indexing and finding an interval

    // Perform binary search to find the closest Mach values
    while (mhi - mlo > 1) {
        mid = (mhi + mlo) / 2; // Integer division is correct here
        if (mach_list_ptr->array[mid] < mach) {
            mlo = mid;
        } else {
            mhi = mid;
        }
    }

    // Determine the closest point to `mach`
    // If the difference between mhi's Mach and input Mach is greater than
    // the difference between input Mach and mlo's Mach, then mlo is closer.
    if (mach_list_ptr->array[mhi] - mach > mach - mach_list_ptr->array[mlo]) {
        m = mlo;
    } else {
        m = mhi;
    }

    // Retrieve the corresponding CurvePoint_t from the curve
    curve_m = curve_ptr->points[m];

    // Return the calculated value using the curve coefficients
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach);
}