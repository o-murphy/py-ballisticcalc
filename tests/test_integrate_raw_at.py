"""``integrate_raw_at``: integrate until a key reaches a value and return the raw point (same API on every engine).

The cythonized engines wrap bclibc's ``integrate_at``; the pure-Python engines (rk4, euler, verlet) and the SciPy
engines implement it in ``BaseIntegrationEngine`` / ``SciPyIntegrationEngine``.  The convention (user decision C8b): the
crossing is located on the cubic Hermite of the first accepted step whose end values bracket the target, with a
3-point PCHIP only as a fallback.  The reference of these tests is an independent search over the dense steps
(``TrajectoryStep``) of the engine's own trajectory.  The SciPy engines have no step list: the crossing is a solver
event on the dense output, so they are checked for exactness of the key, against their own rows and against RK4
(to the accuracy of the two integrations).

Run per engine, e.g. ``pytest tests/test_integrate_raw_at.py --engine=python+rk4``.
"""

import math
from itertools import pairwise

import pytest

from py_ballisticcalc import (
    Ammo,
    DragModel,
    EulerIntegrationEngine,
    InterceptionError,
    RK4IntegrationEngine,
    Shot,
    SolverRuntimeError,
    TableG7,
    VelocityVerletIntegrationEngine,
    Weapon,
    Wind,
)
from py_ballisticcalc.engines.base_engine import RAW_KEY_GETTERS
from py_ballisticcalc.trajectory_data import BaseTrajData, TrajectoryData, TrajectoryStep
from py_ballisticcalc.unit import Angular, Distance, Velocity, Weight

pytestmark = pytest.mark.engine

KEYS = tuple(RAW_KEY_GETTERS)
BCLIBC_REASON = "pinned bclibc: the single-point handler uses a 3-point PCHIP for this key; fixed by the repin (C8b)"
PCHIP_KEYS = (
    "time",
    "mach",
    "position.y",
    "position.z",
    "velocity.x",
    "velocity.y",
    "velocity.z",
)  # position.x was Hermite


def _is_cython(engine) -> bool:
    return engine.__module__.startswith("py_ballisticcalc_exts")


def _family(engine) -> str:
    name = engine.__name__
    for key in ("SciPy", "Euler", "RK4", "Verlet", "CashKarp", "DormandPrince", "Tsitouras"):
        if key in name:
            return key
    return name


def _shot(angle_deg: float = 3.0) -> Shot:
    """A 175 gr .308 G7 at 800 m/s with a 5 m/s cross wind (so that position.z and velocity.z are not constant)."""
    dm = DragModel(0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.05)),
        ammo=Ammo(dm, Velocity.MPS(800)),
        relative_angle=Angular.Degree(angle_deg),
        winds=[Wind(Velocity.MPS(5), Angular.Degree(90))],
    )


def _raw(data) -> tuple[float, float, float, float, float, float, float, float]:
    """(time, x, y, z, vx, vy, vz, mach) of a raw point of any engine (BaseTrajData or CythonizedBaseTrajData)."""
    p, v = data.position, data.velocity
    return data.time, p.x, p.y, p.z, v.x, v.y, v.z, data.mach


def _key(data, key: str) -> float:
    top, _, component = key.partition(".")
    obj = getattr(data, top)
    return getattr(obj, component) if component else obj


def _dense_points(engine, shot: Shot) -> list[BaseTrajData] | None:
    """The accepted steps of the engine's trajectory (None for the SciPy engines, which keep no step list)."""
    hit = engine({}).integrate(shot, Distance.Mile(100), dense_output=True)
    if hit.base_data is None:
        return None
    return hit._native_points() if _is_cython(engine) else list(hit.base_data)


