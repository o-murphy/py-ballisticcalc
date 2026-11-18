"""The ctypes engines read result structures through their bytes, not through the buffer interface of the ctypes structure.

CPython's ctypes structures export the buffer interface, so ``struct.unpack_from(structure)`` works there. The
structures of PyPy 8.0 do not (its buffer protocol was refactored in that release): ``find_apex``, ``zero_point`` and
``find_zero_point`` of the ctypes engines failed on ``pypy3.11`` with ``TypeError: a bytes-like object is required, not
struct_BCLIBCFFI_TrajectoryData``, while the same code passed on CPython and on PyPy 7.3.

These tests run the paths that read one structure with a ``struct.Struct`` that, like those interpreters, refuses
everything but bytes-like objects, so the mistake fails on every interpreter, not only on the one that shows it. Every
ctypes engine is run (``pytest py_ballisticcalc.ctypes/tests``).
"""

import ctypes

import pytest

from py_ballisticcalc import Angular, Calculator, DragModel, Distance, Ammo, Shot, TableG7, Velocity, Weight

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


def create_5_56_mm_shot():
    """5.56x45mm NATO SS109"""
    dm = DragModel(
        bc=0.151,
        drag_table=TableG7,
        weight=Weight.Grain(62),
        diameter=Distance.Millimeter(5.56),
        length=Distance.Millimeter(21.0),
    )
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(900)))


@pytest.fixture(scope="module", autouse=True)
def _library():
    """The engines need the bclibc_ffi library, which a checkout that was not built does not have: skip, do not fail."""
    try:
        native._load_library()
    except (ImportError, OSError) as exc:
        pytest.skip(f"the bclibc_ffi library is not built here: {exc}")


class _BytesOnlyStruct:
    """A struct.Struct that, like ``unpack_from`` on a ctypes structure of PyPy 8.0, takes bytes-like objects only."""

    def __init__(self, real):
        self._real = real
        self.size = real.size
        self.format = real.format

    def unpack_from(self, buffer, offset=0):
        if not isinstance(buffer, (bytes, bytearray, memoryview)):
            raise TypeError(f"a bytes-like object is required, not {type(buffer).__name__}")
        return self._real.unpack_from(buffer, offset)

    def iter_unpack(self, buffer):
        return self._real.iter_unpack(buffer)


@pytest.fixture(params=ENGINES, ids=lambda cls: cls.__name__.removeprefix("Native").removesuffix("IntegrationEngine"))
def engine(request, monkeypatch):
    """An instance of each ctypes engine, with the bytes-only reader."""
    monkeypatch.setattr(native, "_TRAJ_FMT", _BytesOnlyStruct(native._TRAJ_FMT))
    return Calculator(engine=request.param)._engine_instance


def test_the_reader_of_the_test_is_strict():
    """The substitute does what it is for: a ctypes structure is not accepted, its bytes are."""
    strict = _BytesOnlyStruct(native._TRAJ_FMT)
    record = ctypes.create_string_buffer(strict.size)
    with pytest.raises(TypeError, match="bytes-like object is required"):
        strict.unpack_from(ctypes.c_double())
    assert len(strict.unpack_from(record.raw)) == 16


def test_find_apex(engine):
    apex = engine.find_apex(_shot_with_elevation())
    assert apex.time > 0
    assert (apex.height >> Distance.Meter) > 0


def test_zero_point(engine):
    angle, point = engine.zero_point(create_5_56_mm_shot(), Distance.Yard(200))
    assert (point.distance >> Distance.Yard) == pytest.approx(200, abs=0.5)
    assert angle.raw_value > 0


@pytest.mark.parametrize("lofted", [False, True])
def test_find_zero_point(engine, lofted):
    angle, point = engine.find_zero_point(create_5_56_mm_shot(), Distance.Yard(200), lofted=lofted)
    assert (point.distance >> Distance.Yard) == pytest.approx(200, abs=0.5)
    assert angle.raw_value > 0


def test_integrate_raw_at(engine):
    raw, full = engine.integrate_raw_at(create_5_56_mm_shot(), "time", 0.2)
    assert raw.time == pytest.approx(0.2)
    assert full.time == pytest.approx(0.2)


def test_integrate_records(engine):
    """The many-records path reads a copy of the array through the same reader."""
    result = engine.integrate(create_5_56_mm_shot(), Distance.Meter(300), Distance.Meter(100))
    assert len(result.trajectory) >= 3


def _shot_with_elevation():
    shot = create_5_56_mm_shot()
    shot.relative_angle = Angular.Degree(5)
    return shot
