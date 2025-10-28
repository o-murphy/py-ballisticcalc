#include "bclib.h"
#include "v3d.h"
#include "interp.h"
#include <math.h>
#include <stddef.h> // For size_t
#include <stdio.h>  // For warnings (printf used here)
#include <float.h>  // For fabs()
#include <stdlib.h>

LogLevel global_log_level = LOG_LEVEL_CRITICAL; // DIsabled by default

void setLogLevel(LogLevel level)
{
    global_log_level = level;
    C_LOG(LOG_LEVEL_INFO, "Log level set to %d\n", level);
}

void initLogLevel()
{
    const char *env_level_str = getenv("BCLIB_LOG_LEVEL");

    if (env_level_str != NULL)
    {
        int env_level = atoi(env_level_str);

        if (env_level >= 0)
        {
            global_log_level = env_level;
            C_LOG(LOG_LEVEL_INFO, "Log level set from environment variable BCLIB_LOG_LEVEL to %d\n", global_log_level);
            return;
        }
    }

    C_LOG(LOG_LEVEL_INFO, "Log level defaulted to %d\n", global_log_level);
}

// Constants for unit conversions and atmospheric calculations
const double cEarthAngularVelocityRadS = 7.2921159e-5;
const double cDegreesFtoR = 459.67;
const double cDegreesCtoK = 273.15;
const double cSpeedOfSoundImperial = 49.0223;
const double cSpeedOfSoundMetric = 20.0467;
const double cLapseRateKperFoot = -0.0019812;
const double cLapseRateImperial = -0.00356616;
const double cPressureExponent = 5.255876;
const double cLowestTempF = -130.0;
const double mToFeet = 3.280839895;
const double cMaxWindDistanceFeet = 1e8;

void Curve_t_release(Curve_t *curve_ptr)
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

void MachList_t_release(MachList_t *mach_list_ptr)
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

void ShotProps_t_release(ShotProps_t *shot_props_ptr)
{
    if (shot_props_ptr == NULL)
        return;

    Curve_t_release(&shot_props_ptr->curve);
    MachList_t_release(&shot_props_ptr->mach_list);
    WindSock_t_release(&shot_props_ptr->wind_sock);
}

/**
 * @brief Litz spin-drift approximation
 * @param shot_props_ptr Pointer to ShotProps_t containing shot parameters.
 * @param time Time of flight in seconds.
 * @return Windage due to spin drift, in feet.
 */
double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time)
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

ErrorType ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr)
{
    if (shot_props_ptr == NULL)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return T_INPUT_ERROR;
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
            C_LOG(LOG_LEVEL_ERROR, "Division by zero in stability coefficient calculation.");
            return T_ZERO_DIVISION_ERROR; // Exit if denominator is zero
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
            C_LOG(LOG_LEVEL_ERROR, "Division by zero in ftp calculation.");
            return T_ZERO_DIVISION_ERROR; // Exit if pt is zero
        }

        shot_props_ptr->stability_coefficient = sd * fv * ftp;
    }
    else
    {
        shot_props_ptr->stability_coefficient = 0.0;
    }
    C_LOG(LOG_LEVEL_DEBUG, "Updated stability coefficient: %.6f", shot_props_ptr->stability_coefficient);
    return T_NO_ERROR;
}

static inline double calculateByCurveAndMachList(
    const MachList_t *restrict mach_list_ptr,
    const Curve_t *restrict curve_ptr,
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
    const CurvePoint_t seg = curve_ptr->points[i];
    const double dx = mach - xs[i];

    // Horner's method
    return seg.d + dx * (seg.c + dx * (seg.b + dx * seg.a));
}

/**
 * @brief Computes the drag force coefficient (Cd) for a projectile at a given Mach number.
 *
 * This function calculates the drag coefficient based on the bullet's ballistic coefficient (BC)
 * and an empirical drag curve interpolated at the given Mach value.
 *
 * The drag force is derived from the formula:
 *     Fd = V^2 * Cd * AirDensity * S / (2 * m)
 * where:
 *     - Standard air density is assumed to be 0.076474 lb/ft³,
 *     - S is cross-sectional area (π * d² / 4), where d is in inches,
 *     - m is mass in pounds,
 *     - BC encodes m/d² in lb/in² and is converted using factor 144 in²/ft².
 *
 * The constant 2.08551e-04 comes from:
 *     0.076474 * π / (4 * 2 * 144)
 *
 * @param shot_props_ptr Pointer to the ShotProps_t structure containing BC, drag curve, and Mach list.
 * @param mach Mach number at which to evaluate the drag.
 * @return Drag coefficient Cd scaled by BC.
 */
double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach)
{
    double cd = calculateByCurveAndMachList(
        &shot_props_ptr->mach_list,
        &shot_props_ptr->curve,
        mach);
    return cd * 2.08551e-04 / shot_props_ptr->bc;
}

