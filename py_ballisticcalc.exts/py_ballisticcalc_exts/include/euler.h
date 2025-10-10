#ifndef EULER_H
#define EULER_H

/**
 * @brief Calculate time step based on current projectile speed.
 * * @param base_step The base time step value.
 * @param velocity The current projectile speed (magnitude of velocity).
 * @return double The calculated time step.
 */
double _euler_time_step(double base_step, double velocity);

#endif // EULER_H