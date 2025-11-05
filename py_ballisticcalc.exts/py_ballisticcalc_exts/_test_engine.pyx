# cython: freethreading_compatible=True
"""CythonEngineTestHarness (test-only Cython engine).

Provides direct C-layer accessors for parity tests without modifying production
engine modules. Not part of the public API.
"""
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.rk4_engine cimport CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeqT
from libc.math cimport sin, cos
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ShotProps_dragByMach,
    BCLIBC_ShotProps_spinDrift,
    BCLIBC_ShotProps_updateStabilityCoefficient,
    BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude,
    BCLIBC_calculateEnergy,
    BCLIBC_calculateOgw,
    BCLIBC_ErrorType,
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
        return BCLIBC_ShotProps_dragByMach(&self._engine.shot, mach)

    cpdef tuple density_and_mach(self, double altitude_ft):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        cdef double density_ratio = 0.0
        cdef double mach = 0.0
        BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
            &self._engine.shot.atmo,
            altitude_ft,
            &density_ratio,
            &mach
        )
        return density_ratio, mach

    cpdef double spin_drift(self, double time_s):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return BCLIBC_ShotProps_spinDrift(&self._engine.shot, time_s)

    cpdef double update_stability(self):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        if BCLIBC_ShotProps_updateStabilityCoefficient(&self._engine.shot) != BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            raise ZeroDivisionError("Zero division detected in BCLIBC_ShotProps_updateStabilityCoefficient")
        return self._engine.shot.stability_coefficient

    cpdef double energy(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return BCLIBC_calculateEnergy(self._engine.shot.weight, velocity_fps)

    cpdef double ogw(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return BCLIBC_calculateOgw(self._engine.shot.weight, velocity_fps)

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
        cdef BaseTrajSeqT seq = BaseTrajSeqT()
        cdef double v = self._engine.shot.muzzle_velocity
        cdef double be = self._engine.shot.barrel_elevation
        cdef double az = self._engine.shot.barrel_azimuth
        cdef double vx = v * cos(be) * cos(az)
        cdef double vy = v * sin(be)
        cdef double vz = v * cos(be) * sin(az)
        # initial point
        seq.append(
            0.0, 0.0,
            -self._engine.shot.cant_cosine * self._engine.shot.sight_height,
            -self._engine.shot.cant_sine * self._engine.shot.sight_height,
            vx, vy, vz, 1.0
        )
        # second point simple Euler step without drag / gravity for minimal path
        cdef double dt
        if time_step > 0:
            dt = time_step
        else:
            dt = 0.001
        seq.append(
            dt, vx * dt,
            -self._engine.shot.cant_cosine * self._engine.shot.sight_height + vy * dt,
            -self._engine.shot.cant_sine * self._engine.shot.sight_height + vz * dt,
            vx, vy, vz, 1.0
        )
        self.integration_step_count = <int>seq._length
        return (seq, None)
