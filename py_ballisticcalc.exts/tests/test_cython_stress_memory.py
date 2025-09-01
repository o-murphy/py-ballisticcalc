import gc
import os
import math
import pytest

pytestmark = pytest.mark.stress

from py_ballisticcalc import (
    BaseEngineConfigDict,
    Calculator,
    Ammo,
    Shot,
    Distance,
    DragModel,
    TableG7,
    Velocity,
    Weight,
)

from py_ballisticcalc_exts.base_traj_seq import CBaseTrajSeq


def _base_config():
    return BaseEngineConfigDict(
        cMinimumVelocity=0.0,
        cMinimumAltitude=0.0,
        cMaximumDrop=0.0,
    )


def _shot():
    dm = DragModel(bc=0.243, drag_table=TableG7,
                   weight=Weight.Grain(175), diameter=Distance.Millimeter(7.62), length=Distance.Millimeter(32.0))
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))


def _rss_bytes() -> int:
    # psutil not required; use Python's tracemalloc only measures Python allocs.
    # On Linux we could read /proc/self/statm; on Windows, fall back to tracemalloc proxy.
    try:
        import psutil  # type: ignore

        return psutil.Process(os.getpid()).memory_info().rss
    except Exception:
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        current, _ = tracemalloc.get_traced_memory()
        return int(current)


def test_rss_stability_over_many_runs(loaded_engine_instance):
    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = _shot()

    baseline = _rss_bytes()
    for _ in range(40):
        calc.integrate(shot, Distance.Yard(400), Distance.Yard(25))
        calc.find_zero_angle(shot, Distance.Yard(200))
        gc.collect()
    after = _rss_bytes()

    # Allow modest growth for allocator fragmentation; ensure it's not unbounded
    assert after - baseline < 50 * 1024 * 1024  # < 50 MiB growth


def test_cbase_traj_seq_append_and_get_at_edge_cases():
    seq = CBaseTrajSeq()
    # Append many points to exercise reallocation logic
    n = 10_000
    for i in range(n):
        t = float(i) * 0.002
        px = math.sin(i * 0.001) * 100.0 + i * 0.01
        seq.append(t, px, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7)

    # Query at ends and midpoints
    r0 = seq.get_at("time", 0.0)
    r1 = seq.get_at("time", (n - 1) * 0.002)
    rm = seq.get_at("position.x", (r0.position_vector.x + r1.position_vector.x) * 0.5)

    assert r0.time == pytest.approx(0.0)
    assert r1.time == pytest.approx((n - 1) * 0.002)
    assert r0.position_vector.x <= rm.position_vector.x <= r1.position_vector.x


def test_tracemalloc_no_python_object_leak(loaded_engine_instance):
    import tracemalloc

    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = _shot()

    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()
    for _ in range(20):
        _ = calc.integrate(shot, Distance.Yard(300), Distance.Yard(50), dense_output=True)
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()
    stats = snapshot2.compare_to(snapshot1, "filename")

    # There may be noise, but large persistent growth in our package indicates Python-level leaks.
    growth = 0
    for stat in stats:
        if "py_ballisticcalc" in stat.traceback.format() or "py_ballisticcalc_exts" in stat.traceback.format():
            growth += stat.size_diff
    assert growth < 5 * 1024 * 1024  # < 5 MiB net retained in our modules
