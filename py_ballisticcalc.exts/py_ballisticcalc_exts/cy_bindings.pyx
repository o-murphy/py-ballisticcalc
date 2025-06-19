# Total Score: 158, Possible Score: 21000
# Total Non-Empty Lines: 210
# Python Overhead Lines: 19
# Cythonization Percentage: 99.25%
# Python Overhead Lines Percentage: 9.05%

# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, pow, atan2, exp, sqrt, sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)

import warnings

@final
cdef Config_t config_bind(object config):
    return Config_t(
        config.cMaxCalcStepSizeFeet,
        config.cZeroFindingAccuracy,
        config.cMinimumVelocity,
        config.cMaximumDrop,
        config.cMaxIterations,
        config.cGravityConstant,
        config.cMinimumAltitude,
    )

cdef double cy_get_calc_step(Config_t * config, double step = 0):
    cdef double preferred_step = config.cMaxCalcStepSizeFeet
    if step == 0:
        return preferred_step / 2.0
    return fmin(step, preferred_step) / 2.0

cdef MachList_t cy_table_to_mach(list[object] data):
    cdef int data_len = len(data)
    cdef double * result = <double *> malloc(data_len * sizeof(double))
    if result is NULL:
        raise MemoryError("Unable to allocate memory for result array")

    cdef int i
    cdef object dp  # Assuming dp is an object with a Mach attribute

    # Populate the C array
    for i in range(data_len):
        dp = data[i]
        result[i] = dp.Mach  # Access the Mach attribute and store it in the C array

    return MachList_t(
        array=result,
        length=data_len
    )

