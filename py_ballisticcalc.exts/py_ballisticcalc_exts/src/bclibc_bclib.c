#include "bclibc_bclib.h"
#include "bclibc_v3d.h"
#include "bclibc_interp.h"
#include <math.h>
#include <stddef.h> // For size_t
#include <stdio.h>  // For warnings (printf used here)
#include <float.h>  // For fabs()
#include <stdlib.h>

// Constants for unit conversions and atmospheric calculations
/**
 * @brief Earth's angular velocity in radians per second.
 */
const double BCLIBC_cEarthAngularVelocityRadS = 7.2921159e-5;
/**
 * @brief Conversion factor from degrees Fahrenheit to degrees Rankine.
 */
const double BCLIBC_cDegreesFtoR = 459.67;
/**
 * @brief Conversion factor from degrees Celsius to Kelvin.
 */
const double BCLIBC_cDegreesCtoK = 273.15;
/**
 * @brief Constant for speed of sound calculation in Imperial units (fps).
 *
 * (Approx. $\sqrt{\gamma R}$)
 */
const double BCLIBC_cSpeedOfSoundImperial = 49.0223;
/**
 * @brief Constant for speed of sound calculation in Metric units.
 *
 * (Approx. $\sqrt{\gamma R}$)
 */
const double BCLIBC_cSpeedOfSoundMetric = 20.0467;
/**
 * @brief Standard lapse rate in Kelvin per foot in the troposphere.
 */
const double BCLIBC_cLapseRateKperFoot = -0.0019812;
/**
 * @brief Standard lapse rate in Imperial units (degrees per foot).
 */
const double BCLIBC_cLapseRateImperial = -0.00356616;
/**
 * @brief Exponent used in the barometric formula for pressure calculation.
 *
 * (Approx. $g / (L \cdot R)$)
 */
const double BCLIBC_cPressureExponent = 5.255876;
/**
 * @brief Lowest allowed temperature in Fahrenheit for atmospheric model.
 */
const double BCLIBC_cLowestTempF = -130.0;
/**
 * @brief Conversion factor from meters to feet.
 */
const double BCLIBC_mToFeet = 3.280839895;
/**
 * @brief Maximum distance in feet for a wind segment (used as a sentinel value).
 */
const double BCLIBC_cMaxWindDistanceFeet = 1e8;

const double BCLIBC_cGravityImperial = 32.17405;

/**
 * @brief Releases memory associated with a BCLIBC_Curve structure.
 *
 * Frees the dynamically allocated array of points and resets the length to 0.
 * Handles NULL pointer gracefully.
 *
 * @param curve_ptr Pointer to the BCLIBC_Curve structure to release.
 */
void BCLIBC_Curve_release(BCLIBC_Curve *curve_ptr)
{
    if (curve_ptr == NULL)
        return;

    if (curve_ptr->points != NULL)
    {
        free(curve_ptr->points);
        curve_ptr->points = NULL;
    }

    curve_ptr->length = 0;
}

/**
 * @brief Releases memory associated with a BCLIBC_MachList structure.
 *
 * Frees the dynamically allocated array of Mach numbers and resets the length to 0.
 * Handles NULL pointer gracefully.
 *
 * @param mach_list_ptr Pointer to the BCLIBC_MachList structure to release.
 */
void BCLIBC_MachList_release(BCLIBC_MachList *mach_list_ptr)
{
    if (mach_list_ptr == NULL)
        return;

    if (mach_list_ptr->array != NULL)
    {
        free(mach_list_ptr->array);
        mach_list_ptr->array = NULL;
    }

    mach_list_ptr->length = 0;
}

/**
 * @brief Releases all dynamically allocated resources within a BCLIBC_ShotProps structure.
 *
 * Calls release functions for the internal BCLIBC_Curve, BCLIBC_MachList, and BCLIBC_WindSock components.
 *
 * @param shot_props_ptr Pointer to the BCLIBC_ShotProps structure to release.
 */
void BCLIBC_ShotProps_release(BCLIBC_ShotProps *shot_props_ptr)
{
    if (shot_props_ptr == NULL)
        return;

    BCLIBC_Curve_release(&shot_props_ptr->curve);
    BCLIBC_MachList_release(&shot_props_ptr->mach_list);
    BCLIBC_WindSock_release(&shot_props_ptr->wind_sock);
}

