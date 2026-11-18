::: py_ballisticcalc.engines.base_engine.BaseIntegrationEngine
    options:
        group_by_category: false
        members:

::: py_ballisticcalc.engines.base_engine.BaseEngineConfigDict

`cython+dopri` selects
`CythonizedDormandPrinceIntegrationEngine` when the optional compiled package
is installed (`ctypes+dopri` selects `NativeDormandPrinceIntegrationEngine` of the ctypes package, the same engine through ctypes). `relative_tolerance` and `absolute_tolerance` default to `1e-6`;
`get_step_stats()` returns accepted and rejected steps. Its controller follows
SciPy RK45 semantics, unlike compatibility-preserving Cash--Karp.

`cython+tsitouras` selects `CythonizedTsitourasIntegrationEngine` the
same way. It is structurally identical to `CythonizedDormandPrinceIntegrationEngine`
(same 7-stage FSAL shape, same SciPy-RK45-style controller, same `relative_tolerance`/
`absolute_tolerance` config) but uses the Tsitouras 5(4) tableau instead of
Dormand-Prince's — measured to be in the same performance class as Dormand-Prince and
Cash--Karp, not consistently faster, despite its smaller leading truncation-error
coefficient; see [benchmarks](../../concepts/benchmarks.md#dormand-prince-and-tsitouras-engines).

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

::: py_ballisticcalc.engines.scipy_engine.SciPyIntegrationEngineFactory

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

::: py_ballisticcalc_exts.CythonizedTsitourasIntegrationEngine
    options:
        group_by_category: false
        members:

The same engines through ctypes, from the `py_ballisticcalc.ctypes` package (`pip install "py-ballisticcalc[ctypes]"`), are registered under the
names `ctypes+rk4`, ... (the Cython ones are `cython+rk4`, ...). The methods are those of the base engine, run by the native `bclibc_ffi` library.

::: py_ballisticcalc_ctypes._native.NativeEulerIntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex

::: py_ballisticcalc_ctypes._native.NativeRK4IntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex

::: py_ballisticcalc_ctypes._native.NativeVelocityVerletIntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex

::: py_ballisticcalc_ctypes._native.NativeCashKarpIntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex
            - relative_tolerance
            - absolute_tolerance
            - get_step_stats

::: py_ballisticcalc_ctypes._native.NativeDormandPrinceIntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex
            - relative_tolerance
            - absolute_tolerance
            - get_step_stats

::: py_ballisticcalc_ctypes._native.NativeTsitourasIntegrationEngine
    options:
        group_by_category: false
        inherited_members:
            - get_calc_step
            - integrate
            - integrate_raw_at
            - zero_angle
            - zero_point
            - find_zero_angle
            - find_zero_point
            - find_max_range
            - find_apex
            - relative_tolerance
            - absolute_tolerance
            - get_step_stats
