"""The maximum-range search of a downhill shot bounds each probe's flight time (600 s, as in the C++ core).

For a downhill line of sight the drop and altitude limits are lifted (multiplied by 4 up to 1e6 ft) until a probe crosses
the line of sight, and a probe that never does was integrated all the way to the lifted limit.  For steep lines of sight
that took minutes (look -45 degrees: 80-90 s, look -89.9 degrees: more than 300 s, against 0.2 s and 2.3 s in the C++
core).  A probe that exceeds the flight time bound reports "no crossing", exactly as one that hits the limit.
"""

import math
import signal
import warnings

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

# Maximum range (m) of the 0.1 m sight, 800 m/s, G7 BC 0.243 shot, recorded BEFORE the flight time bound (engine class ->
# look angle (deg) -> metres).  The bound must not move a result that was found without it.
RECORDED_M = {
    "py_ballisticcalc.engines.rk4.RK4IntegrationEngine": {
        -10.0: 5091.248666436787,
        -20.0: 5658.52233086307,
        -30.0: 6418.493174044794,
        -45.0: 8184.854413569999,
    },
    "py_ballisticcalc.engines.euler.EulerIntegrationEngine": {
        -10.0: 5090.866937296002,
        -20.0: 5658.112634784975,
        -30.0: 6418.042965178285,
        -45.0: 8184.304688711979,
    },
    "py_ballisticcalc.engines.velocity_verlet.VelocityVerletIntegrationEngine": {
        -10.0: 5091.489762014388,
        -20.0: 5658.776152447689,
        -30.0: 6418.763564979206,
        -45.0: 8185.170112814819,
    },
    "py_ballisticcalc.engines.scipy_engine.SciPyIntegrationEngine": {
        -10.0: 5091.532287271274,
        -20.0: 5658.815006720419,
        -30.0: 6418.79384919901,
        -45.0: 8185.191425646104,
    },
}


class _Hang(Exception):
    pass


def _run_with_time_bound(seconds: int, func, *args):
    """Run func(*args); fail with _Hang if it takes longer than `seconds` (Unix only; elsewhere no bound).

    Pyodide (WebAssembly) defines signal.SIGALRM but has no signal.alarm, so both must be there."""
    if not (hasattr(signal, "SIGALRM") and hasattr(signal, "alarm")):
        return func(*args)

    def _on_alarm(signum, frame):
        raise _Hang(f"did not finish in {seconds} s")

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(seconds)
    try:
        return func(*args)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _make_shot(look_angle_deg: float) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.1), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(800.0)),
        look_angle=Angular.Degree(look_angle_deg),
    )


def _max_range(calc: Calculator, look_angle_deg: float):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # one "No ZERO_DOWN found" warning per probe without a crossing
        return calc.find_max_range(_make_shot(look_angle_deg))


def _is_pure_python(engine) -> bool:
    module = getattr(engine, "__module__", "") or ""
    return module.startswith("py_ballisticcalc.engines.") and "scipy" not in module


@pytest.mark.parametrize("look_angle", (-45.0, -89.9))
def test_steep_downhill_max_range_is_bounded_in_time(loaded_engine_instance, look_angle):
    """find_max_range of a steep downhill shot returns in bounded time (the pure-Python engines took 70-110 s at -45 degrees
    and more than 300 s at -89.9; now ~20 s and ~200 s: each of its ~30 probes that never crosses is followed for 600 s of
    flight, which is a few seconds of pure-Python integration)."""
    if look_angle < -60.0 and _is_pure_python(loaded_engine_instance):
        pytest.skip("~200 s on the pure-Python engines (30 probes of 600 s of flight); covered by the fast engines")
    calc = Calculator(engine=loaded_engine_instance)
    max_range, _ = _run_with_time_bound(45, _max_range, calc, look_angle)
    assert math.isfinite(max_range >> Distance.Meter)
    assert max_range >> Distance.Meter >= 0.0
    recorded = RECORDED_M.get(f"{loaded_engine_instance.__module__}.{loaded_engine_instance.__name__}")
    if recorded and look_angle in recorded:  # (-45 degrees: the search finished before the bound too, same value)
        rel = 1e-6 if "scipy" in loaded_engine_instance.__module__ else 1e-9
        assert max_range >> Distance.Meter == pytest.approx(recorded[look_angle], rel=rel)


@pytest.mark.parametrize("look_angle", (-10.0, -20.0, -30.0))
def test_downhill_max_range_unchanged(loaded_engine_instance, look_angle):
    """Where the search finished without the bound the bound changes nothing."""
    key = f"{loaded_engine_instance.__module__}.{loaded_engine_instance.__name__}"
    recorded = RECORDED_M.get(key)
    if recorded is None:
        pytest.skip(f"no values recorded for {key}")
    calc = Calculator(engine=loaded_engine_instance)
    max_range, _ = _run_with_time_bound(60, _max_range, calc, look_angle)
    # (SciPy's bounded Brent search minimises a noisy objective: its results are compared to 1e-6, as in test_zero_downhill)
    rel = 1e-6 if "scipy" in loaded_engine_instance.__module__ else 1e-9
    assert max_range >> Distance.Meter == pytest.approx(recorded[look_angle], rel=rel)
