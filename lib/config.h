#ifndef CONFIG_H
#define CONFIG_H

typedef struct
{
    double cMaxCalcStepSizeFeet;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} ConfigT;

#endif // CONFIG_H