void Atmosphere_t_updateDensityFactorAndMachForAltitude(
    const Atmosphere_t *restrict atmo_ptr,
    double altitude,
    double *restrict density_ratio_ptr,
    double *restrict mach_ptr)
{
    const double alt_diff = altitude - atmo_ptr->_a0;

    // Fast check
    if (fabs(alt_diff) < 30.0)
    {
        // Close enough to base altitude, use stored values
        *density_ratio_ptr = atmo_ptr->density_ratio;
        *mach_ptr = atmo_ptr->_mach;
        return;
    }

    double celsius = alt_diff * cLapseRateKperFoot + atmo_ptr->_t0;

    if (altitude > 36089.0)
    {
        // Warning: altitude above troposphere
        C_LOG(LOG_LEVEL_WARNING, "Density request for altitude above troposphere. Atmospheric model not valid here.");
    }

    // Clamp temperature
    const double min_temp = -cDegreesCtoK;
    if (celsius < min_temp)
    {
        C_LOG(LOG_LEVEL_WARNING, "Invalid temperature %.2f °C. Adjusted to %.2f °C.", celsius, min_temp);
        celsius = min_temp;
    }
    else if (celsius < atmo_ptr->cLowestTempC)
    {
        celsius = atmo_ptr->cLowestTempC;
        C_LOG(LOG_LEVEL_WARNING, "Reached minimum temperature limit. Adjusted to %.2f °C.", celsius);
    }

    const double kelvin = celsius + cDegreesCtoK;
    const double base_kelvin = atmo_ptr->_t0 + cDegreesCtoK;

    // Pressure calculation using barometric formula
    const double pressure = atmo_ptr->_p0 * pow(
                                                1.0 + cLapseRateKperFoot * alt_diff / base_kelvin,
                                                cPressureExponent);

    const double density_delta = (base_kelvin * pressure) / (atmo_ptr->_p0 * kelvin);

    *density_ratio_ptr = atmo_ptr->density_ratio * density_delta;

    // Mach 1 speed at altitude (fps)
    *mach_ptr = sqrt(kelvin) * cSpeedOfSoundMetric * mToFeet;

    C_LOG(LOG_LEVEL_DEBUG, "Altitude: %.2f, Base Temp: %.2f°C, Current Temp: %.2f°C, Base Pressure: %.2f hPa, Current Pressure: %.2f hPa, Density ratio: %.6f\n",
          altitude, atmo_ptr->_t0, celsius, atmo_ptr->_p0, pressure, *density_ratio_ptr);
}

static inline V3dT Wind_t_to_V3dT(const Wind_t *restrict wind_ptr)
{
    const double dir = wind_ptr->direction_from;
    const double vel = wind_ptr->velocity;

    return (V3dT){
        .x = vel * cos(dir),
        .y = 0.0,
        .z = vel * sin(dir)};
}

ErrorType WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds)
{
    if (ws == NULL)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return T_INPUT_ERROR;
    }

    ws->length = (int)length;
    ws->winds = winds;

    ws->current = 0;
    ws->next_range = cMaxWindDistanceFeet;

    ws->last_vector_cache.x = 0.0;
    ws->last_vector_cache.y = 0.0;
    ws->last_vector_cache.z = 0.0;

    return WindSock_t_updateCache(ws);
}

void WindSock_t_release(WindSock_t *ws)
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
    WindSock_t_init(ws, 0, NULL);
}

V3dT WindSock_t_currentVector(const WindSock_t *wind_sock)
{
    if (wind_sock == NULL)
    {
        return (V3dT){0.0, 0.0, 0.0};
    }
    return wind_sock->last_vector_cache;
}

ErrorType WindSock_t_updateCache(WindSock_t *ws)
{
    if (ws == NULL)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return T_INPUT_ERROR;
    }

    if (ws->current < ws->length)
    {
        Wind_t cur_wind = ws->winds[ws->current];
        ws->last_vector_cache = Wind_t_to_V3dT(&cur_wind);
        ws->next_range = cur_wind.until_distance;
    }
    else
    {
        ws->last_vector_cache.x = 0.0;
        ws->last_vector_cache.y = 0.0;
        ws->last_vector_cache.z = 0.0;
        ws->next_range = cMaxWindDistanceFeet;
    }
    return T_NO_ERROR;
}

V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param)
{
    V3dT zero_vector = {0.0, 0.0, 0.0};

    if (ws == NULL)
    {
        return zero_vector;
    }

    if (next_range_param >= ws->next_range)
    {
        ws->current += 1;

        if (ws->current >= ws->length)
        {
            ws->last_vector_cache = zero_vector;
            ws->next_range = cMaxWindDistanceFeet;
        }
        else
        {
            // If cache update fails, return zero vector
            if (WindSock_t_updateCache(ws) != T_NO_ERROR)
            {
                C_LOG(LOG_LEVEL_WARNING, "Failed. Returning zero vector.");
                return zero_vector;
            }
        }
    }

    return ws->last_vector_cache;
}

