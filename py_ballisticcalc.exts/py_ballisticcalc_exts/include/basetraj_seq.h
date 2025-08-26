#ifndef BASETRAJ_SEQ_H
#define BASETRAJ_SEQ_H

/**
 * Simple C struct for trajectory data points used in the contiguous buffer.
 */
typedef struct {
    double time;  /* Time of the data point */
    double px;    /* Position x-coordinate */
    double py;    /* Position y-coordinate */
    double pz;    /* Position z-coordinate */
    double vx;    /* Velocity x-component */
    double vy;    /* Velocity y-component */
    double vz;    /* Velocity z-component */
    double mach;  /* Mach number */
} BaseTrajC;

#endif /* BASETRAJ_SEQ_H */