def _first_crossing(points: list[BaseTrajData], key: str, target: float) -> BaseTrajData:
    """The independent reference: bisection on the cubic Hermite of the first step whose ends bracket the target."""
    get = RAW_KEY_GETTERS[key]
    for a, b in pairwise(points):
        k0, k1 = get(a), get(b)
        if not ((k0 <= target <= k1) or (k1 <= target <= k0)):
            continue
        if k0 == target:
            return a
        step = TrajectoryStep(a, b)
        lo, hi = a.time, b.time
        flo = k0 - target
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            fmid = get(step.at_time(mid)) - target
            if (fmid < 0) == (flo < 0):
                lo, flo = mid, fmid
            else:
                hi = mid
        return step.at_time(0.5 * (lo + hi))
    raise AssertionError(f"reference trajectory does not reach {key} = {target}")


def _targets(points: list[BaseTrajData]) -> dict[str, float]:
    """A value of every key strictly inside a step of the reference trajectory (so a crossing must be interpolated)."""
    n = len(points)

    def between(key: str, k: int, frac: float, k2: int | None = None) -> float:
        get = RAW_KEY_GETTERS[key]
        a, b = get(points[k]), get(points[min(k + 1 if k2 is None else k2, n - 1)])
        return a + frac * (b - a)

    return {
        "time": between("time", n // 3, 0.4),
        "mach": between(
            "mach", 4 * n // 5, 0.5, 4 * n // 5 + 20
        ),  # on the way down: the speed of sound is flat near the apex
        "position.x": between("position.x", n // 3, 0.37),
        "position.y": between("position.y", n // 10, 0.5),
        "position.z": between("position.z", n // 3, 0.5),
        "velocity.x": between("velocity.x", n // 2, 0.45),
        "velocity.y": between("velocity.y", n // 2, 0.45),
        "velocity.z": between("velocity.z", n // 2, 0.45),
    }


# --------------------------------------------------------------------------------------------------------
# (1) the returned point is the crossing on the Hermite of the first bracketing step
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", KEYS)
def test_point_equals_hermite_crossing(loaded_engine_instance, request, key):
    engine = loaded_engine_instance
    if _is_cython(engine) and key in PCHIP_KEYS:
        request.applymarker(pytest.mark.xfail(strict=False, reason=BCLIBC_REASON))
    shot = _shot()
    points = _dense_points(engine, shot)
    if points is None:
        pytest.skip("SciPy engines keep no step list: see test_scipy_*")
    target = _targets(points)[key]
    expected = _first_crossing(points, key, target)
    raw, full = engine({}).integrate_raw_at(shot, key, target)
    got, want = _raw(raw), _raw(expected)
    msg = f"{key}={target}: got {got}, expected {want}"
    # An engine's step stream is deterministic: the crossing agrees with the independent search to round-off.
    assert got[0] == pytest.approx(want[0], abs=1e-6), msg
    for g, w in zip(got[1:7], want[1:7]):
        assert g == pytest.approx(w, abs=1e-6), msg
    assert got[7] == pytest.approx(want[7], abs=1e-6), msg
    assert _key(raw, key) == pytest.approx(target, abs=1e-9)
    assert isinstance(full, TrajectoryData)
    assert full.time == pytest.approx(raw.time)
    assert full.distance >> Distance.Foot == pytest.approx(raw.position.x, abs=1e-6)
    assert full.height >> Distance.Foot == pytest.approx(raw.position.y, abs=1e-6)


def test_apex_is_the_first_crossing_of_vertical_velocity(loaded_engine_instance, request):
    """`velocity.y = 0` is the apex row of the filter (same step, same Hermite root)."""
    engine = loaded_engine_instance
    if _is_cython(engine):
        request.applymarker(pytest.mark.xfail(strict=False, reason=BCLIBC_REASON))
    shot = _shot()
    inst = engine({})
    raw, _ = inst.integrate_raw_at(shot, "velocity.y", 0.0)
    apex = inst.find_apex(shot)
    assert raw.time == pytest.approx(apex.time, abs=1e-6)
    assert raw.position.x == pytest.approx(apex.distance >> Distance.Foot, abs=1e-5)
    assert raw.position.y == pytest.approx(apex.height >> Distance.Foot, abs=1e-5)
    assert raw.velocity.y == pytest.approx(0.0, abs=1e-9)


def test_first_crossing_of_a_non_monotone_key(loaded_engine_instance, request):
    """`position.y` crosses a height twice (up, then down): the first crossing, on the way up, is returned."""
    engine = loaded_engine_instance
    if _is_cython(engine):
        request.applymarker(pytest.mark.xfail(strict=False, reason=BCLIBC_REASON))
    inst = engine({})
    shot = _shot()
    apex = inst.find_apex(shot)
    target = 0.5 * (apex.height >> Distance.Foot)
    raw, _ = inst.integrate_raw_at(shot, "position.y", target)
    assert raw.velocity.y > 0.0
    assert raw.time < apex.time
    assert raw.position.y == pytest.approx(target, abs=1e-9)


# --------------------------------------------------------------------------------------------------------
# (2) SciPy: a solver event on the dense output
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", KEYS)
def test_scipy_point_is_exact_and_matches_rk4(loaded_engine_instance, key):
    engine = loaded_engine_instance
    if _family(engine) != "SciPy":
        pytest.skip("SciPy engines only")
    shot = _shot()
    target = _targets(_dense_points(RK4IntegrationEngine, shot))[key]
    raw, full = engine({}).integrate_raw_at(shot, key, target)
    assert _key(raw, key) == pytest.approx(target, abs=1e-9)
    assert full.time == pytest.approx(raw.time)
    # Two different integrations of the same flight: they agree to the accuracy of the solutions, not to round-off.
    ref = _first_crossing(_dense_points(RK4IntegrationEngine, shot), key, target)
    for g, w in zip(_raw(raw), _raw(ref)):
        assert g == pytest.approx(w, rel=5e-3, abs=5e-3)


@pytest.mark.parametrize("key", ("time", "position.x"))
def test_scipy_point_equals_its_own_row(loaded_engine_instance, key):
    """The crossing is found on the same dense output as the engine's rows: a row at the target is the same point."""
    engine = loaded_engine_instance
    if _family(engine) != "SciPy":
        pytest.skip("SciPy engines only")
    shot = _shot()
    inst = engine({})
    target = _targets(_dense_points(RK4IntegrationEngine, shot))[key]
    raw, _ = inst.integrate_raw_at(shot, key, target)
    if key == "position.x":
        hit = inst.integrate(shot, Distance.Foot(target), dist_step=Distance.Foot(target))
        row = hit.records[-1]
        assert row.distance >> Distance.Foot == pytest.approx(target, abs=1e-6)
    else:
        hit = inst.integrate(shot, Distance.Mile(100), time_step=target)
        row = next(r for r in hit.records if abs(r.time - target) < 1e-9)
    assert row.time == pytest.approx(raw.time, abs=1e-6)
    assert row.height >> Distance.Foot == pytest.approx(raw.position.y, abs=1e-5)


# --------------------------------------------------------------------------------------------------------
# (3) a target that is not reached raises InterceptionError carrying the last data
# --------------------------------------------------------------------------------------------------------

UNREACHABLE = {
    "time": 1e6,
    "mach": 1e9,
    "position.x": 1e8,
    "position.y": 1e7,
    "position.z": 1e7,
    "velocity.x": 1e6,
    "velocity.y": 1e6,
    "velocity.z": 1e6,
}


@pytest.mark.parametrize("key", KEYS)
def test_unreached_target_raises_interception_error(loaded_engine_instance, key):
    engine = loaded_engine_instance
    with pytest.raises(InterceptionError) as info:
        engine({}).integrate_raw_at(_shot(), key, UNREACHABLE[key])
    error = info.value
    assert isinstance(error, SolverRuntimeError)
    assert "Intercept point not found" in str(error)
    assert len(error.last_data) == 2
    raw, full = error.last_data
    assert isinstance(full, TrajectoryData)
    # the last integrated point: the flight ended (minimum velocity, drop or altitude), well after launch
    assert raw.time > 1.0
    assert full.time == pytest.approx(raw.time)
    assert full.distance >> Distance.Foot == pytest.approx(raw.position.x, abs=1e-6)
    assert _key(raw, key) != UNREACHABLE[key]


def test_unknown_key_is_an_attribute_error(loaded_engine_instance):
    with pytest.raises(AttributeError):
        loaded_engine_instance({}).integrate_raw_at(_shot(), "velocity", 100.0)


# --------------------------------------------------------------------------------------------------------
# (4) edges: a crossing inside the first step, a target equal to the launch value
# --------------------------------------------------------------------------------------------------------


def test_crossing_inside_the_first_step(loaded_engine_instance, request):
    """With a tiny elevation the apex is inside the first step (bclibc C8a): it must be found, not skipped."""
    engine = loaded_engine_instance
    if _is_cython(engine):
        request.applymarker(
            pytest.mark.xfail(strict=False, reason="pinned bclibc may miss a crossing in the first step")
        )
    shot = _shot(angle_deg=0.001)
    inst = engine({})
    raw, _ = inst.integrate_raw_at(shot, "velocity.y", 0.0)
    v_y0 = 800 * 3.2808399 * math.sin(math.radians(0.001))
    assert raw.velocity.y == pytest.approx(0.0, abs=1e-9)
    # vacuum estimate v_y0 / g: drag changes it by a fraction of a percent; Euler is a few percent off in a single step
    assert raw.time == pytest.approx(v_y0 / 32.17405, rel=0.1)
    assert raw.position.x > 0.0


@pytest.mark.parametrize("key,value_of", [("time", lambda p: p.time), ("position.x", lambda p: p.position.x)])
def test_target_equal_to_the_launch_value_returns_the_launch_state(loaded_engine_instance, request, key, value_of):
    """The first step brackets a target equal to its start value, so the launch state is returned (as in bclibc)."""
    if _is_cython(loaded_engine_instance) and key == "time":
        request.applymarker(
            pytest.mark.xfail(
                strict=False, reason="pinned bclibc: time 0 is not found (3-point window); fixed by the repin (C8b)"
            )
        )
    raw, _ = loaded_engine_instance({}).integrate_raw_at(_shot(), key, 0.0)
    assert value_of(raw) == 0.0
    assert raw.time == pytest.approx(0.0, abs=1e-12)
    assert raw.position.x == pytest.approx(0.0, abs=1e-12)
    assert raw.position.y == pytest.approx(-(Distance.Meter(0.05) >> Distance.Foot), abs=1e-9)
    assert raw.velocity.x == pytest.approx(800 * 3.2808399 * math.cos(math.radians(3.0)), rel=1e-6)


# --------------------------------------------------------------------------------------------------------
# (5) parity of the cythonized engines with the pure-Python ones
# --------------------------------------------------------------------------------------------------------

PYTHON_COUNTERPART = {
    "Euler": EulerIntegrationEngine,
    "RK4": RK4IntegrationEngine,
    "Verlet": VelocityVerletIntegrationEngine,
}


@pytest.mark.parametrize("key", KEYS)
def test_cython_matches_python_engine(loaded_engine_instance, request, key):
    engine = loaded_engine_instance
    counterpart = PYTHON_COUNTERPART.get(_family(engine))
    if not _is_cython(engine) or counterpart is None:
        pytest.skip("parity of a cythonized engine with its pure-Python counterpart")
    if key in PCHIP_KEYS:
        request.applymarker(pytest.mark.xfail(strict=False, reason=BCLIBC_REASON))
    shot = _shot()
    target = _targets(_dense_points(counterpart, shot))[key]
    got = _raw(engine({}).integrate_raw_at(shot, key, target)[0])
    want = _raw(counterpart({}).integrate_raw_at(shot, key, target)[0])
    for g, w in zip(got, want):
        assert g == pytest.approx(w, rel=1e-7, abs=1e-5), f"{key}={target}: cython {got} vs python {want}"