cdef Curve_t cy_calculate_curve(list[object] data_points):
    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef Curve_t curve
    cdef CurvePoint_t * curve_points
    cdef int i, num_points, len_data_points, len_data_range

    len_data_points = len(data_points)
    len_data_range = len_data_points - 1

    # Allocate memory for the curve_points array
    curve_points = <CurvePoint_t *> malloc(len_data_points * sizeof(CurvePoint_t))
    if curve_points is NULL:
        raise MemoryError("Unable to allocate memory for curve points")

    # First point: Calculate rate and initialize the first curve point
    rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
    curve_points[0] = CurvePoint_t(0, rate, data_points[0].CD - data_points[0].Mach * rate)

    # Loop through the data points and calculate the curve points
    for i in range(1, len_data_range):
        x1 = data_points[i - 1].Mach
        x2 = data_points[i].Mach
        x3 = data_points[i + 1].Mach
        y1 = data_points[i - 1].CD
        y2 = data_points[i].CD
        y3 = data_points[i + 1].CD
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_points[i] = CurvePoint_t(a, b, c)

    # Last point: Calculate rate for the final point and set the last curve point
    num_points = len_data_points
    rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
           (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
    curve_points[num_points - 1] = CurvePoint_t(0, rate, data_points[num_points - 1].CD - data_points[
        num_points - 2].Mach * rate)

    # Set the length of the curve
    curve.length = <size_t>len_data_points
    curve.points = curve_points

    return curve

# TODO: try malloc there
# # curve_calculations.pyx (or your Cython file name)
#
# # Import necessary C standard library functions
# # We need malloc for dynamic memory allocation
# cdef extern from "stdlib.h":
#     void *malloc(size_t size)
#     void free(void *ptr) # It's good practice to have free available for later use
#
# # Define the CurvePoint_t struct
# # Assuming data_points have 'Mach' and 'CD' attributes.
# # The CurvePoint_t struct should define 'a', 'b', and 'c' for the quadratic/linear segments.
# cdef struct CurvePoint_t:
#     double a
#     double b
#     double c
#
# # Define the Curve_t struct
# # This struct holds a pointer to an array of CurvePoint_t and its length.
# cdef struct Curve_t:
#     CurvePoint_t * points
#     size_t length
#
# # This is an example of what your data_points object might look like.
# # In a real scenario, this would likely be a Python class or a Cython cdef class
# # that 'data_points' are instances of.
# # For demonstration purposes, we'll assume data_points elements have .Mach and .CD attributes.
# # You would define your actual data point structure or class separately.
# # For example, if it's a Python class:
# # class DataPoint:
# #     def __init__(self, mach, cd):
# #         self.Mach = mach
# #         self.CD = cd
#
#
# cdef Curve_t cy_calculate_curve(list[object] data_points):
#     cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
#     cdef Curve_t curve
#     cdef CurvePoint_t * curve_points
#     # Declare variables for lengths and loop counter as size_t where appropriate
#     cdef size_t i, num_points, len_data_points, len_data_range
#
#     # Get the length of the input data_points list and cast to size_t
#     len_data_points = <size_t>len(data_points)
#     # len_data_range is used for the loop upper bound, so it should also be size_t
#     len_data_range = len_data_points - 1
#
#     # Basic validation: ensure we have enough points to form a curve
#     if len_data_points < 2:
#         # A single point doesn't form a segment, and at least 2 are needed for the first rate calc.
#         # If you need quadratic segments, you'll need at least 3 points for the middle section.
#         # Adjust this check based on your curve fitting logic.
#         raise ValueError("Not enough data points to calculate a curve. At least 2 are required.")
#
#     # Allocate memory for the curve_points array
#     # The size of allocation should be based on len_data_points (the total number of points)
#     curve_points = <CurvePoint_t *> malloc(len_data_points * sizeof(CurvePoint_t))
#     if curve_points is NULL:
#         raise MemoryError("Unable to allocate memory for curve points")
#
#     # --- First Point Calculation (Linear Segment) ---
#     # This assumes data_points[0] and data_points[1] exist.
#     # The first curve point is based on a linear interpolation between the first two data points.
#     rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
#     curve_points[0] = CurvePoint_t(0, rate, data_points[0].CD - data_points[0].Mach * rate)
#
#     # --- Middle Points Calculation (Quadratic Segments) ---
#     # This loop calculates quadratic segments for points where you have a preceding and succeeding point.
#     # It iterates from the second point (index 1) up to the second-to-last point (index len_data_points - 2).
#     # This ensures data_points[i-1], data_points[i], and data_points[i+1] are always valid.
#     for i in range(<size_t>1, len_data_range): # Iterate with size_t, casting range arguments
#         x1 = data_points[i - 1].Mach
#         x2 = data_points[i].Mach
#         x3 = data_points[i + 1].Mach
#         y1 = data_points[i - 1].CD
#         y2 = data_points[i].CD
#         y3 = data_points[i + 1].CD
#
#         # Denominator check to prevent division by zero for identical Mach values
#         denominator = ((x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
#         if denominator == 0:
#             # Handle cases where points are collinear or identical in Mach values
#             # This is a simplified error handling; you might want more sophisticated methods
#             # like falling back to linear interpolation or raising a more specific error.
#             # For now, let's raise an error.
#             raise ValueError(f"Degenerate Mach points around index {i} preventing quadratic fit.")
#
#         a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / denominator
#         b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
#         c = y1 - (a * x1 * x1 + b * x1)
#         curve_points[i] = CurvePoint_t(a, b, c)
#
#     # --- Last Point Calculation (Linear Segment) ---
#     # This handles the very last point in the curve, again using a linear segment.
#     # It assumes data_points[num_points - 1] and data_points[num_points - 2] exist.
#     num_points = len_data_points # num_points is already size_t from declaration
#     if num_points > 1: # Only calculate if there are at least two points
#         rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
#                (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
#         curve_points[num_points - 1] = CurvePoint_t(0, rate, data_points[num_points - 1].CD - \
#             data_points[num_points - 2].Mach * rate)
#     else:
#         # Handle the case of only one point (if allowed by initial validation)
#         # In this specific implementation, it means len_data_points was 1,
#         # and the above 'if len_data_points < 2' would have caught it.
#         # But if that check were looser, you'd need a fallback for curve_points[0].
#         # For a single point, 'a' and 'b' would typically be 0, and 'c' would be the CD value.
#         pass # The initial check handles this scenario.
#
#
#     # Set the length of the curve and assign the allocated points
#     curve.length = len_data_points
#     curve.points = curve_points
#
#     return curve

cdef double cy_calculate_by_curve_and_mach_list(MachList_t *mach_list, Curve_t *curve, double mach):
    cdef int num_points, mlo, mhi, mid, m
    cdef CurvePoint_t curve_m

    # Get the number of points in the curve
    num_points = <int>curve.length

    # Set the initial range for binary search
    mlo = 0
    mhi = num_points - 2  # Assuming we have at least 2 points

    # Perform binary search to find the closest Mach values
    while mhi - mlo > 1:
        mid = (mhi + mlo) // 2
        if mach_list.array[mid] < mach:
            mlo = mid
        else:
            mhi = mid

    # Determine the closest point to `mach`
    if mach_list.array[mhi] - mach > mach - mach_list.array[mlo]:
        m = mlo
    else:
        m = mhi

    # Retrieve the corresponding CurvePoint_t from the curve
    curve_m = curve.points[m]

    # Return the calculated value using the curve coefficients
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)

