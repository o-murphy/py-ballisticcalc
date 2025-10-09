# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, WindSock_t
from py_ballisticcalc_exts.cy_bindings cimport (
    ShotProps_t,
    Config_t,
)

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK4IntegrationEngine self)
    cdef tuple _integrate(CythonizedRK4IntegrationEngine self, ShotProps_t *shot_props_ptr,
                          double range_limit_ft, double range_step_ft,
                          double time_step, int filter_flags)
    
cdef tuple _integrate_rk4(ShotProps_t *shot_props_ptr,
                        WindSock_t *wind_sock_ptr,
                        const Config_t *config_ptr,
                        double range_limit_ft, double range_step_ft,
                        double time_step, int filter_flags)
