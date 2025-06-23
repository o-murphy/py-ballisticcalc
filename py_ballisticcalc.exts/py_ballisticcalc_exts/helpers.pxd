cdef extern from "include/helpers.h" nogil:
    double getCorrection(double distance, double offset)
    double calculateEnergy(double bulletWeight, double velocity)
    double calculateOgw(double bulletWeight, double velocity)