#include "bindings.h" // Include your own header first
#include "v3d.h"
#include <stdlib.h>   // For malloc, free
#include <stdio.h>    // For fprintf, stderr
#include <math.h>     // For pow, fabs, atan2, cos, sin, sqrt

// --- Global Constants Definitions ---
const double C_DEGREES_F_TO_R = 459.67;
const double C_DEGREES_C_TO_K = 273.15;
const double C_SPEED_OF_SOUND_IMPERIAL = 49.0223;
const double C_SPEED_OF_SOUND_METRIC = 20.0467;
const double C_LAPSE_RATE_K_PER_FOOT = -0.0019812;
const double C_LAPSE_RATE_IMPERIAL = -3.56616e-03;
const double C_PRESSURE_EXPONENT = 5.2559;
const double C_LOWEST_TEMP_F = -130.0;
const double M_TO_FEET = 3.28084;

// --- Function Implementations ---

double getCalcStepDefault(ConfigT * config) {
    return config->cMaxCalcStepSizeFeet / 2.0;
}

double getCalcStep(ConfigT * config, double step) {
    double preferred_step = config->cMaxCalcStepSizeFeet;
    if (step == 0.0) {
        return preferred_step / 2.0;
    }

    if (step < preferred_step) {
        return step / 2.0; // This might be a bug depending on desired behavior.
                           // If preferred_step is 100 and step is 10, this returns 5.
                           // Original Cython said:
                           // `if step < preferred_step: return step / 2.0`
                           // `else: return preferred_step / 2.0`
                           // This means if step is larger than preferred_step, it uses preferred_step / 2.
                           // If step is smaller, it halves the step.
                           // So the implementation is correct based on original Cython.
    } else {
        return preferred_step / 2.0;
    }
}

MachListT tableToMach(DragTableT * table) {
    MachListT machList;
    machList.length = table->length;

    machList.array = (double *) malloc(machList.length * sizeof(double));
    if (machList.array == NULL) {
        fprintf(stderr, "Error: Unable to allocate memory for MachListT array in tableToMach.\n");
        machList.length = 0;
        return machList;
    }

    for (size_t i = 0; i < machList.length; i++) {
        machList.array[i] = table->points[i].Mach;
    }

    return machList;
}

CurveT calculateCurve(DragTableT * table) {
    CurveT curve;
    CurvePointT * curve_points;
    size_t i;
    size_t len_data_points = table->length;
    size_t len_data_range;

    if (len_data_points < 2) {
        fprintf(stderr, "Error: calculateCurve requires at least 2 data points (received %zu).\n", len_data_points);
        curve.points = NULL;
        curve.length = 0;
        return curve;
    }

    len_data_range = len_data_points - 1;

    curve_points = (CurvePointT *) malloc(len_data_points * sizeof(CurvePointT));
    if (curve_points == NULL) {
        fprintf(stderr, "Error: Unable to allocate memory for curve points in calculateCurve.\n");
        curve.points = NULL;
        curve.length = 0;
        return curve;
    }

    // First point calculation (linear approximation)
    if (len_data_points >= 2) {
        double x1 = table->points[0].Mach;
        double x2 = table->points[1].Mach;
        double y1 = table->points[0].CD;
        double y2 = table->points[1].CD;

        // Ensure no division by zero for rate calculation
        if ((x2 - x1) == 0.0) {
            fprintf(stderr, "Error: Divide by zero in rate calculation for first point in calculateCurve.\n");
            free(curve_points);
            curve.points = NULL;
            curve.length = 0;
            return curve;
        }
        double rate = (y2 - y1) / (x2 - x1);
        curve_points[0].a = 0.0;
        curve_points[0].b = rate;
        curve_points[0].c = y1 - x1 * rate;
    }
    // If only one point (though already checked len_data_points < 2)
    else {
        curve_points[0].a = 0.0;
        curve_points[0].b = 0.0;
        curve_points[0].c = table->points[0].CD;
    }


    // Loop for intermediate points (parabolic interpolation)
    for (i = 1; i < len_data_range; i++) {
        double x1 = table->points[i - 1].Mach;
        double x2 = table->points[i].Mach;
        double x3 = table->points[i + 1].Mach;
        double y1 = table->points[i - 1].CD;
        double y2 = table->points[i].CD;
        double y3 = table->points[i + 1].CD;

        double denominator = (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1);

        if (denominator == 0.0) {
            fprintf(stderr, "Error: Degenerate Mach points encountered in calculateCurve at index %zu (denominator is zero).\n", i);
            free(curve_points);
            curve.points = NULL;
            curve.length = 0;
            return curve;
        }

        // Additional check for (x2 - x1) == 0.0 for 'b' calculation
        if ((x2 - x1) == 0.0) {
            fprintf(stderr, "Error: Divide by zero in 'b' calculation at index %zu in calculateCurve.\n", i);
            free(curve_points);
            curve.points = NULL;
            curve.length = 0;
            return curve;
        }

        curve_points[i].a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / denominator;
        curve_points[i].b = (y2 - y1 - curve_points[i].a * (x2 * x2 - x1 * x1)) / (x2 - x1);
        curve_points[i].c = y1 - (curve_points[i].a * x1 * x1 + curve_points[i].b * x1);
    }

    // Last point calculation (linear approximation)
    if (len_data_points >= 2) {
        size_t last_idx = len_data_points - 1;
        double x_prev = table->points[last_idx - 1].Mach;
        double x_last = table->points[last_idx].Mach;
        double y_prev = table->points[last_idx - 1].CD;
        double y_last = table->points[last_idx].CD;

        // Ensure no division by zero for rate calculation
        if ((x_last - x_prev) == 0.0) {
            fprintf(stderr, "Error: Divide by zero in rate calculation for last point in calculateCurve.\n");
            free(curve_points);
            curve.points = NULL;
            curve.length = 0;
            return curve;
        }
        double rate = (y_last - y_prev) / (x_last - x_prev);
        curve_points[last_idx].a = 0.0;
        curve_points[last_idx].b = rate;
        curve_points[last_idx].c = y_last - x_last * rate;
    }

    curve.length = len_data_points;
    curve.points = curve_points;

    return curve;
}

