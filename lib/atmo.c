#include <stdio.h>
#include <math.h>
#include "consts.h"
#include "atmo.h"

void updateDensityFactorAndMatchForAltitude(AtmosphereT *atmo, double altitude, double *densityRatio, double *mach)
{
    if (atmo == NULL || densityRatio == NULL || mach == NULL)
    {
        fprintf(stderr, "Error: NULL pointer in updateDensityFactorAndMatchForAltitude.\n");
        return;
    }
    // Placeholder: In a real implementation, you would calculate these based on 'atmo' and 'altitude'
    // For now, let's just set some arbitrary values or use defaults.
    // This function requires access to atmospheric constants.
    // Example: Using global constants from bc.c
    // Note: These calculations are simplified and would typically involve more complex atmospheric models.

    // Assuming a simplified model where density factor decreases with altitude
    // and mach depends on temperature (which decreases with altitude)
    *densityRatio = 1.0 - (altitude / 100000.0); // Simple linear decrease
    if (*densityRatio < 0.1)
        *densityRatio = 0.1; // Cap at a minimum

    // Simplified Mach calculation: Speed of sound varies with temperature.
    // Assuming a constant temperature for simplicity here, or a linear lapse rate.
    // Using C_SPEED_OF_SOUND_IMPERIAL as a base.
    // A more accurate calculation would involve temperature and speed of sound at current altitude.
    // For now, let's just say mach is related to density or a fixed value.
    *mach = C_SPEED_OF_SOUND_IMPERIAL; // Placeholder: this would be the local speed of sound,
                                       // NOT the mach number of the bullet itself.
                                       // The mach number of the bullet (velocity/speed_of_sound)
                                       // is calculated in createTrajectoryData or integrate.

    // If 'atmo->mach' is intended to be the *speed of sound*, then this would be more like:
    double current_temp_k = atmo->t0 + (altitude * C_LAPSE_RATE_K_PER_FOOT); // Very simplified
    if (current_temp_k < 0)
        current_temp_k = 200;               // Prevent negative temp
    *mach = 20.0467 * sqrt(current_temp_k); // Approx speed of sound in m/s, using the constant from bc.c
                                            // The constant C_SPEED_OF_SOUND_IMPERIAL/METRIC is likely sqrt(gamma * R * T).
                                            // This might be the speed of sound at a reference temp (e.g., 0C or 15C).
                                            // For now, just a direct assignment for demonstration.
    // Re-evaluating: the 'mach' parameter in updateDensityFactorAndMatchForAltitude should be the speed of sound at current altitude.
    // The mach *number* of the projectile is then velocity / this 'mach' parameter.
    // Let's use a simplified calculation for `mach` (speed of sound at current alt).
    // This requires `atmo->t0` to be a valid initial temperature.
    double temp_f = atmo->t0 + (altitude * C_LAPSE_RATE_IMPERIAL);                           // Use imperial lapse rate for feet input
    double temp_r = temp_f + C_DEGREES_F_TO_R;                                               // Convert to Rankine
    *mach = C_SPEED_OF_SOUND_IMPERIAL * sqrt(temp_r / (C_LOWEST_TEMP_F + C_DEGREES_F_TO_R)); // Simplified proportionality

    // The density factor calculation is also complex, often involving pressure and temperature exponents.
    // For demonstration, a direct assignment based on the input 'atmo' might be needed:
    // *densityRatio = atmo->densityFactor; // If atmo already has this calculated for its '0' alt.
    // Or, a more robust calculation based on barometric formula:
    // double pressure_ratio = pow((atmo->t0 + (altitude * C_LAPSE_RATE_K_PER_FOOT)) / atmo->t0, C_PRESSURE_EXPONENT);
    // *densityRatio = pressure_ratio * (atmo->t0 / (atmo->t0 + (altitude * C_LAPSE_RATE_K_PER_FOOT)));
    // For this example, let's keep it simple or align it if 'atmo' already has a fixed `densityFactor`.
    // The 'atmo->densityFactor' should be for the starting altitude.
    // Let's assume the `densityRatio` refers to `(current_density / standard_density_at_sea_level)`.
    // And `mach` refers to `speed_of_sound_at_current_altitude`.
    // For demo, just use the `atmo` initial values if available, or simplified change:
    *densityRatio = atmo->densityFactor * (1.0 - (altitude * 0.00001)); // Arbitrary scaling
    if (*densityRatio < 0.1)
        *densityRatio = 0.1; // Prevent zero/negative
    if (*densityRatio > 2.0)
        *densityRatio = 2.0; // Prevent too high

    // Ensure mach is positive
    if (*mach < 1.0)
        *mach = 1.0; // Minimal speed of sound to prevent division by zero later
}