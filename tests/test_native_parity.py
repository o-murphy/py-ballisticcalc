"""The two native variants of the bclibc core agree: Cython (py_ballisticcalc.exts, over the bclibc C ABI) and ctypes
(py_ballisticcalc.ctypes). They are the same core behind different bindings, so every integration method must give the same
trajectory. A variant that is not installed is skipped; the test needs both.

The comparison is by field, abs tolerance 1e-9.

Documented divergences of ctypes from exts (not checked for equality here):
- ctypes is 20-45% slower than exts.
- the ctypes bclibc version check compares major.minor only.
- ctypes is pure Python: integrate_raw_at returns the core BaseTrajData, not the Cython CythonizedBaseTrajData.
"""

import math
import warnings

import pytest

from py_ballisticcalc import Ammo, Angular, Atmo, Calculator, DragModel, Shot, TableG1, TableG7, Unit, Weapon, Wind

VARIANTS = {
    "exts": ("py_ballisticcalc_exts", "cython"),
    "ctypes": ("py_ballisticcalc_ctypes", "ctypes"),
}
METHODS = ["euler", "rk4", "verlet", "rkck", "dopri", "tsitouras"]
TOLERANCE = 1e-9
FIELDS = ("time", "distance", "velocity", "mach", "height", "drop_angle", "windage")


def installed_variants():
    present = []
    for name, (module, _) in VARIANTS.items():
        try:
            __import__(module)
        except ImportError:
            continue
        present.append(name)
    return present


SHOTS = {
    "g1_wind": (
        lambda: Shot(
            weapon=Weapon(sight_height=Unit.Inch(1.5)),
            ammo=Ammo(DragModel(bc=0.759, drag_table=TableG1), mv=Unit.MPS(815)),
            atmo=Atmo.icao(),
            winds=[Wind(Unit.MPS(3), Angular.Degree(90))],
        ),
        Unit.Meter(1000),
    ),
    "g7_cold_altitude": (
        lambda: Shot(
            weapon=Weapon(sight_height=Unit.Inch(2), twist=Unit.Inch(9)),
            ammo=Ammo(DragModel(bc=0.243, drag_table=TableG7), mv=Unit.MPS(800)),
            atmo=Atmo(altitude=Unit.Meter(1500), temperature=Unit.Celsius(-20)),
            winds=[Wind(Unit.MPS(6), Angular.Degree(45))],
        ),
        Unit.Meter(1200),
    ),
}


def records(engine, make_shot, trajectory_range):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = Calculator(engine=engine).fire(make_shot(), trajectory_range=trajectory_range, extra_data=True)
        return [
            (
                float(p.time),
                p.distance >> Unit.Meter,
                p.velocity >> Unit.MPS,
                float(p.mach),
                p.height >> Unit.Meter,
                p.drop_angle >> Unit.Radian,
                p.windage >> Unit.Meter,
            )
            for p in result.trajectory
        ]


@pytest.mark.parametrize("shot_name", list(SHOTS))
@pytest.mark.parametrize("method", METHODS)
def test_variants_agree(shot_name, method):
    variants = installed_variants()
    if len(variants) < 2:
        pytest.skip("needs at least two of the native variants (exts, ctypes) installed")
    make_shot, trajectory_range = SHOTS[shot_name]
    reference_name = variants[0]
    reference = records(f"{VARIANTS[reference_name][1]}+{method}", make_shot, trajectory_range)
    for name in variants[1:]:
        other = records(f"{VARIANTS[name][1]}+{method}", make_shot, trajectory_range)
        assert len(other) == len(reference), f"{name} vs {reference_name}: {len(other)} records, {len(reference)}"
        for i, (a, b) in enumerate(zip(reference, other)):
            for field, x, y in zip(FIELDS, a, b):
                assert math.isclose(x, y, rel_tol=0.0, abs_tol=TOLERANCE), (
                    f"{name} vs {reference_name}, record {i}, {field}: {y} != {x}"
                )


def _engine(name, method):
    return Calculator(engine=f"{VARIANTS[name][1]}+{method}")._engine_instance