double calculateByCurveAndMachList(MachListT * machList, CurveT * curve, double mach) {
    size_t num_points;
    size_t mlo, mhi, mid;
    size_t m;
    CurvePointT curve_m;

    if (machList == NULL || machList->array == NULL || machList->length == 0) {
        fprintf(stderr, "Error: MachList is invalid or empty in calculateByCurveAndMachList.\n");
        return 0.0;
    }
    if (curve == NULL || curve->points == NULL || curve->length == 0) {
        fprintf(stderr, "Error: Curve is invalid or empty in calculateByCurveAndMachList.\n");
        return 0.0;
    }

    num_points = curve->length;

    if (machList->length != num_points) {
        fprintf(stderr, "Error: MachList and Curve lengths do not match in calculateByCurveAndMachList.\n");
        return 0.0;
    }

    if (mach <= machList->array[0]) {
        m = 0;
    } else if (mach >= machList->array[num_points - 1]) {
        m = num_points - 1;
    } else {
        mlo = 0;
        mhi = num_points - 1;

        while (mhi - mlo > 1) {
            mid = mlo + (mhi - mlo) / 2;
            if (mid >= num_points) { // Added bound check for mid
                fprintf(stderr, "Error: Mid index out of bounds in binary search.\n");
                return 0.0;
            }
            if (machList->array[mid] < mach) {
                mlo = mid;
            } else {
                mhi = mid;
            }
        }

        if (fabs(machList->array[mhi] - mach) > fabs(mach - machList->array[mlo])) {
            m = mlo;
        } else {
            m = mhi;
        }
    }

    if (m >= curve->length) { // Check if 'm' is a valid index for curve->points
        fprintf(stderr, "Error: Calculated index 'm' (%zu) out of bounds for curve points (length %zu).\n", m, curve->length);
        return 0.0;
    }
    curve_m = curve->points[m];
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach);
}

double dragByMach(ShotDataT * t, double mach) {
    if (t == NULL || t->bc == 0.0) {
        fprintf(stderr, "Error: ShotDataT is NULL or bc is zero in dragByMach.\n");
        return 0.0;
    }

    double cd = calculateByCurveAndMachList(&t->machList, &t->curve, mach);

    return cd * 2.08551e-04 / t->bc;
}

double spinDrift(ShotDataT * t, double time) {
    double sign;

    if (t == NULL) {
        fprintf(stderr, "Error: ShotDataT is NULL in spinDrift.\n");
        return 0.0;
    }

    if (t->twist != 0.0 && t->stabilityCoefficient != 0.0) {
        sign = (t->twist > 0.0) ? 1.0 : -1.0;
        return sign * (1.25 * (t->stabilityCoefficient + 1.2) * pow(time, 1.83)) / 12.0;
    }
    return 0.0;
}

