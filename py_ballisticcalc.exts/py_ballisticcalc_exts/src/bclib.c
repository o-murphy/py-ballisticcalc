#include "bclib.h"
#include "v3d.h"
#include <math.h>
#include <stddef.h>  // For size_t
#include <stdio.h>   // For warnings (printf used here)
#include <float.h>   // For fabs()
#include <stdlib.h>

// Constants for unit conversions and atmospheric calculations
const double cEarthAngularVelocityRadS = 7.2921159e-5;
const double cDegreesFtoR           = 459.67;
const double cDegreesCtoK           = 273.15;
const double cSpeedOfSoundImperial  = 49.0223;
const double cSpeedOfSoundMetric    = 20.0467;
const double cLapseRateKperFoot     = -0.0019812;
const double cLapseRateImperial     = -0.00356616;
const double cPressureExponent      = 5.255876;
const double cLowestTempF           = -130.0;
const double mToFeet                = 3.280839895;
const double cMaxWindDistanceFeet   = 1e8;

void Curve_t_free(Curve_t *curve_ptr) {
    if (curve_ptr != NULL && curve_ptr->points != NULL) {
        free(curve_ptr->points);
        curve_ptr->points = NULL;  // optional: avoid dangling pointer
        curve_ptr->length = 0;     // optional: reset length
    }
}

void MachList_t_free(MachList_t *mach_list_ptr) {
    if (mach_list_ptr != NULL && mach_list_ptr->array != NULL) {
        free((void *)mach_list_ptr->array);
        mach_list_ptr->array = NULL;  // avoid dangling pointer
        mach_list_ptr->length = 0;    // reset length
    }
}

void ShotProps_t_free(ShotProps_t *shot_props_ptr) {
    if (shot_props_ptr == NULL) return;

    Curve_t_free(&shot_props_ptr->curve);
    MachList_t_free(&shot_props_ptr->mach_list);
}

/**
 * @brief Litz spin-drift approximation
 * @param shot_props_ptr Pointer to ShotProps_t containing shot parameters.
 * @param time Time of flight in seconds.
 * @return Windage due to spin drift, in feet.
 */
double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time) {
    double sign;

    // Check if twist and stability_coefficient are non-zero.
    // In C, comparing doubles directly to 0 can sometimes be problematic due to
    // floating-point precision. However, for typical use cases here, direct
    // comparison with 0 is often acceptable if the values are expected to be
    // exactly 0 or significantly non-zero. If extreme precision is needed for
    // checking "effectively zero", you might use an epsilon (e.g., fabs(val) > EPSILON).
    if (shot_props_ptr->twist != 0 && shot_props_ptr->stability_coefficient != 0) {
        // Determine the sign based on twist direction.
        if (shot_props_ptr->twist > 0) {
            sign = 1.0;
        } else {
            sign = -1.0;
        }
        // Calculate the spin drift using the Litz approximation formula.
        // The division by 12 converts the result from inches (implied by Litz formula) to feet.
        return sign * (1.25 * (shot_props_ptr->stability_coefficient + 1.2) * pow(time, 1.83)) / 12.0;
    }
    // If either twist or stability_coefficient is zero, return 0.
    return 0.0;
}

int ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr) {
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

        if (denom_part1 != 0.0 && denom_part2 != 0.0 && denom_part3 != 0.0 && denom_part4 != 0.0) {
            sd = 30.0 * shot_props_ptr->weight / (denom_part1 * denom_part2 * denom_part3 * denom_part4);
        } else {
            shot_props_ptr->stability_coefficient = 0.0;
            return -1; // Exit if denominator is zero
        }

        fv = pow(shot_props_ptr->muzzle_velocity / 2800.0, 1.0 / 3.0);
        ft = (shot_props_ptr->atmo._t0 * 9.0 / 5.0) + 32.0;  // Convert from Celsius to Fahrenheit
        pt = shot_props_ptr->atmo._p0 / 33.863881565591;  // Convert hPa to inHg

        // Ensure pt is not zero before division
        if (pt != 0.0) {
            ftp = ((ft + 460.0) / (59.0 + 460.0)) * (29.92 / pt);
        } else {
            shot_props_ptr->stability_coefficient = 0.0;
            return -1; // Exit if pt is zero
        }

        shot_props_ptr->stability_coefficient = sd * fv * ftp;
    } else {
        shot_props_ptr->stability_coefficient = 0.0;
    }
    return 0;
}

double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                   const Curve_t *curve_ptr,
                                   double mach) {
    // PCHIP evaluation: find segment i with x in [x_i, x_{i+1}], then y = d + dx*(c + dx*(b + dx*a))
    const double *xs = mach_list_ptr->array;
    int n = (int)mach_list_ptr->length;     // number of knots
    if (n < 2) {
        // insufficient data; return 0
        return 0.0;
    }

    // Clamp to range endpoints
    int i;
    if (mach <= xs[0]) {
        i = 0;
    } else if (mach >= xs[n - 1]) {
        i = n - 2;
    } else {
        // lower_bound to find first j with xs[j] >= mach, then i = j - 1
        int lo = 0, hi = n - 1;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            if (xs[mid] < mach) lo = mid + 1; else hi = mid;
        }
        i = lo - 1;
        if (i < 0) i = 0;
        if (i > n - 2) i = n - 2;
    }

    CurvePoint_t seg = curve_ptr->points[i];
    double dx = mach - xs[i];
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
double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach) {
    double cd = calculateByCurveAndMachList(
        &shot_props_ptr->mach_list,
        &shot_props_ptr->curve,
        mach
    );
    return cd * 2.08551e-04 / shot_props_ptr->bc;
}

void Atmosphere_t_updateDensityFactorAndMachForAltitude(
    const Atmosphere_t *atmo_ptr,
    double altitude,
    double *density_ratio_ptr,
    double *mach_ptr)
{
    double celsius, kelvin, pressure, density_delta;

    if (fabs(atmo_ptr->_a0 - altitude) < 30.0) {
        // Close enough to base altitude, use stored values
        *density_ratio_ptr = atmo_ptr->density_ratio;
        *mach_ptr = atmo_ptr->_mach;
        return;
    }

    celsius = (altitude - atmo_ptr->_a0) * cLapseRateKperFoot + atmo_ptr->_t0;

    if (altitude > 36089.0) {
        // Warning: altitude above troposphere
        fprintf(stderr, "Warning: Density request for altitude above troposphere. Atmospheric model not valid here.\n");
    }

    if (celsius < -cDegreesCtoK) {
        fprintf(stderr, "Warning: Invalid temperature %.2f °C. Adjusted to absolute zero %.2f °C to avoid domain error.\n",
                celsius, -cDegreesCtoK);
        celsius = -cDegreesCtoK;
    } else if (celsius < atmo_ptr->cLowestTempC) {
        celsius = atmo_ptr->cLowestTempC;
        fprintf(stderr, "Warning: Reached minimum temperature limit. Adjusted to %.2f °C. Redefine 'cLowestTempF' constant to increase it.\n", celsius);
    }

    kelvin = celsius + cDegreesCtoK;

    // Pressure calculation using barometric formula
    pressure = atmo_ptr->_p0 * pow(
        1.0 + cLapseRateKperFoot * (altitude - atmo_ptr->_a0) / (atmo_ptr->_t0 + cDegreesCtoK),
        cPressureExponent);

    density_delta = ((atmo_ptr->_t0 + cDegreesCtoK) * pressure) / (atmo_ptr->_p0 * kelvin);

    *density_ratio_ptr = atmo_ptr->density_ratio * density_delta;

    // Mach 1 speed at altitude (fps)
    *mach_ptr = sqrt(kelvin) * cSpeedOfSoundMetric * mToFeet;

    // Optional debug print (uncomment if needed)
    // printf("Altitude: %.2f, Base Temp: %.2f°C, Current Temp: %.2f°C, Base Pressure: %.2f hPa, Current Pressure: %.2f hPa, Density ratio: %.6f\n",
    //        altitude, atmo_ptr->_t0, celsius, atmo_ptr->_p0, pressure, *density_ratio_ptr);
}

V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr) {
    return (V3dT){
        .x=wind_ptr->velocity * cos(wind_ptr->direction_from),
        .y=0.0,
        .z=wind_ptr->velocity * sin(wind_ptr->direction_from)
    };
}

void WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds) {

    ws->length = (int)length;
    ws->winds = winds;

    ws->current = 0;
    ws->next_range = cMaxWindDistanceFeet;

    ws->last_vector_cache.x = 0.0;
    ws->last_vector_cache.y = 0.0;
    ws->last_vector_cache.z = 0.0;

    WindSock_t_updateCache(ws);
}

void WindSock_t_free(WindSock_t *ws) {
    if (ws != NULL) {
        if (ws->winds != NULL) {
            free(ws->winds);
        }
        free(ws);
    }
}

V3dT WindSock_t_currentVector(WindSock_t *wind_sock) {
    if (wind_sock == NULL) {
        return (V3dT){0.0, 0.0, 0.0};
    }
    return wind_sock->last_vector_cache;
}

int WindSock_t_updateCache(WindSock_t *ws) {
    if (ws == NULL) {
        return -1;
    }

    if (ws->current < ws->length) {
        Wind_t cur_wind = ws->winds[ws->current];
        ws->last_vector_cache = Wind_t_to_V3dT(&cur_wind);
        ws->next_range = cur_wind.until_distance;
    } else {
        ws->last_vector_cache.x = 0.0;
        ws->last_vector_cache.y = 0.0;
        ws->last_vector_cache.z = 0.0;
        ws->next_range = cMaxWindDistanceFeet;
    }
    return 0;
}

V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param) {
    V3dT zero_vector = {0.0, 0.0, 0.0};

    if (ws == NULL) {
        return zero_vector;
    }

    if (next_range_param >= ws->next_range) {
        ws->current += 1;

        if (ws->current >= ws->length) {
            ws->last_vector_cache = zero_vector;
            ws->next_range = cMaxWindDistanceFeet;
        } else {
            // If cache update fails, return zero vector
            if (WindSock_t_updateCache(ws) < 0) {
                fprintf(stderr, "Warning: WindSock_t_updateCache failed. Returning zero vector.\n");
                return zero_vector;
            }
        }
    }

    return ws->last_vector_cache;
}


// helpers
double getCorrection(double distance, double offset) {
    if (distance != 0.0) {
        return atan2(offset, distance);
    }
    // fprintf(stderr, "Error: Division by zero in getCorrection.\n");
    return 0.0;
}

double calculateEnergy(double bulletWeight, double velocity) {
    return bulletWeight * velocity * velocity / 450400.0;
}

double calculateOgw(double bulletWeight, double velocity) {
    return bulletWeight * bulletWeight * velocity * velocity * velocity * 1.5e-12;
}

/**
 * @brief Calculate Coriolis acceleration in local coordinates
 * @param coriolis_ptr Pointer to Coriolis_t containing precomputed transformation data
 * @param velocity Pointer to ground velocity of projectile
 * @param accel_ptr Pointer to store acceleration in local coordinates
 */
void Coriolis_t_coriolis_acceleration_local(
    const Coriolis_t *coriolis_ptr,
    V3dT *velocity_ptr,
    V3dT *accel_ptr
) {
    // Return zero acceleration if not full 3D mode
    if (coriolis_ptr->flat_fire_only) {
        accel_ptr->x = 0.0;
        accel_ptr->y = 0.0;
        accel_ptr->z = 0.0;
        return;
    }

    // Transform velocity from local (range/up/cross) to ENU coordinates
    double vel_east = velocity_ptr->x * coriolis_ptr->range_east + velocity_ptr->z * coriolis_ptr->cross_east;
    double vel_north = velocity_ptr->x * coriolis_ptr->range_north + velocity_ptr->z * coriolis_ptr->cross_north;
    double vel_up = velocity_ptr->y;

    // Coriolis acceleration in ENU coordinates
    double factor = -2.0 * cEarthAngularVelocityRadS;
    double accel_east = factor * (coriolis_ptr->cos_lat * vel_up - coriolis_ptr->sin_lat * vel_north);
    double accel_north = factor * (coriolis_ptr->sin_lat * vel_east);
    double accel_up = factor * (-coriolis_ptr->cos_lat * vel_east);

    // Transform acceleration back to local coordinates
    double accel_range = accel_east * coriolis_ptr->range_east + accel_north * coriolis_ptr->range_north;
    double accel_cross = accel_east * coriolis_ptr->cross_east + accel_north * coriolis_ptr->cross_north;

    accel_ptr->x = accel_range;
    accel_ptr->y = accel_up;
    accel_ptr->z = accel_cross;
}
