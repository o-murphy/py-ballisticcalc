#ifndef ATMO_H
#define ATMO_H

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