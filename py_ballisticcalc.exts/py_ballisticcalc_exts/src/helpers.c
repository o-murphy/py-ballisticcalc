#include <math.h>
#include <stdio.h> // Only needed if you were printing errors, but in this case, it's not.
#include "helpers.h"

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
    return pow(bulletWeight, 2) * pow(velocity, 3) * 1.5e-12;
}