cdef double cy_drag_by_mach(ShotData_t * t, double mach):
    """ Drag force = V^2 * Cd * AirDensity * S / 2m where:
        cStandardDensity of Air = 0.076474 lb/ft^3
        S is cross-section = d^2 pi/4, where d is bullet diameter in inches
        m is bullet mass in pounds
    bc contains m/d^2 in units lb/in^2, which we multiply by 144 to convert to lb/ft^2
    Thus: The magic constant found here = StandardDensity * pi / (4 * 2 * 144)
    """
    cdef double cd = cy_calculate_by_curve_and_mach_list(&t.mach_list, &t.curve, mach)
    return cd * 2.08551e-04 / t.bc

cdef double cy_spin_drift(ShotData_t * t, double time):
    """Litz spin-drift approximation
    :param time: Time of flight
    :return: windage due to spin drift, in feet
    """
    cdef double sign
    if (t.twist != 0) and (t.stability_coefficient != 0):
        sign = 1 if t.twist > 0 else -1
        return sign * (1.25 * (t.stability_coefficient + 1.2) * pow(time, 1.83)) / 12
    return 0

cdef void cy_update_stability_coefficient(ShotData_t * t):
    """Miller stability coefficient"""
    cdef:
        double twist_rate, length, sd, fv, ft, pt, ftp
    if t.twist and t.length and t.diameter and t.atmo._p0:
        twist_rate = fabs(t.twist) / t.diameter
        length = t.length / t.diameter
        sd = 30.0 * t.weight / (pow(twist_rate, 2) * pow(t.diameter, 3) * length * (1 + pow(length, 2)))
        fv = pow(t.muzzle_velocity / 2800, 1.0 / 3.0)
        ft = (t.atmo._t0 * 9.0 / 5.0) + 32.0  # Convert from Celsius to Fahrenheit
        pt = t.atmo._p0 / 33.8639  # Convert hPa to inHg
        ftp = ((ft + 460.0) / (59.0 + 460.0)) * (29.92 / pt)
        t.stability_coefficient = sd * fv * ftp
    else:
        t.stability_coefficient = 0.0

# Function to free memory for Curve_t
cdef void free_curve(Curve_t *curve):
    if curve.points is not NULL:
        free(curve.points)

# Function to free memory for MachList_t
cdef void free_mach_list(MachList_t *mach_list):
    if mach_list.array is not NULL:
        free(<void *> mach_list.array)

# Function to free memory for ShotData_t
cdef void free_trajectory(ShotData_t *t):
    # Free memory for curve and mach_list
    free_curve(&t.curve)
    free_mach_list(&t.mach_list)

cdef double cDegreesFtoR = 459.67
cdef double cDegreesCtoK = 273.15
cdef double cSpeedOfSoundImperial = 49.0223
cdef double cSpeedOfSoundMetric = 20.0467
cdef double cLapseRateKperFoot = -0.0019812
cdef double cLapseRateImperial = -3.56616e-03
cdef double cPressureExponent = 5.2559
cdef double cLowestTempF = -130
cdef double mToFeet = 3.28084