// helpers
double getCorrection(double distance, double offset)
{
    if (distance != 0.0)
    {
        return atan2(offset, distance);
    }
    C_LOG(LOG_LEVEL_ERROR, "Division by zero in getCorrection.");
    return 0.0;
}

double calculateEnergy(double bulletWeight, double velocity)
{
    return bulletWeight * velocity * velocity / 450400.0;
}

double calculateOgw(double bulletWeight, double velocity)
{
    return bulletWeight * bulletWeight * velocity * velocity * velocity * 1.5e-12;
}

/**
 * @brief Calculate Coriolis acceleration in local coordinates
 * @param coriolis_ptr Pointer to Coriolis_t containing precomputed transformation data
 * @param velocity Pointer to ground velocity of projectile
 * @param accel_ptr Pointer to store acceleration in local coordinates
 */
void Coriolis_t_coriolis_acceleration_local(
    const Coriolis_t *restrict coriolis_ptr,
    const V3dT *restrict velocity_ptr,
    V3dT *restrict accel_ptr)
{
    // Early exit for most common case
    if (coriolis_ptr->flat_fire_only)
    {
        *accel_ptr = (V3dT){0.0, 0.0, 0.0};
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

    // Transform velocity to ENU
    const double vel_east = vx * range_east + vz * cross_east;
    const double vel_north = vx * range_north + vz * cross_north;
    const double vel_up = vy;

    // Coriolis acceleration in ENU
    const double factor = -2.0 * cEarthAngularVelocityRadS;
    const double sin_lat = coriolis_ptr->sin_lat;
    const double cos_lat = coriolis_ptr->cos_lat;

    const double accel_east = factor * (cos_lat * vel_up - sin_lat * vel_north);
    const double accel_north = factor * sin_lat * vel_east;
    const double accel_up = factor * (-cos_lat * vel_east);

    // Transform back to local coordinates
    accel_ptr->x = accel_east * range_east + accel_north * range_north;
    accel_ptr->y = accel_up;
    accel_ptr->z = accel_east * cross_east + accel_north * cross_north;
}

// Lookup table
static inline double get_key_value(const BaseTrajData_t *restrict p, InterpKey key_kind)
{
    switch (key_kind)
    {
    case KEY_TIME:
        return p->time;
    case KEY_MACH:
        return p->mach;
    case KEY_POS_X:
        return p->position.x;
    case KEY_POS_Y:
        return p->position.y;
    case KEY_POS_Z:
        return p->position.z;
    case KEY_VEL_X:
        return p->velocity.x;
    case KEY_VEL_Y:
        return p->velocity.y;
    case KEY_VEL_Z:
        return p->velocity.z;
    default:
        return 0.0;
    }
}

ErrorType BaseTrajData_t_interpolate(
    InterpKey key_kind,
    double key_value,
    const BaseTrajData_t *restrict p0,
    const BaseTrajData_t *restrict p1,
    const BaseTrajData_t *restrict p2,
    BaseTrajData_t *restrict out)
{
    if (!p0 || !p1 || !p2 || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Invalid input (NULL pointer).");
        return T_INPUT_ERROR;
    }

    // Get key values
    const double x0 = get_key_value(p0, key_kind);
    const double x1 = get_key_value(p1, key_kind);
    const double x2 = get_key_value(p2, key_kind);

    // Guard against degenerate segments
    if (x0 == x1 || x0 == x2 || x1 == x2)
    {
        return T_ZERO_DIVISION_ERROR;
    }

    // Cache position and velocity
    const V3dT vp0 = p0->position;
    const V3dT vp1 = p1->position;
    const V3dT vp2 = p2->position;
    const V3dT vv0 = p0->velocity;
    const V3dT vv1 = p1->velocity;
    const V3dT vv2 = p2->velocity;

    // Scalar interpolation using PCHIP

    // Interpolate all scalar fields
    out->time = (key_kind == KEY_TIME) ? key_value : interpolate_3_pt(key_value, x0, x1, x2, p0->time, p1->time, p2->time);
    out->position = (V3dT){
        interpolate_3_pt(key_value, x0, x1, x2, vp0.x, vp1.x, vp2.x),
        interpolate_3_pt(key_value, x0, x1, x2, vp0.y, vp1.y, vp2.y),
        interpolate_3_pt(key_value, x0, x1, x2, vp0.z, vp1.z, vp2.z)};
    out->velocity = (V3dT){
        interpolate_3_pt(key_value, x0, x1, x2, vv0.x, vv1.x, vv2.x),
        interpolate_3_pt(key_value, x0, x1, x2, vv0.y, vv1.y, vv2.y),
        interpolate_3_pt(key_value, x0, x1, x2, vv0.z, vv1.z, vv2.z)};

    out->mach = (key_kind == KEY_MACH) ? key_value : interpolate_3_pt(key_value, x0, x1, x2, p0->mach, p1->mach, p2->mach);

    return T_NO_ERROR;
}