/**
 * @brief Litz spin-drift approximation
 *
 * Calculates the lateral displacement (windage) due to spin drift using
 * Litz's approximation formula. This formula provides an estimate based on
 * the stability coefficient and time of flight.
 *
 * Formula used (converted to feet):
 * $\text{Spin Drift (ft)} = \text{sign} \cdot \frac{1.25 \cdot (S_g + 1.2) \cdot \text{time}^{1.83}}{12.0}$
 * where $S_g$ is the stability coefficient.
 *
 * @param shot_props_ptr Pointer to BCLIBC_ShotProps containing shot parameters (twist, stability_coefficient).
 * @param time Time of flight in seconds.
 * @return Windage due to spin drift, in feet. Returns 0.0 if twist or stability_coefficient is zero.
 */
double BCLIBC_ShotProps_spinDrift(const BCLIBC_ShotProps *shot_props_ptr, double time)
{
    double sign;

    // Check if twist and stability_coefficient are non-zero.
    // In C, comparing doubles directly to 0 can sometimes be problematic due to
    // floating-point precision. However, for typical use cases here, direct
    // comparison with 0 is often acceptable if the values are expected to be
    // exactly 0 or significantly non-zero. If extreme precision is needed for
    // checking "effectively zero", you might use an epsilon (e.g., fabs(val) > EPSILON).
    if (shot_props_ptr->twist != 0 && shot_props_ptr->stability_coefficient != 0)
    {
        // Determine the sign based on twist direction.
        if (shot_props_ptr->twist > 0)
        {
            sign = 1.0;
        }
        else
        {
            sign = -1.0;
        }
        // Calculate the spin drift using the Litz approximation formula.
        // The division by 12 converts the result from inches (implied by Litz formula) to feet.
        return sign * (1.25 * (shot_props_ptr->stability_coefficient + 1.2) * pow(time, 1.83)) / 12.0;
    }
    // If either twist or stability_coefficient is zero, return 0.
    return 0.0;
}

/**
 * @brief Updates the Miller stability coefficient ($S_g$) for the projectile.
 *
 * Calculates the Miller stability coefficient based on bullet dimensions, weight,
 * muzzle velocity, and atmospheric conditions ($\text{temperature, pressure}$).
 * The result is stored in `shot_props_ptr->stability_coefficient`.
 *
 * Formula components:
 * - $\text{sd}$ (Stability Divisor)
 * - $\text{fv}$ (Velocity Factor)
 * - $\text{ftp}$ (Temperature/Pressure Factor)
 * - $S_g = \text{sd} \cdot \text{fv} \cdot \text{ftp}$
 *
 * @param shot_props_ptr Pointer to BCLIBC_ShotProps containing parameters like twist, length, diameter, weight, muzzle_velocity, and atmo.
 * @return BCLIBC_E_NO_ERROR on success, BCLIBC_E_INPUT_ERROR for NULL input, BCLIBC_E_ZERO_DIVISION_ERROR if a division by zero occurs during calculation.
 */