# Function to calculate density ratio and Mach speed at altitude
cdef void update_density_factor_and_mach_for_altitude(
        Atmosphere_t * atmo, double altitude, double * density_ratio, double * mach
):
    """
    :param altitude: ASL in units of feet
    :return: density ratio and Mach 1 (fps) for the specified altitude
    """
    cdef double celsius, kelvin, pressure, density_delta
    if fabs(atmo._a0 - altitude) < 30:
        density_ratio[0] = atmo.density_ratio
        mach[0] = atmo._mach
    else:
        celsius = (altitude - atmo._a0) * cLapseRateKperFoot + atmo._t0

        if altitude > 36089:
            warnings.warn("Density request for altitude above troposphere."
                            " Atmospheric model not valid here.", RuntimeWarning)
        if celsius < -cDegreesCtoK:
            warnings.warn(f"Invalid temperature: {celsius}°C. Adjusted to absolute zero "
                          f"It must be >= {-cDegreesFtoR} to avoid a domain error.", RuntimeWarning)
            celsius = -cDegreesCtoK
        elif celsius < atmo.cLowestTempC:
            celsius = atmo.cLowestTempC
            warnings.warn(f"Reached minimum temperature limit. Adjusted to {celsius}°C "
                          "redefine 'cLowestTempF' constant to increase it ", RuntimeWarning)

        kelvin = celsius + cDegreesCtoK
        pressure = atmo._p0 * pow(1 + cLapseRateKperFoot * (altitude - atmo._a0) / (atmo._t0 + cDegreesCtoK),
                            cPressureExponent)
        density_delta = ((atmo._t0 + cDegreesCtoK) * pressure) / (atmo._p0 * kelvin)
        density_ratio[0] = atmo.density_ratio * density_delta
        # Alternative exponential approximation to density:
        #density_ratio[0] = atmo.density_ratio * exp(-(altitude - atmo._a0) / 34112.0)
        mach[0] = sqrt(kelvin) * cSpeedOfSoundMetric * mToFeet
        #debug
        #print(f"Altitude: {altitude}, {atmo._t0}°C now {celsius}°C, pressure {atmo._p0} now {pressure}hPa >> {density_ratio[0]} from density_delta {density_delta}")

cdef V3dT wind_to_c_vector(Wind_t * w):
    cdef:
        # Downrange (x-axis) wind velocity component:
        double range_component = w.velocity * cos(w.direction_from)
        # Downrange (x-axis) wind velocity component:
        double cross_component = w.velocity * sin(w.direction_from)
    return V3dT(range_component, 0., cross_component)

# cdef void free_trajectory(ShotData_t * t):
#     if t.mach_list != NULL:
#         if t.mach_list.array != NULL:
#             free(t.mach_list.array)  # Free the array inside MachList_t
#             t.mach_list.array = NULL  # Avoid dangling pointer
#
#         free(t.mach_list)  # Free the MachList_t struct itself
#         t.mach_list = NULL  # Avoid dangling pointer


#
# # Function to calculate the curve
# cdef Curve_t calculate_curve(list[object] data_points):
#     cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
#     cdef Curve_t curve
#     cdef int i, num_points, len_data_points, len_data_range
#
#     len_data_points = len(data_points)
#     len_data_range = len_data_points - 1
#
#     # Allocate memory for the memory view (typed array of CurvePoint_t)
#     curve.points = <CurvePoint_t[:]>malloc(len_data_points * sizeof(CurvePoint_t))
#     if curve.points is NULL:
#         raise MemoryError("Unable to allocate memory for curve points")
#
#     # First point: Calculate rate and initialize the first curve point
#     rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
#     curve.points[0] = CurvePoint_t(0, rate, data_points[0].CD - data_points[0].Mach * rate)
#
#     # Loop through the data points and calculate the curve points
#     for i in range(1, len_data_range):
#         x1 = data_points[i - 1].Mach
#         x2 = data_points[i].Mach
#         x3 = data_points[i + 1].Mach
#         y1 = data_points[i - 1].CD
#         y2 = data_points[i].CD
#         y3 = data_points[i + 1].CD
#         a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
#                 (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
#         b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
#         c = y1 - (a * x1 * x1 + b * x1)
#         curve.points[i] = CurvePoint_t(a, b, c)
#
#     # Last point: Calculate rate for the final point and set the last curve point
#     num_points = len_data_points
#     rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
#            (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
#     curve.points[len_data_points - 1] = CurvePoint_t(0, rate, data_points[num_points - 1].CD - data_points[num_points - 1].Mach * rate)
#
#     return curve
