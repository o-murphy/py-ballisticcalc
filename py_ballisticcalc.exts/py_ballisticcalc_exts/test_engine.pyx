"""CythonEngineTestHarness (test-only Cython engine).

Provides direct C-layer accessors for parity tests without modifying production
engine modules. Not part of the public API.
"""
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,  # retained for type reference
    calculateEnergy,
    calculateOgw,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.rk4_engine cimport CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport CBaseTrajSeq
from libc.math cimport sin, cos
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    ShotProps_t,
    ShotProps_t_dragByMach,
    ShotProps_t_spinDrift,
    ShotProps_t_updateStabilityCoefficient,
    Atmosphere_t_updateDensityFactorAndMachForAltitude,
)

__all__ = ["CythonEngineTestHarness"]


@final
cdef class CythonEngineTestHarness(CythonizedRK4IntegrationEngine):
    cdef bint _prepared

    def __cinit__(self, object config):
        self._prepared = <bint>0

    cpdef void prepare(self, object shot):
        self._init_trajectory(shot)
        self._prepared = <bint>1

    cpdef double drag(self, double mach):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return ShotProps_t_dragByMach(&self._shot_s, mach)

    cpdef tuple density_and_mach(self, double altitude_ft):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        cdef double density_ratio = <double>0.0
        cdef double mach = <double>0.0
        Atmosphere_t_updateDensityFactorAndMachForAltitude(&self._shot_s.atmo, altitude_ft, &density_ratio, &mach)
        return density_ratio, mach

    cpdef double spin_drift(self, double time_s):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return ShotProps_t_spinDrift(&self._shot_s, time_s)

    cpdef double update_stability(self):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        ShotProps_t_updateStabilityCoefficient(&self._shot_s)
        return self._shot_s.stability_coefficient

    cpdef double energy(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return calculateEnergy(self._shot_s.weight, velocity_fps)

    cpdef double ogw(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return calculateOgw(self._shot_s.weight, velocity_fps)

    cpdef int step_count(self):
        return self.integration_step_count

    cpdef object integrate_minimal(self, double range_limit_ft, double range_step_ft, double time_step):
        """Very small dummy integration for test parity of step counting.

        Generates two trajectory points: t=0 and t=time_step advancing a trivial
        range using muzzle velocity components. Not physically exact; only used
        by tests that assert step_count()>0 and non-None sequence.
        """
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        cdef CBaseTrajSeq seq = CBaseTrajSeq()
        cdef double v = self._shot_s.muzzle_velocity
        cdef double be = self._shot_s.barrel_elevation
        cdef double az = self._shot_s.barrel_azimuth
        cdef double vx = v * cos(be) * cos(az)
        cdef double vy = v * sin(be)
        cdef double vz = v * cos(be) * sin(az)
        # initial point
        seq._append_c(<double>0.0, <double>0.0,
              -self._shot_s.cant_cosine * self._shot_s.sight_height,
              -self._shot_s.cant_sine * self._shot_s.sight_height,
              vx, vy, vz, <double>1.0)
        # second point simple Euler step without drag / gravity for minimal path
        cdef double dt
        if time_step > 0:
            dt = time_step
        else:
            dt = <double>0.001
        seq._append_c(dt, vx * dt,
              -self._shot_s.cant_cosine * self._shot_s.sight_height + vy * dt,
              -self._shot_s.cant_sine * self._shot_s.sight_height + vz * dt,
              vx, vy, vz, <double>1.0)
        self.integration_step_count = <int>seq._length
        return (seq, None)