BCLIBC_ErrorType BCLIBC_ShotProps_updateStabilityCoefficient(BCLIBC_ShotProps *shot_props_ptr)
{
    if (shot_props_ptr == NULL)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }
    /* Miller stability coefficient */
    double twist_rate, length, sd, fv, ft, pt, ftp;

    // Check for non-zero or valid input values before calculation
    if (shot_props_ptr->twist != 0.0 &&
        shot_props_ptr->length != 0.0 &&
        shot_props_ptr->diameter != 0.0 &&
        shot_props_ptr->atmo._p0 != 0.0)
    {
        twist_rate = fabs(shot_props_ptr->twist) / shot_props_ptr->diameter;
        length = shot_props_ptr->length / shot_props_ptr->diameter;

        // Ensure denominator components are non-zero to avoid division by zero
        // This check is crucial for robustness in C
        double denom_part1 = pow(twist_rate, 2);
        double denom_part2 = pow(shot_props_ptr->diameter, 3);
        double denom_part3 = length;
        double denom_part4 = (1 + pow(length, 2));

        if (denom_part1 != 0.0 && denom_part2 != 0.0 && denom_part3 != 0.0 && denom_part4 != 0.0)
        {
            sd = 30.0 * shot_props_ptr->weight / (denom_part1 * denom_part2 * denom_part3 * denom_part4);
        }
        else
        {
            shot_props_ptr->stability_coefficient = 0.0;
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Division by zero in stability coefficient calculation.");
            return BCLIBC_E_ZERO_DIVISION_ERROR; // Exit if denominator is zero
        }

        fv = pow(shot_props_ptr->muzzle_velocity / 2800.0, 1.0 / 3.0);
        ft = (shot_props_ptr->atmo._t0 * 9.0 / 5.0) + 32.0; // Convert from Celsius to Fahrenheit
        pt = shot_props_ptr->atmo._p0 / 33.863881565591;    // Convert hPa to inHg

        // Ensure pt is not zero before division
        if (pt != 0.0)
        {
            ftp = ((ft + 460.0) / (59.0 + 460.0)) * (29.92 / pt);
        }
        else
        {
            shot_props_ptr->stability_coefficient = 0.0;
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Division by zero in ftp calculation.");
            return BCLIBC_E_ZERO_DIVISION_ERROR; // Exit if pt is zero
        }

        shot_props_ptr->stability_coefficient = sd * fv * ftp;
    }
    else
    {
        // If critical parameters are zero, stability coefficient is meaningless or zero
        shot_props_ptr->stability_coefficient = 0.0;
    }
    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Updated stability coefficient: %.6f", shot_props_ptr->stability_coefficient);
    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Interpolates a value from a Mach list and a curve using the PCHIP method.
 *
 * This function performs an optimized binary search to find the correct segment
 * in the `mach_list_ptr` and then uses the corresponding cubic polynomial segment
 * from `curve_ptr` (Horner's method) to interpolate the value at the given Mach number.
 *
 * The curve is assumed to represent the ballistic coefficient or a drag curve.
 *
 * @param mach_list_ptr Pointer to the BCLIBC_MachList containing the Mach segment endpoints (x values).
 * @param curve_ptr Pointer to the BCLIBC_Curve containing the PCHIP cubic segment coefficients (a, b, c, d).
 * @param mach The Mach number at which to interpolate.
 * @return The interpolated value (e.g., drag coefficient or BC factor). Returns 0.0 if insufficient data or out of range.
 */
static inline double calculateByCurveAndMachList(
    const BCLIBC_MachList *restrict mach_list_ptr,
    const BCLIBC_Curve *restrict curve_ptr,
    double mach)
{
    const double *restrict xs = mach_list_ptr->array;
    const int n = (int)mach_list_ptr->length;

    if (n < 2)
    {
        // insufficient data; return 0
        return 0.0;
    }

    // Clamp to range endpoints
    int i;
    if (mach <= xs[0])
    {
        i = 0;
    }
    else if (mach >= xs[n - 1])
    {
        i = n - 2;
    }
    else
    {
        // Optimized binary search
        int lo = 0, hi = n - 1;
        while (lo < hi)
        {
            int mid = lo + ((hi - lo) >> 1); // Bitshift is fater
            if (xs[mid] < mach)
                lo = mid + 1;
            else
                hi = mid;
        }
        i = lo - 1;
        // Clamping not needed more
    }

    // Storing struct locally for better access
    const BCLIBC_CurvePoint seg = curve_ptr->points[i];
    const double dx = mach - xs[i];

    // Horner's method for PCHIP interpolation:
    // $y = d + dx \cdot (c + dx \cdot (b + dx \cdot a))$
    return seg.d + dx * (seg.c + dx * (seg.b + dx * seg.a));
}

/**
 * @brief Computes the scaled drag force coefficient ($C_d$) for a projectile at a given Mach number.
 *
 * This function calculates the drag coefficient using a cubic spline interpolation
 * (via `calculateByCurveAndMachList`) and scales it by a constant factor and the
 * bullet's ballistic coefficient (BC). The result is $\frac{C_d}{\text{BC} \cdot \text{scale\_factor}}$.
 *
 * The constant $2.08551\text{e-}04$ is a combination of standard air density,
 * cross-sectional area conversion, and mass conversion factors.
 *
 * Formula used:
 * $\text{Scaled } C_d = \frac{C_d(\text{Mach}) \cdot 2.08551\text{e-}04}{\text{BC}}$
 *
 * @param shot_props_ptr Pointer to the BCLIBC_ShotProps structure containing BC, drag curve, and Mach list.
 * @param mach Mach number at which to evaluate the drag.
 * @return Drag coefficient $C_d$ scaled by $\text{BC}$ and conversion factors, in units suitable for the trajectory calculation.
 */
double BCLIBC_ShotProps_dragByMach(const BCLIBC_ShotProps *shot_props_ptr, double mach)
{
    double cd = calculateByCurveAndMachList(
        &shot_props_ptr->mach_list,
        &shot_props_ptr->curve,
        mach);
    return cd * 2.08551e-04 / shot_props_ptr->bc;
}

/**
 * @brief Updates the density ratio and speed of sound (Mach 1) for a given altitude.
 *
 * This function calculates the new atmospheric pressure, temperature, and resulting
 * density ratio and speed of sound (Mach 1) at a given altitude using the
 * Standard Atmosphere model for the troposphere, adjusted for base conditions ($\text{atmo\_ptr->_t0, atmo\_ptr->_p0, atmo\_ptr->_a0}$).
 *
 * The barometric formula is used for pressure, and the lapse rate for temperature.
 *
 * @param atmo_ptr Pointer to the base BCLIBC_Atmosphere structure.
 * @param altitude The new altitude in feet.
 * @param density_ratio_ptr Pointer to store the calculated density ratio ($\rho / \rho_{\text{std}}$).
 * @param mach_ptr Pointer to store the calculated speed of sound (Mach 1) in feet per second (fps).
 */
void BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
    const BCLIBC_Atmosphere *restrict atmo_ptr,
    double altitude,
    double *restrict density_ratio_ptr,
    double *restrict mach_ptr)
{
    const double alt_diff = altitude - atmo_ptr->_a0;

    // Fast check: if altitude is close to base altitude, use stored values
    if (fabs(alt_diff) < 30.0)
    {
        // Close enough to base altitude, use stored values
        *density_ratio_ptr = atmo_ptr->density_ratio;
        *mach_ptr = atmo_ptr->_mach;
        return;
    }

    double celsius = alt_diff * BCLIBC_cLapseRateKperFoot + atmo_ptr->_t0;

    if (altitude > 36089.0)
    {
        // Warning: altitude above standard troposphere height
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_WARNING, "Density request for altitude above troposphere. Atmospheric model not valid here.");
    }

    // Clamp temperature to prevent non-physical results
    const double min_temp = -BCLIBC_cDegreesCtoK;
    if (celsius < min_temp)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_WARNING, "Invalid temperature %.2f °C. Adjusted to %.2f °C.", celsius, min_temp);
        celsius = min_temp;
    }
    else if (celsius < atmo_ptr->cLowestTempC)
    {
        celsius = atmo_ptr->cLowestTempC;
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_WARNING, "Reached minimum temperature limit. Adjusted to %.2f °C.", celsius);
    }

    const double kelvin = celsius + BCLIBC_cDegreesCtoK;
    const double base_kelvin = atmo_ptr->_t0 + BCLIBC_cDegreesCtoK;

    // Pressure calculation using barometric formula for the troposphere
    // $P = P_0 \cdot (1 + \frac{L \cdot \Delta h}{T_0})^ {g / (L \cdot R)}$
    const double pressure = atmo_ptr->_p0 * pow(
                                                1.0 + BCLIBC_cLapseRateKperFoot * alt_diff / base_kelvin,
                                                BCLIBC_cPressureExponent);

    // Density ratio calculation: $\frac{\rho}{\rho_{\text{std}}} = \frac{\rho_0}{\rho_{\text{std}}} \cdot \frac{P \cdot T_0}{P_0 \cdot T}$
    const double density_delta = (base_kelvin * pressure) / (atmo_ptr->_p0 * kelvin);

    *density_ratio_ptr = atmo_ptr->density_ratio * density_delta;

    // Mach 1 speed at altitude (fps): $a = \sqrt{\gamma R T}$
    *mach_ptr = sqrt(kelvin) * BCLIBC_cSpeedOfSoundMetric * BCLIBC_mToFeet;

    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Altitude: %.2f, Base Temp: %.2f°C, Current Temp: %.2f°C, Base Pressure: %.2f hPa, Current Pressure: %.2f hPa, Density ratio: %.6f\n",
               altitude, atmo_ptr->_t0, celsius, atmo_ptr->_p0, pressure, *density_ratio_ptr);
}

