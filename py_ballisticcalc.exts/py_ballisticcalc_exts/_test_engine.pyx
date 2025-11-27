# cython: freethreading_compatible=True
"""CythonEngineTestHarness (test-only Cython engine).

Provides direct C-layer accessors for parity tests without modifying production
engine modules. Not part of the public API.
"""
from cython cimport final
from libcpp.cmath cimport sin, cos
from py_ballisticcalc_exts.rk4_engine cimport CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.traj_data cimport CythonizedBaseTrajSeq, BCLIBC_BaseTrajData
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_calculateEnergy,
    BCLIBC_calculateOgw,
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
        return self._this.shot.drag_by_mach(mach)

    cpdef tuple density_and_mach(self, double altitude_ft):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        cdef double density_ratio = 0.0
        cdef double mach = 0.0
        self._this.shot.atmo.update_density_factor_and_mach_for_altitude(
            altitude_ft,
            density_ratio,
            mach
        )
        return density_ratio, mach

    cpdef double spin_drift(self, double time_s):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return self._this.shot.spin_drift(time_s)

    cpdef double update_stability(self):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        self._this.shot.update_stability_coefficient()
        return self._this.shot.stability_coefficient

    cpdef double energy(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return BCLIBC_calculateEnergy(self._this.shot.weight, velocity_fps)

    cpdef double ogw(self, double velocity_fps):
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        return BCLIBC_calculateOgw(self._this.shot.weight, velocity_fps)

    cpdef object integrate_minimal(self, double range_limit_ft, double range_step_ft, double time_step):
        """Very small dummy integration for test parity of step counting.

        Generates two trajectory points: t=0 and t=time_step advancing a trivial
        range using muzzle velocity components. Not physically exact; only used
        by tests that assert step_count()>0 and non-None sequence.
        """
        if not self._prepared:
            raise RuntimeError("prepare() must be called first")
        cdef CythonizedBaseTrajSeq seq = CythonizedBaseTrajSeq()
        cdef double v = self._this.shot.muzzle_velocity
        cdef double be = self._this.shot.barrel_elevation
        cdef double az = self._this.shot.barrel_azimuth
        cdef double vx = v * cos(be) * cos(az)
        cdef double vy = v * sin(be)
        cdef double vz = v * cos(be) * sin(az)
        # initial point
        seq._this.append(
            BCLIBC_BaseTrajData(
                0.0, 0.0,
                -self._this.shot.cant_cosine * self._this.shot.sight_height,
                -self._this.shot.cant_sine * self._this.shot.sight_height,
                vx, vy, vz, 1.0
            )
        )
        # second point simple Euler step without drag / gravity for minimal path
        cdef double dt
        if time_step > 0:
            dt = time_step
        else:
            dt = 0.001
        seq._this.append(
            BCLIBC_BaseTrajData(
                dt, vx * dt,
                -self._this.shot.cant_cosine * self._this.shot.sight_height + vy * dt,
                -self._this.shot.cant_sine * self._this.shot.sight_height + vz * dt,
                vx, vy, vz, 1.0
            )
        )
        self.integration_step_count = <int>seq._length
        return (seq, None)
