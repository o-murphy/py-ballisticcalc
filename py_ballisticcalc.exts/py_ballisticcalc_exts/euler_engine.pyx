"""
Cythonized Euler Integration Engine

Because storing each step in a CBaseTrajSeq is practically costless, we always run with "dense_output=True".
"""
from cython cimport final
from libc.math cimport fabs, sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    ShotProps_t,
    Config_t,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    WindSock_t,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport CBaseTrajSeq, CBaseTrajSeq_t

from py_ballisticcalc.exceptions import RangeError

__all__ = [
    'CythonizedEulerIntegrationEngine',
]

cdef extern from "include/bclib.h":
    ctypedef enum TerminationReason:
        NoRangeError
        RangeErrorInvalidParameter
        RangeErrorMinimumVelocityReached
        RangeErrorMaximumDropReached
        RangeErrorMinimumAltitudeReached

cdef extern from "include/euler.h":
    double _euler_time_step(double base_step, double velocity) noexcept nogil

    TerminationReason _integrate_euler(ShotProps_t *shot_props_ptr,
                                    WindSock_t *wind_sock_ptr,
                                    const Config_t *config_ptr,
                                    double range_limit_ft, double range_step_ft,
                                    double time_step, int filter_flags,
                                    CBaseTrajSeq_t *traj_seq_ptr) noexcept nogil


@final
cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""
    DEFAULT_STEP = 0.5  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    cdef double get_calc_step(CythonizedEulerIntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)

    cdef tuple _integrate(CythonizedEulerIntegrationEngine self, ShotProps_t *shot_props_ptr,
                           double range_limit_ft, double range_step_ft,
                           double time_step, int filter_flags):
        cdef CBaseTrajSeq traj_seq = CBaseTrajSeq()
        cdef TerminationReason termination_reason = _integrate_euler(
            shot_props_ptr,
            self._wind_sock,
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
