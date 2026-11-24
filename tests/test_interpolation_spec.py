"""Spec tests for the interpolation convention of integration-step queries (C8b).

The convention (reference implementation: ``TrajectoryStep`` in ``trajectory_data.py``): everything that
works with integration steps -- filter rows, APEX/MACH/ZERO events, ``find_apex``, dense ``get_at`` -- is a
per-step cubic Hermite built from the two end states (positions with velocity-derived slopes).  A 3-point
PCHIP of trajectory data is only a fallback when no step with derivatives brackets the query.  Euler is
not special-cased: its known inaccuracy at an apex step is documented, not worked around.

The pure-Python engines are the reference.  The native (cythonized) engines are expected to follow it; the
cases where bclibc single-point queries still use a 3-point PCHIP are marked ``xfail(strict=False)`` for
the cythonized engines only, until the bclibc change lands.

Run per engine, e.g. ``pytest tests/test_interpolation_spec.py --engine=euler_engine``.
"""

import pytest

from py_ballisticcalc import (
    Ammo,
    BaseEngineConfigDict,
    Calculator,
    DragModel,
    EulerIntegrationEngine,
    OutOfRangeError,
    RK4IntegrationEngine,
    Shot,
    TableG7,
    TrajFlag,
    VelocityVerletIntegrationEngine,
    Weapon,
)
from py_ballisticcalc.trajectory_data import BaseTrajData, TrajectoryStep
from py_ballisticcalc.unit import Angular, Distance, Velocity, Weight

pytestmark = pytest.mark.engine

BCLIBC_REASON = "bclibc single-point queries still use 3-point PCHIP; fixed by the bclibc C8b change"
DENSE_REASON = (
    "needs the newer bclibc/exts (repin): the pinned build narrows time_step to float32 (time rows off by ~1e-8 s) "
    "and its adaptive/Euler dense steps differ from the Hermite rows"
)

# Python Euler reference values (per-step Hermite, from the raw step stream) for the vertical shot below.
EULER_VERTICAL_APEX_TIME = 23.790193  # s
EULER_VERTICAL_APEX_HEIGHT = 12861.55643  # ft
EULER_FINE_STEP_LIMIT_TIME = 23.848012  # s, Euler with calc_step/64: the documented Euler inaccuracy is below 0.07 s

# Tolerances (stated, not tuned): an event row from the same Hermite step must agree to float noise.
TIME_TOL = 1e-6  # s
HEIGHT_TOL = 1e-4  # ft
# The max range of a vertical shot comes from a golden-section search over the elevation, not from an
# event row, so it agrees with the apex height only to the search accuracy (observed <= 3.2e-4 ft).
MAX_RANGE_TOL = 5e-3  # ft
# Adaptive engines: the search sees the error-controlled step noise as well (observed 5.6e-3 .. 2.8e-2 ft).
ADAPTIVE = ("CashKarp", "DormandPrince", "Tsitouras", "SciPy")
ADAPTIVE_MAX_RANGE_TOL = 5e-2  # ft


def _is_cython(engine) -> bool:
    return engine.__module__.startswith("py_ballisticcalc_exts")


def _is_tiny(engine) -> bool:
    return engine.__module__.startswith("tiny_bclibc")


def _family(engine) -> str:
    name = engine.__name__
    # SciPy first: the class names SciPyRK45/RK23/DOP853/... embed other family names (RK4 in "SciPyRK45").
    for key in ("SciPy", "Euler", "RK4", "Verlet", "CashKarp", "DormandPrince", "Tsitouras"):
        if key in name:
            return key
    return name


def _python_counterpart(engine):
    return {
        "Euler": EulerIntegrationEngine,
        "RK4": RK4IntegrationEngine,
        "Verlet": VelocityVerletIntegrationEngine,
    }.get(_family(engine))


def _xfail_cython(request, engine, families, reason=BCLIBC_REASON):
    """Mark the running test as an expected failure for cythonized engines of the given families only."""
    if _is_cython(engine) and _family(engine) in families:
        request.applymarker(pytest.mark.xfail(strict=False, reason=reason))


