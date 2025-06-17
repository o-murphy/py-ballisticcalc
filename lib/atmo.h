#ifndef ATMO_H
#define ATMO_H

extern const double C_DEGREES_F_TO_R;
extern const double C_DEGREES_C_TO_K;
extern const double C_SPEED_OF_SOUND_IMPERIAL;
extern const double C_SPEED_OF_SOUND_METRIC;
extern const double C_LAPSE_RATE_K_PER_FOOT;
extern const double C_LAPSE_RATE_IMPERIAL;
extern const double C_PRESSURE_EXPONENT;
extern const double M_TO_FEET;
extern const double C_LOWEST_TEMP_F;

typedef struct
{
    double t0;
    double a0;
    double p0;
    double mach;
    double densityFactor; // Renamed from density_ratio to match C convention and usage
    double cLowestTempC;
} AtmosphereT;

void updateDensityFactorAndMatchForAltitude(AtmosphereT *atmo, double altitude, double *densityRatio, double *mach);

#endif // ATMO_H