@pytest.mark.parametrize("method", METHODS)
def test_integration_step_count_agrees(method):
    """The step count of the last integrate() is the same in every variant: the accepted steps of an adaptive method, the
    steps taken by a fixed-step one (BCLIBCFFI_integrate_dense_shot_stats)."""
    variants = installed_variants()
    if len(variants) < 2:
        pytest.skip("needs at least two of the native variants installed")
    make_shot, trajectory_range = SHOTS["g1_wind"]
    counts = {}
    for name in variants:
        engine = _engine(name, method)
        engine.integrate(make_shot(), trajectory_range)
        counts[name] = engine.integration_step_count
    reference = variants[0]
    assert counts[reference] > 0, f"{reference}: no step count after integrate()"
    for name in variants[1:]:
        assert counts[name] == counts[reference], f"{name}: {counts[name]} steps, {reference}: {counts[reference]}"


@pytest.mark.parametrize("method", METHODS)
def test_integrate_raw_at_agrees(method):
    """The raw point at time 0.5 s and the full trajectory point at that time agree in every variant."""
    variants = installed_variants()
    if len(variants) < 2:
        pytest.skip("needs at least two of the native variants installed")
    make_shot, _ = SHOTS["g1_wind"]

    def point(name):
        raw, full = _engine(name, method).integrate_raw_at(make_shot(), "time", 0.5)
        return (
            float(raw.time),
            raw.position.x,
            raw.position.y,
            raw.position.z,
            raw.velocity.x,
            raw.velocity.y,
            raw.velocity.z,
            float(raw.mach),
            full.height >> Unit.Meter,
        )

    reference = variants[0]
    expected = point(reference)
    for name in variants[1:]:
        for field, x, y in zip(("time", "px", "py", "pz", "vx", "vy", "vz", "mach", "height"), expected, point(name)):
            assert math.isclose(x, y, rel_tol=0.0, abs_tol=TOLERANCE), f"{name} vs {reference}, {field}: {y} != {x}"


def test_integrate_raw_at_class_divergence():
    """exts returns CythonizedBaseTrajData from integrate_raw_at; ctypes is pure Python and returns BaseTrajData."""
    if len(installed_variants()) < 2:
        pytest.skip("needs the exts and ctypes variants installed")
    make_shot, _ = SHOTS["g1_wind"]
    raw_exts, _ = _engine("exts", "dopri").integrate_raw_at(make_shot(), "time", 0.5)
    raw_ctypes, _ = _engine("ctypes", "dopri").integrate_raw_at(make_shot(), "time", 0.5)
    assert type(raw_exts).__name__ == "CythonizedBaseTrajData"
    assert type(raw_ctypes).__name__ == "BaseTrajData"


def _dense(name):
    make_shot, _ = SHOTS["g1_wind"]
    return _engine(name, "dopri").integrate(make_shot(), Unit.Meter(300), dense_output=True).base_data


def _point(b):
    return (
        float(b.time),
        b.position.x,
        b.position.y,
        b.position.z,
        b.velocity.x,
        b.velocity.y,
        b.velocity.z,
        float(b.mach),
    )


@pytest.mark.parametrize("name", ["ctypes"])
def test_dense_sequence_methods_agree(name):
    """The dense sequence (base_data) of a variant: get_at, get_at_slant_height and interpolate_at give the exts values."""
    if name not in installed_variants() or "exts" not in installed_variants():
        pytest.skip("needs the exts and this variant installed")
    reference, other = _dense("exts"), _dense(name)
    assert len(other) == len(reference)
    checks = {
        "get_at_time": lambda s: s.get_at("time", 0.3),
        "get_at_start": lambda s: s.get_at("time", 0.3, 0.1),
        "slant_height": lambda s: s.get_at_slant_height(0.0, 0.5),
        "interpolate_at": lambda s: s.interpolate_at(2, "time", 0.2),
    }
    for label, call in checks.items():
        expected, actual = _point(call(reference)), _point(call(other))
        for x, y in zip(expected, actual):
            assert math.isclose(x, y, rel_tol=0.0, abs_tol=TOLERANCE), f"{name} {label}: {actual} != {expected}"


@pytest.mark.parametrize("name", ["ctypes"])
def test_dense_sequence_errors_agree(name):
    """An unknown key is an AttributeError in every variant; reserve() with a negative size is a ValueError."""
    if name not in installed_variants() or "exts" not in installed_variants():
        pytest.skip("needs the exts and this variant installed")
    for seq in (_dense("exts"), _dense(name)):
        with pytest.raises(AttributeError):
            seq.get_at("no_such_key", 0.1)
        with pytest.raises(ValueError):
            seq.reserve(-1)