/**
 * @brief Converts a BCLIBC_Wind structure to a BCLIBC_V3dT vector.
 *
 * The wind vector components are calculated assuming a standard coordinate system
 * where x is positive downrange and z is positive across-range (windage).
 * Wind direction is 'from' the specified direction (e.g., $0^\circ$ is tailwind, $90^\circ$ is wind from the right).
 *
 * @param wind_ptr Pointer to the BCLIBC_Wind structure.
 * @return A BCLIBC_V3dT structure representing the wind velocity vector (x=downrange, y=vertical, z=crossrange).
 */
static inline BCLIBC_V3dT BCLIBC_WindToV3dT(const BCLIBC_Wind *restrict wind_ptr)
{
    const double dir = wind_ptr->direction_from;
    const double vel = wind_ptr->velocity;

    // Wind direction is from:
    // x = vel * cos(dir) (Downrange, positive is tailwind)
    // z = vel * sin(dir) (Crossrange, positive is wind from right)
    return (BCLIBC_V3dT){
        .x = vel * cos(dir),
        .y = 0.0,
        .z = vel * sin(dir)};
}

/**
 * @brief Initializes a BCLIBC_WindSock structure.
 *
 * Sets up the internal state, including the array of wind segments, the current
 * segment index, the range for the next segment, and initializes the wind vector cache.
 * Note: The `winds` array memory is expected to be managed externally or by a
 * higher-level function if it was dynamically allocated before calling this.
 *
 * @param ws Pointer to the BCLIBC_WindSock structure to initialize.
 * @param length The number of wind segments in the `winds` array.
 * @param winds Pointer to the array of BCLIBC_Wind structures.
 * @return BCLIBC_E_NO_ERROR on success, BCLIBC_E_INPUT_ERROR for NULL input.
 */
