"""The three native variants of the bclibc core agree: Cython (py_ballisticcalc.exts), the C ABI in Cython (py_ballisticcalc.cabi)
and ctypes (py_ballisticcalc.ctypes). They are the same C++ core behind different bindings, so every integration method must give
the same trajectory. A variant that is not installed is skipped; the test needs at least two of them.

The comparison is by field, abs tolerance 1e-9 (the same core compiled with -ffp-contract=off gives identical numbers).
"""

import math
import warnings

import pytest

from py_ballisticcalc import Ammo, Angular, Atmo, Calculator, DragModel, Shot, TableG1, TableG7, Unit, Weapon, Wind

VARIANTS = {
    "exts": ("py_ballisticcalc_exts", "cython"),
    "cabi": ("py_ballisticcalc_cabi", "cabi"),
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
        pytest.skip("needs at least two of the native variants (exts, cabi, ctypes) installed")
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


ADAPTIVE = ["rkck", "dopri", "tsitouras"]
FIXED = ["euler", "rk4", "verlet"]


def _engine(name, method):
    return Calculator(engine=f"{VARIANTS[name][1]}+{method}")._engine_instance


@pytest.mark.parametrize("method", ADAPTIVE)
def test_integration_step_count_agrees(method):
    """The adaptive methods: the step count of the last integrate() is the accepted steps, the same in every variant."""
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
    for name in variants[1:]:
        assert counts[name] == counts[reference], f"{name}: {counts[name]} steps, {reference}: {counts[reference]}"


@pytest.mark.parametrize("method", FIXED)
def test_fixed_step_count_is_reported_by_exts_only(method):
    """Known gap: the C ABI reports no step count for a fixed-step integration, so cabi and ctypes raise NotImplementedError
    where the exts engine returns its counter. The test fails when the gap is closed, to be updated then."""
    if "exts" not in installed_variants():
        pytest.skip("the exts variant is the reference of the step count")
    make_shot, trajectory_range = SHOTS["g1_wind"]
    engine = _engine("exts", method)
    engine.integrate(make_shot(), trajectory_range)
    assert engine.integration_step_count > 0
    for name in installed_variants():
        if name == "exts":
            continue
        engine = _engine(name, method)
        engine.integrate(make_shot(), trajectory_range)
        with pytest.raises(NotImplementedError):
            _ = engine.integration_step_count


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


def test_integrate_raw_at_class_is_the_exts_class():
    """cabi returns the exts class CythonizedBaseTrajData from integrate_raw_at. ctypes is pure Python and returns the core
    BaseTrajData (no Cython class is available there), so it is not compared by class."""
    if "exts" not in installed_variants() or "cabi" not in installed_variants():
        pytest.skip("needs the exts and cabi variants installed")
    make_shot, _ = SHOTS["g1_wind"]
    raw_exts, _ = _engine("exts", "dopri").integrate_raw_at(make_shot(), "time", 0.5)
    raw_cabi, _ = _engine("cabi", "dopri").integrate_raw_at(make_shot(), "time", 0.5)
    assert type(raw_cabi).__name__ == type(raw_exts).__name__ == "CythonizedBaseTrajData"
