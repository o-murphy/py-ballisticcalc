# cython: freethreading_compatible=True
"""
Cythonized RK4 Integration Engine

Because storing each step in a BaseTrajSeqT is practically costless, we always run with "dense_output=True".
"""
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport ShotProps_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeqT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    TerminationReason,
    NoRangeError,
    RangeErrorInvalidParameter,
    RangeErrorMinimumVelocityReached,
    RangeErrorMaximumDropReached,
    RangeErrorMinimumAltitudeReached,
)

from py_ballisticcalc.exceptions import RangeError

__all__ = [
    'CythonizedRK4IntegrationEngine',
]

@final
cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""
    DEFAULT_TIME_STEP = 0.0025

    cdef double get_calc_step(CythonizedRK4IntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_TIME_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)

    cdef tuple _integrate(CythonizedRK4IntegrationEngine self, const ShotProps_t *shot_props_ptr,
                           double range_limit_ft, double range_step_ft,
                           double time_step, int filter_flags):
        cdef BaseTrajSeqT traj_seq = BaseTrajSeqT()
        cdef TerminationReason termination_reason = _integrate_rk4(
            shot_props_ptr,
            &self._wind_sock,
            &self._config_s,
            range_limit_ft, 
            range_step_ft, 
            time_step, 
            filter_flags,
            traj_seq._c_view,
        )
        cdef str termination_reason_str = None
        if termination_reason == RangeErrorInvalidParameter:
            raise RuntimeError("InvalidParameter")
        if termination_reason == RangeErrorMinimumVelocityReached:
            termination_reason_str = RangeError.MinimumVelocityReached
        if termination_reason == RangeErrorMaximumDropReached:
            termination_reason_str = RangeError.MaximumDropReached
        if termination_reason == RangeErrorMinimumAltitudeReached:
            termination_reason_str = RangeError.MinimumAltitudeReached
        return traj_seq, termination_reason_str