BCLIBC_ErrorType BCLIBC_WindSock_init(BCLIBC_WindSock *ws, size_t length, BCLIBC_Wind *winds)
{
    if (ws == NULL)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    ws->length = (int)length;
    ws->winds = winds;

    ws->current = 0;
    ws->next_range = BCLIBC_cMaxWindDistanceFeet;

    ws->last_vector_cache.x = 0.0;
    ws->last_vector_cache.y = 0.0;
    ws->last_vector_cache.z = 0.0;

    return BCLIBC_WindSock_updateCache(ws);
}

/**
 * @brief Releases memory associated with a BCLIBC_WindSock structure and resets state.
 *
 * Frees the dynamically allocated `winds` array and calls `BCLIBC_WindSock_init`
 * to reset the internal state to empty/safe values.
 *
 * @param ws Pointer to the BCLIBC_WindSock structure to release.
 */
void BCLIBC_WindSock_release(BCLIBC_WindSock *ws)
{
    if (ws == NULL)
    {
        return;
    }

    if (ws->winds != NULL)
    {
        free(ws->winds);
        ws->winds = NULL;
    }
    // Initialize to empty state after freeing
    BCLIBC_WindSock_init(ws, 0, NULL);
}

/**
 * @brief Returns the wind vector for the currently active wind segment.
 *
 * The vector is pre-calculated and stored in the cache.
 *
 * @param wind_sock Pointer to the BCLIBC_WindSock structure.
 * @return The current wind velocity vector (BCLIBC_V3dT). Returns a zero vector if the pointer is NULL.
 */
BCLIBC_V3dT BCLIBC_WindSock_currentVector(const BCLIBC_WindSock *wind_sock)
{
    if (wind_sock == NULL)
    {
        return (BCLIBC_V3dT){0.0, 0.0, 0.0};
    }
    return wind_sock->last_vector_cache;
}

/**
 * @brief Updates the internal wind vector cache and next range threshold.
 *
 * Fetches the data for the wind segment at `ws->current`, converts it to a vector,
 * and updates `ws->last_vector_cache` and `ws->next_range`.
 * If `ws->current` is out of bounds, the cache is set to a zero vector and the next range to `BCLIBC_cMaxWindDistanceFeet`.
 *
 * @param ws Pointer to the BCLIBC_WindSock structure.
 * @return BCLIBC_E_NO_ERROR on success, BCLIBC_E_INPUT_ERROR for NULL input.
 */
