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
