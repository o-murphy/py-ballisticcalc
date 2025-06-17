#include <stdio.h>
#include "drag.h"

MachListT tableToMach(DragTableT *table)
{
    MachListT machList;
    machList.values = NULL;
    machList.length = 0;

    if (table == NULL || table->table == NULL || table->length == 0)
    {
        fprintf(stderr, "Warning: tableToMach received a NULL, empty, or invalid DragTableT.\n");
        // Return an empty MachListT
        return machList;
    }

    // Each point in DragTableT consists of 2 doubles (Mach, CD).
    // So, the 'values' array in MachListT needs to be twice the length of DragTableT.
    size_t num_doubles = table->length * 2;

    // Allocate memory for the interleaved Mach and CD values
    machList.values = (double *)malloc(num_doubles * sizeof(double));
    if (machList.values == NULL)
    {
        fprintf(stderr, "Error: Failed to allocate memory for MachListT.values.\n");
        return machList; // Return empty on allocation failure
    }

    machList.length = num_doubles; // Set the length to the total number of doubles

    // Copy data from DragTableT to MachListT in an interleaved manner
    for (size_t i = 0; i < table->length; ++i)
    {
        // Mach value at even index
        machList.values[2 * i] = table->table[i].Mach;
        // CD value at odd index
        machList.values[2 * i + 1] = table->table[i].CD;
    }

    return machList;
}

// Helper function to free a MachListT
// This function frees the single 'values' array.
void freeMachList(MachListT *machList)
{
    if (machList == NULL)
    {
        return;
    }
    if (machList->values != NULL)
    {
        free(machList->values);
        machList->values = NULL;
    }
    machList->length = 0;
}

// Implementation for freeDragTable
void freeDragTable(DragTableT *table)
{
    if (table != NULL)
    {
        // Assuming 'table->table' is a dynamically allocated array of DragPointT
        // that needs to be freed. If DragTableT has other dynamically allocated
        // members, they should also be freed here.
        if (table->table != NULL)
        {
            free(table->table);
            table->table = NULL; // Good practice to set to NULL after freeing
        }
        // If DragTableT itself was dynamically allocated, you might free 'table' here.
        // However, based on typical usage, it's often passed as a pointer
        // and its memory might be managed by the caller, so we only free its internal
        // dynamically allocated members.
    }
}

// Implementation for freeCurve
void freeCurve(CurveT *curve)
{
    if (curve != NULL)
    {
        // Assuming 'curve->points' is a dynamically allocated array of V3dT points
        // that needs to be freed. If CurveT has other dynamically allocated
        // members, they should also be freed here.
        if (curve->points != NULL)
        {
            free(curve->points);
            curve->points = NULL; // Good practice to set to NULL after freeing
        }
        // Similar to freeDragTable, if CurveT itself was dynamically allocated,
        // you might free 'curve' here.
    }
}