BCLIBC_ErrorType BCLIBC_WindSock_updateCache(BCLIBC_WindSock *ws)
{
    if (ws == NULL)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    if (ws->current < ws->length)
    {
        BCLIBC_Wind cur_wind = ws->winds[ws->current];
        ws->last_vector_cache = BCLIBC_WindToV3dT(&cur_wind);
        ws->next_range = cur_wind.until_distance;
    }
    else
    {
        // No more wind segments; set to zero wind
        ws->last_vector_cache.x = 0.0;
        ws->last_vector_cache.y = 0.0;
        ws->last_vector_cache.z = 0.0;
        ws->next_range = BCLIBC_cMaxWindDistanceFeet;
    }
    return BCLIBC_E_NO_ERROR;
}

/**
 * @brief Gets the current wind vector, updating to the next segment if necessary.
 *
 * Compares the given `next_range_param` (the current range in the simulation)
 * against the threshold for the current wind segment (`ws->next_range`).
 * If the threshold is met or exceeded, it advances to the next wind segment
 * and updates the cache.
 *
 * @param ws Pointer to the BCLIBC_WindSock structure.
 * @param next_range_param The current range (distance from muzzle) of the projectile.
 * @return The wind velocity vector (BCLIBC_V3dT) for the current or next applicable segment. Returns a zero vector if the pointer is NULL or an update fails.
 */
BCLIBC_V3dT BCLIBC_WindSock_vectorForRange(BCLIBC_WindSock *ws, double next_range_param)
{
    BCLIBC_V3dT zero_vector = {0.0, 0.0, 0.0};

    if (ws == NULL)
    {
        return zero_vector;
    }

    if (next_range_param >= ws->next_range)
    {
        ws->current += 1;

        if (ws->current >= ws->length)
        {
            // Reached the end of the wind segments
            ws->last_vector_cache = zero_vector;
            ws->next_range = BCLIBC_cMaxWindDistanceFeet;
        }
        else
        {
            // Move to the next wind segment
            // If cache update fails, return zero vector
            if (BCLIBC_WindSock_updateCache(ws) != BCLIBC_E_NO_ERROR)
            {
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_WARNING, "Failed. Returning zero vector.");
                return zero_vector;
            }
        }
    }

    return ws->last_vector_cache;
}

// helpers
/**
 * @brief Calculates the angular correction needed to hit a target.
 *
 * Computes the angle (in radians) to correct a shot based on the linear offset
 * at a given distance using the arc tangent function ($\arctan(\text{offset}/\text{distance})$).
 *
 * @param distance The distance to the target (or the point of offset).
 * @param offset The linear offset (e.g., vertical drop or windage).
 * @return The correction angle in radians. Returns 0.0 if distance is zero (to avoid division by zero).
 */
double BCLIBC_getCorrection(double distance, double offset)
{
    if (distance != 0.0)
    {
        return atan2(offset, distance);
    }
    BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Division by zero in BCLIBC_getCorrection.");
    return 0.0;
}

/**
 * @brief Calculates the kinetic energy of the projectile.
 *
 * Uses the formula: $\text{Energy (ft-lbs)} = \frac{\text{Weight (grains)} \cdot \text{Velocity (fps)}^2}{450400}$.
 *
 * @param bulletWeight Bullet weight in grains.
 * @param velocity Projectile velocity in feet per second (fps).
 * @return Kinetic energy in foot-pounds (ft-lbs).
 */
double BCLIBC_calculateEnergy(double bulletWeight, double velocity)
{
    return bulletWeight * velocity * velocity / 450400.0;
}

/**
 * @brief Calculates the Optimum Game Weight (OGW) factor.
 *
 * OGW is a metric that attempts to combine kinetic energy and momentum into a single number.
 * Formula used: $\text{OGW} = \text{Weight (grains)}^2 \cdot \text{Velocity (fps)}^3 \cdot 1.5\text{e-}12$.
 *
 * @param bulletWeight Bullet weight in grains.
 * @param velocity Projectile velocity in feet per second (fps).
 * @return The Optimum Game Weight (OGW) factor.
 */
