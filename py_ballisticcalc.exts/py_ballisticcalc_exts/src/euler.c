#include <math.h>
#include "euler.h"

/**
 * @brief Calculate time step based on current projectile speed.
 * * @param base_step The base time step value.
 * @param velocity The current projectile speed (magnitude of velocity).
 * @return double The calculated time step.
 */
double _euler_time_step(double base_step, double velocity)
{
    // C equivalent of fmax(1.0, velocity)
    // fmax is defined in <math.h>
    double divisor = fmax(1.0, velocity);
    
    return base_step / divisor;
}
