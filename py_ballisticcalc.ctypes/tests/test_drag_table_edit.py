"""A drag table edited in place between two calls of one engine is seen by the next call, as the Cython engines see it.

The engine keeps the curve built for the drag table of the previous call. It used to take the same list object (with the same first and
last point and length) for the same table, so an edit of a middle point on the spot was not seen: the second call returned the result
of the old table, while a fresh engine, and the Cython engine, returned that of the new one.
"""

import pytest

from py_ballisticcalc import Ammo, Calculator, DragDataPoint, DragModel, Distance, Shot, TableG7, Velocity, Weight

native = pytest.importorskip("py_ballisticcalc_ctypes._native")

ENGINES = [
    getattr(native, name)
    for name in (
        "NativeEulerIntegrationEngine",
        "NativeRK4IntegrationEngine",
        "NativeVelocityVerletIntegrationEngine",
        "NativeCashKarpIntegrationEngine",
        "NativeDormandPrinceIntegrationEngine",
        "NativeTsitourasIntegrationEngine",
    )
]


@pytest.fixture(scope="module", autouse=True)
def _library():
    """The engines need the bclibc_ffi library, which a checkout that was not built does not have: skip, do not fail."""
    try:
        native._load_library()
    except (ImportError, OSError) as exc:
        pytest.skip(f"the bclibc_ffi library is not built here: {exc}")


def _shot(table):
    dm = DragModel(
        bc=0.151,
        drag_table=table,
        weight=Weight.Grain(62),
        diameter=Distance.Millimeter(5.56),
        length=Distance.Millimeter(21.0),
    )
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(900))), dm


def _speed(engine, shot):
    result = engine.integrate(shot, Distance.Meter(400), Distance.Meter(400))
    return result.records[-1].velocity.raw_value


def _fresh(cls):
    return Calculator(engine=cls)._engine_instance


@pytest.mark.parametrize(
    "cls", ENGINES, ids=lambda cls: cls.__name__.removeprefix("Native").removesuffix("IntegrationEngine")
)
@pytest.mark.parametrize("which", ["standard G7 table", "custom table"])
def test_an_edit_of_a_middle_point_is_seen(cls, which):
    table = TableG7 if which == "standard G7 table" else [DragDataPoint(p["Mach"], p["CD"] * 1.05) for p in TableG7]
    shot, dm = _shot(table)
    engine = _fresh(cls)
    before = _speed(engine, shot)

    middle = len(dm.drag_table) // 2
    point = dm.drag_table[middle]
    dm.drag_table[middle] = DragDataPoint(point.Mach, point.CD * 3)  # in place, not the first or the last point

    after = _speed(engine, shot)
    assert after == _speed(_fresh(cls), shot)  # what an engine that never saw the old table gets
    assert after != before  # the edit changed the result, so the test can tell a stale curve


def test_an_unchanged_table_gives_the_same_result():
    shot, _ = _shot(TableG7)
    engine = _fresh(ENGINES[1])
    assert _speed(engine, shot) == _speed(engine, shot)
