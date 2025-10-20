# cython: freethreading_compatible=True
"""
Cythonized Euler Integration Engine

Because storing each step in a BaseTrajSeqT is practically costless, we always run with "dense_output=True".
"""
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeqT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport TerminationReason, TrajFlag_t, ShotProps_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc.exceptions import RangeError

__all__ = [
    'CythonizedEulerIntegrationEngine',
]


@final
cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""
    DEFAULT_STEP = 0.5  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    cdef double get_calc_step(CythonizedEulerIntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)

    cdef tuple _integrate(CythonizedEulerIntegrationEngine self, const ShotProps_t *shot_props_ptr,
                          double range_limit_ft, double range_step_ft,
                          double time_step, TrajFlag_t filter_flags):
        cdef BaseTrajSeqT traj_seq = BaseTrajSeqT()
        cdef TerminationReason termination_reason = _integrate_euler(
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
        if termination_reason == TerminationReason.RangeErrorInvalidParameter:
            raise RuntimeError("InvalidParameter")
        if termination_reason == TerminationReason.RangeErrorMinimumVelocityReached:
            termination_reason_str = RangeError.MinimumVelocityReached
        if termination_reason == TerminationReason.RangeErrorMaximumDropReached:
            termination_reason_str = RangeError.MaximumDropReached
        if termination_reason == TerminationReason.RangeErrorMinimumAltitudeReached:
            termination_reason_str = RangeError.MinimumAltitudeReached
        return traj_seq, termination_reason_str
