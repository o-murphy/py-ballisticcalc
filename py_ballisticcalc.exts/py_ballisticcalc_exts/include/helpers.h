#ifndef HELPERS_H
#define HELPERS_H

#include <math.h>

double getCorrection(double distance, double offset);
double calculateEnergy(double bulletWeight, double velocity);
double calculateOgw(double bulletWeight, double velocity);

#endif // HELPERS_H