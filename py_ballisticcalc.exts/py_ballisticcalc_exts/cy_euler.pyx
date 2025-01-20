# noinspection PyUnresolvedReferences
from cython cimport final
from libc.stdlib cimport malloc, free
from libc.math cimport fabs, pow, atan2, exp, sqrt, sin, cos
from py_ballisticcalc_exts.vector cimport CVector
import warnings

@final
cdef Config_t config_bind(object config):
    return Config_t(
        config.max_calc_step_size_feet,
        config.chart_resolution,
        config.cZeroFindingAccuracy,
        config.cMinimumVelocity,
        config.cMaximumDrop,
        config.cMaxIterations,
        config.cGravityConstant,
        config.cMinimumAltitude,
    )

cdef double cy_get_calc_step(Config_t * config, double step = 0):
    cdef double preferred_step = config.max_calc_step_size_feet
    if step == 0:
        return preferred_step / 2.0
    return min(step, preferred_step) / 2.0

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
    curve.length = len_data_points
    curve.points = curve_points

    return curve

cdef double cy_calculate_by_curve_and_mach_list(MachList_t *mach_list, Curve_t *curve, double mach):
    cdef int num_points, mlo, mhi, mid, m
    cdef CurvePoint_t curve_m

    # Get the number of points in the curve
    num_points = int(curve.length)

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

cdef double cy_spin_drift(ShotData_t * t, double time):
    """Litz spin-drift approximation
    :param time: Time of flight
    :return: windage due to spin drift, in feet
    """
    cdef int sign
    if t.twist != 0:
        sign = 1 if t.twist > 0 else -1
        return sign * (1.25 * (t.stability_coefficient + 1.2) * pow(time, 1.83)) / 12
    return 0

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

cdef void cy_update_stability_coefficient(ShotData_t * t):
    """Miller stability coefficient"""
    cdef:
        double twist_rate, length, sd, fv, ft, pt, ftp
    if t.twist and t.length and t.diameter:
        twist_rate = fabs(t.twist) / t.diameter
        length = t.length / t.diameter
        sd = 30 * t.weight / (pow(twist_rate, 2) * pow(t.diameter, 3) * length * (1 + pow(length, 2)))
        fv = pow(t.muzzle_velocity / 2800, 1.0 / 3.0)
        ft = t.atmo._t0  # F
        pt = t.atmo._p0  # inHg
        ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
        t.stability_coefficient = sd * fv * ftp

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

cdef double cy_get_correction(double distance, double offset):
    if distance != 0:
        return atan2(offset, distance)
    return 0  # better None

cdef double cy_calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double cy_calculate_ogw(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12

cdef double cDegreesFtoR = 459.67
cdef double cSpeedOfSoundImperial = 49.0223
cdef double cLapseRateImperial = -3.56616e-03
cdef double cLowestTempF = -130

# Function to calculate density factor and Mach at altitude
cdef void update_density_factor_and_mach_for_altitude(
        Atmosphere_t * atmo, double altitude, double * density_ratio, double * mach
):
    """
    :param altitude: ASL in units of feet
    :return: density ratio and Mach 1 (fps) for the specified altitude
    """
    cdef double fahrenheit
    if fabs(atmo._a0 - altitude) < 30:
        density_ratio[0] = atmo.density_ratio
        mach[0] = atmo._mach1
    else:
        density_ratio[0] = exp(-altitude / 34112.0)
        fahrenheit = (altitude - atmo._a0) * cLapseRateImperial + atmo._t0

        if fahrenheit < cLowestTempF:
            fahrenheit = cLowestTempF
            warnings.warn(f"Reached minimum temperature limit. Adjusted to {cLowestTempF}°F "
                          "redefine 'cLowestTempF' constant to increase it ", RuntimeWarning)

        if fahrenheit < -cDegreesFtoR:
            fahrenheit = -cDegreesFtoR
            warnings.warn(f"Invalid temperature: {fahrenheit}°F. Adjusted to absolute zero "
                          f"It must be >= {-cDegreesFtoR} to avoid a domain error."
                          f"redefine 'cDegreesFtoR' constant to increase it", RuntimeWarning)

        mach[0] = sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

cdef CVector wind_to_c_vector(Wind_t * w):
    cdef:
        # Downrange (x-axis) wind velocity component:
        double range_component = w.velocity * cos(w.direction_from)
        # Downrange (x-axis) wind velocity component:
        double cross_component = w.velocity * sin(w.direction_from)
    return CVector(range_component, 0., cross_component)

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