def _shot(**kwargs) -> Shot:
    """The shot used by the C8b research (a 175 gr .308 G7, 800 m/s)."""
    dm = DragModel(0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(weapon=Weapon(sight_height=Distance.Meter(0.05)), ammo=Ammo(dm, Velocity.MPS(800)), **kwargs)


def _calc(engine, **config) -> Calculator:
    return Calculator(config=BaseEngineConfigDict(cMinimumVelocity=0, **config), engine=engine)


def _apex_row(calc: Calculator, shot: Shot):
    """The APEX row of the filtered trajectory (not of ``find_apex``)."""
    hit = calc.fire(
        shot, Distance.Mile(100), trajectory_step=Distance.Mile(100), flags=TrajFlag.APEX, raise_range_error=False
    )
    row = hit.flag(TrajFlag.APEX)
    assert row is not None, "filtered trajectory has no APEX row"
    return row


def _xy(row):
    return row.time, row.height >> Distance.Foot


# --------------------------------------------------------------------------------------------------------
# (1) find_apex is the APEX row of the filtered trajectory
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("angle", [5.0, 45.0, 89.99])
def test_find_apex_equals_filter_apex_row(loaded_engine_instance, request, angle):
    """``find_apex`` and the APEX row of the filter are the same Hermite event: same time, height, distance."""
    engine = loaded_engine_instance
    # Observed: cythonized rk4/verlet agree; euler (apex step inconsistent with a Hermite) and the adaptive
    # engines (wide steps) differ, because find_apex is a 3-point PCHIP there.
    _xfail_cython(request, engine, {"Euler", "CashKarp", "DormandPrince", "Tsitouras"})
    shot = _shot(relative_angle=Angular.Degree(angle))
    calc = _calc(engine)
    apex = calc.find_apex(shot)
    row = _apex_row(calc, shot)
    t_a, h_a = _xy(apex)
    t_r, h_r = _xy(row)
    assert t_a == pytest.approx(t_r, abs=TIME_TOL), (
        f"apex time {t_a:.9f} vs filter row {t_r:.9f} (diff {t_a - t_r:+.3e})"
    )
    assert h_a == pytest.approx(h_r, abs=HEIGHT_TOL), (
        f"apex height {h_a:.6f} vs filter row {h_r:.6f} (diff {h_a - h_r:+.3e})"
    )
    assert (apex.distance >> Distance.Foot) == pytest.approx(row.distance >> Distance.Foot, abs=HEIGHT_TOL)


# --------------------------------------------------------------------------------------------------------
# (2) vertical shot: apex height / OutOfRangeError.max_range, within the same method family
# --------------------------------------------------------------------------------------------------------


def _vertical_max_range(engine) -> float:
    """OutOfRangeError.max_range [ft] of a vertical shot: the apex slant distance (= height at 90 degrees)."""
    calc = Calculator(engine=engine)
    with pytest.raises(OutOfRangeError) as info:
        calc.find_zero_angle(_shot(look_angle=Angular.Degree(90)), Distance.Foot(30000))
    return info.value.max_range >> Distance.Foot


def test_vertical_max_range_matches_own_apex_height(loaded_engine_instance):
    """Within one engine, the vertical max range is the apex height (to the golden-section search accuracy)."""
    engine = loaded_engine_instance
    if _is_tiny(engine):
        pytest.skip(
            "the vertical max range is read from OutOfRangeError.max_range; the native tiny_bclibc engine reports the "
            "out-of-range zero search as a plain SolverRuntimeError string that carries no max_range"
        )
    apex = _calc(engine).find_apex(_shot(relative_angle=Angular.Degree(89.99)))
    apex_h = apex.height >> Distance.Foot
    max_range = _vertical_max_range(engine)
    tol = ADAPTIVE_MAX_RANGE_TOL if _family(engine) in ADAPTIVE else MAX_RANGE_TOL
    assert max_range == pytest.approx(apex_h, abs=tol), f"max_range {max_range:.6f} vs apex {apex_h:.6f}"


def test_vertical_apex_and_max_range_match_python_family(loaded_engine_instance, request):
    """A cythonized engine agrees with the pure-Python engine of the same method on the vertical shot."""
    engine = loaded_engine_instance
    ref_cls = _python_counterpart(engine)
    if not _is_cython(engine) or ref_cls is None:
        pytest.skip(
            "cross-engine comparison needs a cythonized engine with a pure-Python counterpart (euler/rk4/verlet)"
        )
    _xfail_cython(request, engine, {"Euler"})
    shot = _shot(relative_angle=Angular.Degree(89.99))
    t_c, h_c = _xy(_calc(engine).find_apex(shot))
    t_p, h_p = _xy(_calc(ref_cls).find_apex(shot))
    mr_c, mr_p = _vertical_max_range(engine), _vertical_max_range(ref_cls)
    msg = (
        f"apex t {t_c:.6f} vs {t_p:.6f} ({t_c - t_p:+.3e} s); h {h_c:.5f} vs {h_p:.5f} ({h_c - h_p:+.3e} ft); "
        f"max_range {mr_c:.5f} vs {mr_p:.5f} ({mr_c - mr_p:+.3e} ft)"
    )
    assert t_c == pytest.approx(t_p, abs=TIME_TOL), msg
    assert h_c == pytest.approx(h_p, abs=HEIGHT_TOL), msg
    assert mr_c == pytest.approx(mr_p, abs=MAX_RANGE_TOL), msg


# --------------------------------------------------------------------------------------------------------
# (3) dense get_at equals the Hermite row of the filter at the same distance / time, for wide steps
# --------------------------------------------------------------------------------------------------------

_LOOSE = {"relative_tolerance": 1e-3, "absolute_tolerance": 1e-3}  # adaptive engines: few, wide steps


def _wide_step_engine(engine):
    """An instance with wide steps: loosened tolerances if the engine is adaptive, else as loaded."""
    if _family(engine) in ADAPTIVE:
        return _calc(engine, **_LOOSE)
    return _calc(engine)


@pytest.mark.parametrize("key,target", [("distance", Distance.Yard(733)), ("time", 1.234)])
def test_dense_get_at_equals_hermite_row(loaded_engine_instance, request, key, target):
    """With dense output, ``HitResult.get_at`` returns the per-step Hermite row, not an interpolation of sparse rows."""
    engine = loaded_engine_instance
    # Cython: HitResult.get_at calls the native dense get_at (C++ Hermite of the step).
    _xfail_cython(request, engine, {"Euler", "RK4", "Verlet", *ADAPTIVE}, DENSE_REASON)
    if _family(engine) == "SciPy":
        request.applymarker(
            pytest.mark.xfail(
                strict=False,
                reason="scipy engine keeps no accepted-step list; HitResult.get_at falls back to 3-point PCHIP on records",
            )
        )
    shot = _shot(relative_angle=Angular.Degree(5.0))
    calc = _wide_step_engine(engine)
    try:
        # Records every 500 yd (wide), dense data kept.
        dense = calc.fire(
            shot, Distance.Yard(1000), trajectory_step=Distance.Yard(500), flags=TrajFlag.NONE, dense_output=True
        )
    except NotImplementedError:
        pytest.skip("dense_output is not supported by this engine")
    # The reference row: the filter's own Hermite row, sampled exactly at the target.
    if key == "distance":
        ref = calc.fire(shot, Distance.Yard(1000), trajectory_step=target, flags=TrajFlag.RANGE)
        ref_row = next(r for r in ref.records if abs((r.distance >> Distance.Yard) - 733) < 1e-6)
    else:
        ref = calc.fire(shot, Distance.Yard(1000), trajectory_step=Distance.Yard(1000), time_step=target)
        ref_row = next(r for r in ref.records if abs(r.time - target) < 1e-9)
    got = dense.get_at(key, target)
    gh, rh = got.height >> Distance.Foot, ref_row.height >> Distance.Foot
    gx, rx = got.distance >> Distance.Foot, ref_row.distance >> Distance.Foot
    gv, rv = got.velocity >> Velocity.FPS, ref_row.velocity >> Velocity.FPS
    msg = f"{key}: height {gh:.6f} vs {rh:.6f} ({gh - rh:+.3e}); distance {gx:.6f} vs {rx:.6f} ({gx - rx:+.3e}); v {gv:.6f} vs {rv:.6f}"
    assert gh == pytest.approx(rh, abs=1e-6), msg
    assert gx == pytest.approx(rx, abs=1e-6), msg
    assert got.time == pytest.approx(ref_row.time, abs=1e-9), msg


@pytest.mark.parametrize("attr", ["height", "velocity", "mach", "slant_height", "slant_distance", "distance", "time"])
def test_dense_get_at_every_attribute_equals_hermite_row(loaded_engine_instance, request, attr):
    """``HitResult.get_at(attr, v)`` on dense data returns the filter's Hermite row where ``attr == v``.

    The value is read off the filter's own row at t = 1.234 s (before the apex: every key is monotone there),
    then ``get_at`` has to find that same row from the value alone.
    """
    engine = loaded_engine_instance
    _xfail_cython(request, engine, {"Euler", "RK4", "Verlet", *ADAPTIVE}, DENSE_REASON)
    if _family(engine) == "SciPy":
        request.applymarker(
            pytest.mark.xfail(strict=False, reason="scipy engine keeps no accepted-step list; no dense get_at")
        )
    if _family(engine) == "Euler" and attr in ("velocity", "mach"):
        request.applymarker(
            pytest.mark.xfail(
                strict=False,
                reason="Euler's velocity within a step is not the Hermite of its end states (also in pure Python)",
            )
        )
    shot = _shot(relative_angle=Angular.Degree(5.0), look_angle=Angular.Degree(2.0))
    calc = _wide_step_engine(engine)
    t = 1.234
    try:
        dense = calc.fire(
            shot, Distance.Yard(1000), trajectory_step=Distance.Yard(500), flags=TrajFlag.NONE, dense_output=True
        )
    except NotImplementedError:
        pytest.skip("dense_output is not supported by this engine")
    ref = calc.fire(shot, Distance.Yard(1000), trajectory_step=Distance.Yard(1000), time_step=t)
    ref_row = next(r for r in ref.records if abs(r.time - t) < 1e-9)
    target = getattr(ref_row, attr)
    got = dense.get_at(attr, target)
    msg = f"{attr}: time {got.time:.9f} vs {ref_row.time:.9f}"
    assert got.time == pytest.approx(ref_row.time, abs=1e-6), msg
    for name in ("height", "distance", "slant_height", "slant_distance"):
        g, r = getattr(got, name) >> Distance.Foot, getattr(ref_row, name) >> Distance.Foot
        assert g == pytest.approx(r, abs=1e-6), f"{msg}; {name} {g:.6f} vs {r:.6f} ({g - r:+.3e})"
    assert got.velocity >> Velocity.FPS == pytest.approx(ref_row.velocity >> Velocity.FPS, abs=1e-6), msg


def test_dense_get_at_matches_manual_hermite_step(loaded_engine_instance):
    """Pure-Python engines: ``get_at`` equals ``TrajectoryStep`` evaluated on the bracketing accepted step."""
    engine = loaded_engine_instance
    if _is_cython(engine):
        pytest.skip("base_data of a cythonized engine is a native sequence, not a list of accepted steps")
    shot = _shot(relative_angle=Angular.Degree(5.0))
    calc = _calc(engine)
    try:
        dense = calc.fire(shot, Distance.Yard(1000), trajectory_step=Distance.Yard(500), dense_output=True)
    except NotImplementedError:
        pytest.skip("dense_output is not supported by this engine")
    if not isinstance(dense.base_data, list) or not isinstance(dense.base_data[0], BaseTrajData):
        pytest.skip("this engine does not expose a flat list of accepted steps")
    t = 1.234
    start, end = next((a, b) for a, b in zip(dense.base_data, dense.base_data[1:]) if a.time < t < b.time)
    expected = TrajectoryStep(start, end).at_time(t)
    got = dense.get_at("time", t)
    assert got.time == pytest.approx(t, abs=1e-9)
    assert (got.height >> Distance.Foot) == pytest.approx(expected.position.y, abs=1e-9)
    assert (got.distance >> Distance.Foot) == pytest.approx(expected.position.x, abs=1e-9)


# --------------------------------------------------------------------------------------------------------
# (4) Euler: documented behaviour, no special-casing
# --------------------------------------------------------------------------------------------------------


def test_euler_vertical_apex_is_the_hermite_value(loaded_engine_instance, request):
    """Euler's apex on the vertical shot is the per-step Hermite value (23.790193 s, 12861.556 ft).

    Euler's own step (p1 = p0 + v1*dt) is inconsistent with a (position, velocity) Hermite, so the apex
    time is early by up to ~0.06 s against the fine-step limit (23.848 s).  That is the documented
    inaccuracy; the convention does not special-case it (no linear/PCHIP substitute)."""
    engine = loaded_engine_instance
    if _family(engine) != "Euler":
        pytest.skip("Euler-specific")
    _xfail_cython(request, engine, {"Euler"})
    apex = _calc(engine).find_apex(_shot(relative_angle=Angular.Degree(89.99)))
    t, h = _xy(apex)
    msg = f"apex t={t:.6f} h={h:.5f} (Hermite {EULER_VERTICAL_APEX_TIME}, {EULER_VERTICAL_APEX_HEIGHT})"
    assert t == pytest.approx(EULER_VERTICAL_APEX_TIME, abs=TIME_TOL), msg
    assert h == pytest.approx(EULER_VERTICAL_APEX_HEIGHT, abs=2e-5), msg


def test_euler_vertical_apex_inaccuracy_is_bounded(loaded_engine_instance):
    """The documented Euler error at the apex step stays below 0.07 s against the fine-step limit (either scheme)."""
    engine = loaded_engine_instance
    if _family(engine) != "Euler":
        pytest.skip("Euler-specific")
    apex = _calc(engine).find_apex(_shot(relative_angle=Angular.Degree(89.99)))
    assert abs(apex.time - EULER_FINE_STEP_LIMIT_TIME) < 0.07