double BCLIBC_calculateOgw(double bulletWeight, double velocity)
{
    return bulletWeight * bulletWeight * velocity * velocity * velocity * 1.5e-12;
}

void BCLIBC_Coriolis_flatFireOffsets(const BCLIBC_Coriolis *coriolis, double time, double distance_ft, double drop_ft, double *delta_y, double *delta_z)
{
    if (!coriolis->flat_fire_only)
    {
        *delta_y = 0.0;
        *delta_z = 0.0;
        return;
    }

    double horizontal = BCLIBC_cEarthAngularVelocityRadS * distance_ft * coriolis->sin_lat * time;
    double vertical = 0.0;
    if (coriolis->sin_az)
    {
        double vertical_factor = -2.0 * BCLIBC_cEarthAngularVelocityRadS * coriolis->muzzle_velocity_fps * coriolis->cos_lat * coriolis->sin_az;
        vertical = drop_ft * (vertical_factor / BCLIBC_cGravityImperial);
    }
    *delta_y = vertical;
    *delta_z = horizontal;
}

BCLIBC_V3dT BCLIBC_Coriolis_adjustRange(const BCLIBC_Coriolis *coriolis, double time, const BCLIBC_V3dT *range_vector)
{
    if (!coriolis || !coriolis->flat_fire_only)
    {
        return *range_vector;
    }
    double delta_y, delta_z;
    BCLIBC_Coriolis_flatFireOffsets(coriolis, time, range_vector->x, range_vector->y, &delta_y, &delta_z);
    if (delta_y == 0.0 && delta_z == 0.0)
    {
        return *range_vector;
    }
    return (BCLIBC_V3dT){range_vector->x, range_vector->y + delta_y, range_vector->z + delta_z};
}

BCLIBC_V3dT BCLIBC_adjustRangeFromCoriolis(const BCLIBC_Coriolis *coriolis, double time, const BCLIBC_V3dT *range_vector)
{
    if (!coriolis)
    {
        return *range_vector;
    }
    return BCLIBC_Coriolis_adjustRange(coriolis, time, range_vector);
}

/**
 * @brief Calculate Coriolis acceleration in local coordinates (range, up, crossrange).
 *
 * Transforms the projectile's ground velocity (local coordinates) to the
 * Earth-North-Up (ENU) coordinate system, calculates the Coriolis acceleration
 * in ENU, and then transforms the acceleration back to local coordinates.
 *
 * Coriolis acceleration formula in ENU:
 * - $\mathbf{a}_{\text{coriolis}} = -2 \cdot \mathbf{\omega}_{\text{earth}} \times \mathbf{v}_{\text{ENU}}$
 *
 * @param coriolis_ptr Pointer to BCLIBC_Coriolis containing precomputed transformation data ($\sin(\text{lat}), \cos(\text{lat})$, range/cross factors).
 * @param velocity_ptr Pointer to the projectile's ground velocity vector (local coordinates: x=range, y=up, z=crossrange).
 * @param accel_ptr Pointer to store the calculated Coriolis acceleration vector (local coordinates).
 */
void BCLIBC_Coriolis_coriolisAccelerationLocal(
    const BCLIBC_Coriolis *restrict coriolis_ptr,
    const BCLIBC_V3dT *restrict velocity_ptr,
    BCLIBC_V3dT *restrict accel_ptr)
{
    // Early exit for most common case (flat fire: Coriolis effect is ignored/zeroed)
    if (coriolis_ptr->flat_fire_only)
    {
        *accel_ptr = (BCLIBC_V3dT){0.0, 0.0, 0.0};
        return;
    }

    // Cache frequently used values
    const double vx = velocity_ptr->x;
    const double vy = velocity_ptr->y;
    const double vz = velocity_ptr->z;

    const double range_east = coriolis_ptr->range_east;
    const double range_north = coriolis_ptr->range_north;
    const double cross_east = coriolis_ptr->cross_east;
    const double cross_north = coriolis_ptr->cross_north;

    // Transform velocity to ENU (East, North, Up)
    const double vel_east = vx * range_east + vz * cross_east;
    const double vel_north = vx * range_north + vz * cross_north;
    const double vel_up = vy;

    // Coriolis acceleration in ENU
    const double factor = -2.0 * BCLIBC_cEarthAngularVelocityRadS;
    const double sin_lat = coriolis_ptr->sin_lat;
    const double cos_lat = coriolis_ptr->cos_lat;

    // $\mathbf{a}_{\text{coriolis}} = -2 \cdot \mathbf{\omega}_{\text{earth}} \times \mathbf{v}_{\text{ENU}}$
    // $\mathbf{\omega}_{\text{earth}} = \omega_e \cdot (0, \cos(\text{lat}), \sin(\text{lat}))$
    const double accel_east = factor * (cos_lat * vel_up - sin_lat * vel_north);
    const double accel_north = factor * sin_lat * vel_east;
    const double accel_up = factor * (-cos_lat * vel_east);

    // Transform back to local coordinates (x=range, y=up, z=crossrange)
    accel_ptr->x = accel_east * range_east + accel_north * range_north;
    accel_ptr->y = accel_up;
    accel_ptr->z = accel_east * cross_east + accel_north * cross_north;
}