CurveT calculateCurve(DragTableT *table)
{
    CurveT curve;
    curve.points = NULL; // Initialize to NULL
    curve.length = 0;    // Initialize to 0

    // Input validation
    if (table == NULL || table->table == NULL || table->length == 0)
    {
        fprintf(stderr, "Error: calculateCurve received a NULL, empty, or invalid DragTableT.\n");
        return curve; // Return an empty/invalid curve
    }

    size_t len_data_points = table->length;
    size_t len_data_range = len_data_points - 1;

    // Allocate memory for the curve_points array
    curve.points = (CurvePointT *)malloc(len_data_points * sizeof(CurvePointT));
    if (curve.points == NULL)
    {
        fprintf(stderr, "Error: Unable to allocate memory for curve points in calculateCurve.\n");
        // MemoryError handling as in Cython
        return curve; // Return an empty/invalid curve
    }

    // Assign the length of the curve
    curve.length = len_data_points;

    double rate, x1, x2, x3, y1, y2, y3, a, b, c;

    // First point: Calculate rate and initialize the first curve point
    // Ensure there are at least two points to calculate a rate for the first segment.
    if (len_data_points >= 2)
    {
        // Prevent division by zero if Mach values are the same
        if (table->table[1].Mach - table->table[0].Mach == 0.0)
        {
            fprintf(stderr, "Warning: Duplicate Mach values for first two points in DragTable. Rate calculation problematic.\n");
            rate = 0.0; // Or handle as an error, depending on desired behavior
        }
        else
        {
            rate = (table->table[1].CD - table->table[0].CD) / (table->table[1].Mach - table->table[0].Mach);
        }
        curve.points[0].a = 0.0; // Linear interpolation
        curve.points[0].b = rate;
        curve.points[0].c = table->table[0].CD - table->table[0].Mach * rate;
    }
    else
    {
        // If only one data point, it's a constant. Treat as linear with 0 slope.
        curve.points[0].a = 0.0;
        curve.points[0].b = 0.0;
        curve.points[0].c = table->table[0].CD;
    }

    // Loop through the data points and calculate the curve points
    // This loop runs from the second point up to the second-to-last point.
    for (size_t i = 1; i < len_data_range; ++i)
    { // Cython uses range(1, len_data_range), which is exclusive of end.
        x1 = table->table[i - 1].Mach;
        x2 = table->table[i].Mach;
        x3 = table->table[i + 1].Mach;
        y1 = table->table[i - 1].CD;
        y2 = table->table[i].CD;
        y3 = table->table[i + 1].CD;

        // Denominators for 'a' and 'b' calculations
        double denom_a = (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1);
        double denom_b = (x2 - x1);

        // Check for division by zero before calculation
        if (denom_a == 0.0 || denom_b == 0.0)
        {
            fprintf(stderr, "Warning: Division by zero in curve calculation for point %zu. Using linear approximation.\n", i);
            // Fallback to linear interpolation if parabolic calculation is problematic
            if (table->table[i].Mach - table->table[i - 1].Mach == 0.0)
            {
                rate = 0.0; // Avoid division by zero
            }
            else
            {
                rate = (table->table[i].CD - table->table[i - 1].CD) / (table->table[i].Mach - table->table[i - 1].Mach);
            }
            curve.points[i].a = 0.0;
            curve.points[i].b = rate;
            curve.points[i].c = table->table[i - 1].CD - table->table[i - 1].Mach * rate;
        }
        else
        {
            a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / denom_a;
            b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / denom_b;
            c = y1 - (a * x1 * x1 + b * x1);
            curve.points[i].a = a;
            curve.points[i].b = b;
            curve.points[i].c = c;
        }
    }

    // Last point: Calculate rate for the final point and set the last curve point
    // Ensure there are at least two points to calculate a rate for the last segment.
    if (len_data_points >= 2)
    {
        // Prevent division by zero if Mach values are the same
        if (table->table[len_data_points - 1].Mach - table->table[len_data_points - 2].Mach == 0.0)
        {
            fprintf(stderr, "Warning: Duplicate Mach values for last two points in DragTable. Rate calculation problematic.\n");
            rate = 0.0; // Or handle as an error
        }
        else
        {
            rate = (table->table[len_data_points - 1].CD - table->table[len_data_points - 2].CD) /
                   (table->table[len_data_points - 1].Mach - table->table[len_data_points - 2].Mach);
        }
        curve.points[len_data_points - 1].a = 0.0; // Linear interpolation
        curve.points[len_data_points - 1].b = rate;
        curve.points[len_data_points - 1].c = table->table[len_data_points - 1].CD - table->table[len_data_points - 1].Mach * rate;
    }
    else if (len_data_points == 1)
    {
        // If only one point, it's already handled in the 'first point' logic by the 'else' branch there.
        // This 'else if' should ideally not be reached if len_data_points >= 2 for the first point check.
        // It's a redundant check here but ensures safety if previous logic changes.
        // For a single point, the last point IS the first point.
    }

    return curve;
}

double calculateByCurveAndMachList(MachListT *mach_list, CurveT *curve, double mach)
{
    // Input validation
    if (mach_list == NULL || mach_list->values == NULL || mach_list->length == 0)
    {
        fprintf(stderr, "Error: calculateByCurveAndMachList received a NULL, empty, or invalid MachListT.\n");
        return 0.0; // Or a specific error value
    }
    if (curve == NULL || curve->points == NULL || curve->length == 0)
    {
        fprintf(stderr, "Error: calculateByCurveAndMachList received a NULL, empty, or invalid CurveT.\n");
        return 0.0; // Or a specific error value
    }

    size_t num_points = curve->length; // Number of original data points, also number of curve points.

    // Handle single point case
    if (num_points == 1)
    {
        return curve->points[0].c + mach * (curve->points[0].b + curve->points[0].a * mach);
    }

    // Handle mach values outside the range of the MachList
    // Mach values are stored at even indices: mach_list->values[0], mach_list->values[2*1], ..., mach_list->values[2*(num_points-1)]
    if (mach <= mach_list->values[0])
    {
        return curve->points[0].c + mach * (curve->points[0].b + curve->points[0].a * mach);
    }
    if (mach >= mach_list->values[2 * (num_points - 1)])
    {
        return curve->points[num_points - 1].c + mach * (curve->points[num_points - 1].b + curve->points[num_points - 1].a * mach);
    }

    // Binary search to find the correct segment
    int mlo = 0;
    int mhi = num_points - 1; // Search range for indices into the original data points

    int m; // Resulting index for curve->points

    // The loop runs until mlo and mhi are adjacent (mhi = mlo + 1)
    while (mhi - mlo > 1)
    {
        int mid = mlo + (mhi - mlo) / 2; // Safer mid calculation
        // Compare with the Mach value at the mid index (remembering interleaved format)
        if (mach_list->values[2 * mid] < mach)
        {
            mlo = mid;
        }
        else
        {
            mhi = mid;
        }
    }

    // After the loop, mach is between mach_list->values[2 * mlo] and mach_list->values[2 * mhi]
    // Pick the closer of the two points (mlo or mhi) as done in Cython
    if (mach_list->values[2 * mhi] - mach > mach - mach_list->values[2 * mlo])
    {
        m = mlo;
    }
    else
    {
        m = mhi;
    }

    // Retrieve the corresponding CurvePointT
    CurvePointT curve_m = curve->points[m];

    // Return the calculated value using the curve coefficients
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach);
}