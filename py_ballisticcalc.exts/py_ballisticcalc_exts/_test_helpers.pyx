# cython: freethreading_compatible=True
"""Test helper accessors for Cython-specific tests.

This module is NOT part of the public API. It provides a minimal surface for
tests to directly evaluate the C-side drag interpolation (BCLIBC_ShotProps_dragByMach)
and inspect underlying prepared spline coefficients (a,b,c,d) plus Mach knots.

We deliberately keep this separate from production engine modules to avoid
polluting hot paths or public symbols. Import only inside test code.
"""

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ShotProps,
    BCLIBC_ShotProps_dragByMach,
    BCLIBC_ShotProps_spinDrift,
    BCLIBC_ShotProps_updateStabilityCoefficient,
    BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude,
    BCLIBC_TrajFlag,
    BCLIBC_calculateEnergy,
    BCLIBC_calculateOgw,
    BCLIBC_BaseTrajData,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT

__all__ = [
    'init_shot',
    'free_shot',
    'shot_props_addr',
    'drag_eval',
    'drag_eval_current',
    'spin_drift_eval',
    'stability_update_eval',
    'energy_eval',
    'ogw_eval',
    'density_and_mach_eval',
    'integration_minimal',
    'step_count',
    'introspect_shot',
]


# Small Python factory for tests and convenience
cpdef make_base_traj_data(double time, double px, double py, double pz,
                          double vx, double vy, double vz, double mach):
    return BaseTrajDataT(BCLIBC_BaseTrajData(time, BCLIBC_V3dT(px, py, pz), BCLIBC_V3dT(vx, vy, vz), mach))

cpdef double drag_eval(size_t shot_props_addr, double mach):
    """Evaluate drag (standard drag factor / ballistic coefficient scaling) for a Mach.

    Args:
        shot_props_addr: `id()` of an internal BCLIBC_ShotProps struct exposed via engine._engine.shot
        mach: Mach number to evaluate

    Returns:
        Drag factor computed by the C spline + Mach lookup.

    Notes:
        We pass a raw address obtained from a Cython engine instance to avoid adding
        a new public attribute. Tests obtain it with `shot_props_addr = <long>&engine._engine.shot`.
    """
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    return BCLIBC_ShotProps_dragByMach(sp_ptr, mach)

cpdef double drag_eval_current(object engine, double mach):
    """Evaluate drag using engine's current in-memory ShotProps without exposing raw pointer."""
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    return BCLIBC_ShotProps_dragByMach(&e._engine.shot, mach)

cpdef size_t shot_props_addr(object engine):
    """Return raw address of the engine's internal BCLIBC_ShotProps struct.

    Engine must have performed at least one initialization (e.g., integrate or zeroing)
    so that its _engine.shot contains prepared curve + mach list.
    """
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    return <size_t>&e._engine.shot

cpdef size_t init_shot(object engine, object shot):
    """Initialize shot props inside engine and return its address.

    Leaves the trajectory allocated for further direct C access.
    """
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    cdef BCLIBC_ShotProps *ptr = e._init_trajectory(shot)
    return <size_t>ptr

cpdef void free_shot(object engine):
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    e._release_trajectory()

cpdef double spin_drift_eval(size_t shot_props_addr, double time_s):
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    return BCLIBC_ShotProps_spinDrift(sp_ptr, time_s)

cpdef double stability_update_eval(size_t shot_props_addr):
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    BCLIBC_ShotProps_updateStabilityCoefficient(sp_ptr)
    return sp_ptr.stability_coefficient

cpdef dict introspect_shot(size_t shot_props_addr):
    """Return basic structural info about BCLIBC_ShotProps for debugging."""
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    if not sp_ptr:
        return {'null': True}
    return {'bc': sp_ptr.bc, 'curve_len': sp_ptr.curve.length, 'mach_len': sp_ptr.mach_list.length}

cpdef double energy_eval(size_t shot_props_addr, double velocity_fps):
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    return BCLIBC_calculateEnergy(sp_ptr.weight, velocity_fps)

cpdef double ogw_eval(size_t shot_props_addr, double velocity_fps):
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    return BCLIBC_calculateOgw(sp_ptr.weight, velocity_fps)

cpdef tuple density_and_mach_eval(size_t shot_props_addr, double altitude_ft):
    cdef BCLIBC_ShotProps *sp_ptr = <BCLIBC_ShotProps *> shot_props_addr
    cdef double density_ratio = 0.0
    cdef double mach = 0.0
    BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(&sp_ptr.atmo, altitude_ft, &density_ratio, &mach)
    return density_ratio, mach

cpdef tuple integration_minimal(object engine, size_t shot_props_addr,
                                double range_limit_ft, double range_step_ft, double time_step):
    """Call engine._integrate directly with current shot props."""
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    return e._integrate(range_limit_ft, range_step_ft, time_step, BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_NONE)

cpdef int step_count(object engine):
    cdef CythonizedBaseIntegrationEngine e = <CythonizedBaseIntegrationEngine>engine
    return e.integration_step_count