void updateStabilityCoefficient(ShotDataT * t) {
    double twist_rate, length_ratio, sd, fv, ft_celsius, ft_fahrenheit, pt_hpa, pt_inhg, ftp;

    if (t == NULL) {
        fprintf(stderr, "Error: ShotDataT is NULL in updateStabilityCoefficient.\n");
        return;
    }

    if (t->twist != 0.0 && t->length != 0.0 && t->diameter != 0.0 && t->atmo._p0 != 0.0) {
        twist_rate = fabs(t->twist) / t->diameter;
        length_ratio = t->length / t->diameter;

        if (t->diameter == 0.0 || length_ratio == 0.0) { // Check t->diameter for twist_rate as well
            t->stabilityCoefficient = 0.0;
            return;
        }

        double sd_denominator = (twist_rate * twist_rate) * (t->diameter * t->diameter * t->diameter) * length_ratio * (1.0 + (length_ratio * length_ratio));
        if (sd_denominator == 0.0) {
            fprintf(stderr, "Error: Denominator for SD calculation is zero in updateStabilityCoefficient.\n");
            t->stabilityCoefficient = 0.0;
            return;
        }
        sd = 30.0 * t->weight / sd_denominator;

        // Ensure 2800.0 is not zero
        if (2800.0 == 0.0) { // This is a constant, so this check is mostly for conceptual completeness.
            fprintf(stderr, "Error: Division by zero in fv calculation (2800.0).\n");
            t->stabilityCoefficient = 0.0;
            return;
        }
        fv = pow(t->muzzleVelocity / 2800.0, 1.0 / 3.0);

        ft_celsius = t->atmo._t0;
        ft_fahrenheit = (ft_celsius * 9.0 / 5.0) + 32.0;

        pt_hpa = t->atmo._p0;
        if (33.8639 == 0.0) { // This is a constant, won't be zero.
             fprintf(stderr, "Error: Division by zero for hPa to inHg conversion.\n");
             t->stabilityCoefficient = 0.0;
             return;
        }
        pt_inhg = pt_hpa / 33.8639;

        if ( (59.0 + 460.0) == 0.0 || pt_inhg == 0.0) {
            fprintf(stderr, "Error: Division by zero in FTP calculation.\n");
            t->stabilityCoefficient = 0.0;
            return;
        }
        ftp = ((ft_fahrenheit + 460.0) / (59.0 + 460.0)) * (29.92 / pt_inhg);

        t->stabilityCoefficient = sd * fv * ftp;
    } else {
        t->stabilityCoefficient = 0.0;
    }
}

void freeCurve(CurveT *curve) {
    if (curve == NULL) {
        fprintf(stderr, "Warning: Attempted to free a NULL CurveT pointer.\n");
        return;
    }
    if (curve->points != NULL) {
        free(curve->points);
        curve->points = NULL;
    }
}

void freeMachList(MachListT *machList) {
    if (machList == NULL) {
        fprintf(stderr, "Warning: Attempted to free a NULL MachListT pointer.\n");
        return;
    }
    if (machList->array != NULL) {
        free(machList->array);
        machList->array = NULL;
    }
}

void freeDragTable(DragTableT *table) {
    if (table == NULL) {
        fprintf(stderr, "Warning: Attempted to free a NULL DragTable pointer.\n");
        return;
    }
    if (table->points != NULL) {
        free(table->points);
        table->points = NULL;
    }
}

void freeTrajectory(ShotDataT *t) {
    if (t == NULL) {
        fprintf(stderr, "Warning: Attempted to free a NULL ShotDataT pointer.\n");
        return;
    }
    freeCurve(&t->curve);
    freeMachList(&t->machList);
    // If DragTable was part of ShotDataT, it would be freed here as well
}

double getCorrection(double distance, double offset) {
    if (distance != 0.0) {
        return atan2(offset, distance);
    }
    return 0.0;
}

double calculateEnergy(double bulletWeight, double velocity) {
    // Ensure 450400.0 is not zero
    if (450400.0 == 0.0) { // This is a constant, won't be zero.
        fprintf(stderr, "Error: Division by zero in energy calculation.\n");
        return 0.0;
    }
    return bulletWeight * (velocity * velocity) / 450400.0;
}

double calculateOGW(double bulletWeight, double velocity) {
    return (bulletWeight * bulletWeight) * (velocity * velocity * velocity) * 1.5e-12;
}

void updateDensityFactorAndMatchForAltitude(
    AtmosphereT * atmo, double altitude, double * densityRatio, double * mach)
{
    double celsius, kelvin, pressure, density_delta;

    if (atmo == NULL || densityRatio == NULL || mach == NULL) {
        fprintf(stderr, "Error: NULL pointer passed to updateDensityFactorAndMatchForAltitude.\n");
        if (densityRatio != NULL) *densityRatio = 0.0;
        if (mach != NULL) *mach = 0.0;
        return;
    }

    if (fabs(atmo->_a0 - altitude) < 30.0) {
        *densityRatio = atmo->densityFactor;
        *mach = atmo->_mach;
    } else {
        celsius = (altitude - atmo->_a0) * C_LAPSE_RATE_K_PER_FOOT + atmo->_t0;

        if (altitude > 36089.0) {
            fprintf(stderr, "Warning: Density request for altitude above troposphere (%.2f ft)."
                            " Atmospheric model not valid here.\n", altitude);
        }

        if (celsius < -C_DEGREES_C_TO_K) {
            fprintf(stderr, "Warning: Invalid temperature: %.2f°C. Adjusted to absolute zero (-%.2f°C)."
                            " It must be >= %.2f to avoid a domain error.\n",
                            celsius, C_DEGREES_C_TO_K, -C_DEGREES_F_TO_R);
            celsius = -C_DEGREES_C_TO_K;
        }
        else if (celsius < atmo->cLowestTempC) {
            celsius = atmo->cLowestTempC;
            fprintf(stderr, "Warning: Reached minimum temperature limit. Adjusted to %.2f°C."
                            " Redefine 'cLowestTempC' constant to increase it.\n", celsius);
        }

        kelvin = celsius + C_DEGREES_C_TO_K;
        if (kelvin <= 0.0) {
            fprintf(stderr, "Error: Kelvin temperature is non-positive (%.2f K) in updateDensityFactorAndMatchForAltitude.\n", kelvin);
            *densityRatio = 0.0;
            *mach = 0.0;
            return;
        }

        double pressure_denominator = (atmo->_t0 + C_DEGREES_C_TO_K);
        if (pressure_denominator == 0.0) {
            fprintf(stderr, "Error: Division by zero in pressure calculation (atmo->_t0 + C_DEGREES_C_TO_K is zero).\n");
            *densityRatio = 0.0;
            *mach = 0.0;
            return;
        }
        double pressure_base = 1.0 + C_LAPSE_RATE_K_PER_FOOT * (altitude - atmo->_a0) / pressure_denominator;

        if (pressure_base <= 0.0) { // pow function needs positive base if exponent is not an integer
            fprintf(stderr, "Error: Non-positive base for pressure calculation in updateDensityFactorAndMatchForAltitude. Base: %.2f\n", pressure_base);
            *densityRatio = 0.0;
            *mach = 0.0;
            return;
        }
        pressure = atmo->_p0 * pow(pressure_base, C_PRESSURE_EXPONENT);

        if (atmo->_p0 == 0.0 || kelvin == 0.0) {
             fprintf(stderr, "Error: Zero reference pressure or Kelvin in density_delta calculation.\n");
             *densityRatio = 0.0;
             *mach = 0.0;
             return;
        }
        density_delta = ((atmo->_t0 + C_DEGREES_C_TO_K) * pressure) / (atmo->_p0 * kelvin);

        *densityRatio = atmo->densityFactor * density_delta;
        *mach = sqrt(kelvin) * C_SPEED_OF_SOUND_METRIC * M_TO_FEET;
    }
}

V3d windToVector(const WindT *w) { // Added const as input 'w' isn't modified
    V3d result;

    if (w == NULL) {
        fprintf(stderr, "Error: NULL WindT pointer passed to windToVector.\n");
        result.x = 0.0;
        result.y = 0.0;
        result.z = 0.0;
        return result;
    }

    double range_component = w->velocity * cos(w->directionFrom);
    double cross_component = w->velocity * sin(w->directionFrom);

    result.x = range_component;
    result.y = 0.0; // Wind often acts horizontally, so Y (vertical) component is zero
    result.z = cross_component;

    return result;
}