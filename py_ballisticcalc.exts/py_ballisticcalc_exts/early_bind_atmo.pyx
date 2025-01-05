from libc.math cimport fabs, exp, sqrt
from cython cimport final

cdef double cDegreesFtoR = 459.67
cdef double cSpeedOfSoundImperial = 49.0223
cdef double cLapseRateImperial = -3.56616e-03

@final
cdef class _EarlyBindAtmo:

    def __cinit__(_EarlyBindAtmo self, object atmo):
        self._t0 = atmo._t0
        self._a0 = atmo._a0
        self._mach1 = atmo._mach1
        self.density_ratio = atmo.density_ratio

    # Function to calculate density factor and Mach at altitude
    cdef void get_density_factor_and_mach_for_altitude(
            _EarlyBindAtmo self, double altitude, double* density_ratio, double* mach
    ) nogil:
        """
        :param altitude: ASL in units of feet
        :return: density ratio and Mach 1 (fps) for the specified altitude
        """
        if fabs(self._a0 - altitude) < 30:
            density_ratio[0] = self.density_ratio
            mach[0] = self._mach1
        else:
            density_ratio[0] = exp(-altitude / 34112.0)
            t = (altitude - self._a0) * cLapseRateImperial + self._t0
            mach[0] = sqrt(t + cDegreesFtoR) * cSpeedOfSoundImperial