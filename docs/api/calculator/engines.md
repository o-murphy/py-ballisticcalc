::: py_ballisticcalc.engines.base_engine.BaseIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.base_engine.BaseEngineConfigDict

`cythonized_dopri_engine` selects
`CythonizedDormandPrinceIntegrationEngine` when the optional compiled package
is installed. `relative_tolerance` and `absolute_tolerance` default to `1e-6`;
`get_step_stats()` returns accepted and rejected steps. Its controller follows
SciPy RK45 semantics, unlike compatibility-preserving Cash--Karp.

::: py_ballisticcalc.engines.RK4IntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.EulerIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.VelocityVerletIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.SciPyIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.scipy_engine.SciPyEngineConfigDict

::: py_ballisticcalc_exts.CythonizedBaseIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc_exts.CythonizedRK4IntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc_exts.CythonizedEulerIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc_exts.CythonizedVelocityVerletIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc_exts.CythonizedCashKarpIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc_exts.CythonizedDormandPrinceIntegrationEngine
    options:
        group_by_category: false
        members:
