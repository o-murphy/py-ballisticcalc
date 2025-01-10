# Declare constants
cdef double cDegreesFtoR
cdef double cSpeedOfSoundImperial
cdef double cLapseRateImperial

# Declare class
cdef class _EarlyBindAtmo:
    cdef:
        double _t0
        double _a0
        double _mach1
        double density_ratio

    cdef void get_density_factor_and_mach_for_altitude(
            _EarlyBindAtmo self, double altitude, double * density_ratio, double * mach
    )