/**
 * @brief Lookup table helper to retrieve a specific scalar value from BCLIBC_BaseTrajData.
 *
 * Used internally by the interpolation function to get the correct 'x' values
 * for the interpolation key.
 *
 * @param p Pointer to the BCLIBC_BaseTrajData structure.
 * @param key_kind The BCLIBC_BaseTrajSeq_InterpKey specifying which field to retrieve (e.g., BCLIBC_BASE_TRAJ_INTERP_KEY_TIME, BCLIBC_BASE_TRAJ_INTERP_KEY_MACH, BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X).
 * @return The value of the requested field. Returns 0.0 for an unknown key.
 */
static inline double get_key_value(const BCLIBC_BaseTrajData *restrict p, BCLIBC_BaseTrajSeq_InterpKey key_kind)
{
    switch (key_kind)
    {
    case BCLIBC_BASE_TRAJ_INTERP_KEY_TIME:
        return p->time;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_MACH:
        return p->mach;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X:
        return p->position.x;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y:
        return p->position.y;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z:
        return p->position.z;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X:
        return p->velocity.x;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y:
        return p->velocity.y;
    case BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z:
        return p->velocity.z;
    default:
        return 0.0;
    }
}

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
 * @return BCLIBC_E_NO_ERROR on success, BCLIBC_E_INPUT_ERROR for NULL input, BCLIBC_E_ZERO_DIVISION_ERROR for degenerate segments (identical key values).
 */
BCLIBC_ErrorType BCLIBC_BaseTrajData_interpolate(
    BCLIBC_BaseTrajSeq_InterpKey key_kind,
    double key_value,
    const BCLIBC_BaseTrajData *restrict p0,
    const BCLIBC_BaseTrajData *restrict p1,
    const BCLIBC_BaseTrajData *restrict p2,
    BCLIBC_BaseTrajData *restrict out)
{
    if (!p0 || !p1 || !p2 || !out)
    {
        BCLIBC_LOG(BCLIBC_LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return BCLIBC_E_INPUT_ERROR;
    }

    // Get key values
    const double x0 = get_key_value(p0, key_kind);
    const double x1 = get_key_value(p1, key_kind);
    const double x2 = get_key_value(p2, key_kind);

    // Guard against degenerate segments
    if (x0 == x1 || x0 == x2 || x1 == x2)
    {
        return BCLIBC_E_ZERO_DIVISION_ERROR;
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
    out->time = (key_kind == BCLIBC_BASE_TRAJ_INTERP_KEY_TIME) ? key_value : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0->time, p1->time, p2->time);
    out->position = (BCLIBC_V3dT){
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.x, vp1.x, vp2.x),
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.y, vp1.y, vp2.y),
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vp0.z, vp1.z, vp2.z)};
    out->velocity = (BCLIBC_V3dT){
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.x, vv1.x, vv2.x),
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.y, vv1.y, vv2.y),
        BCLIBC_interpolate3pt(key_value, x0, x1, x2, vv0.z, vv1.z, vv2.z)};

    out->mach = (key_kind == BCLIBC_BASE_TRAJ_INTERP_KEY_MACH) ? key_value : BCLIBC_interpolate3pt(key_value, x0, x1, x2, p0->mach, p1->mach, p2->mach);

    return BCLIBC_E_NO_ERROR;
}
