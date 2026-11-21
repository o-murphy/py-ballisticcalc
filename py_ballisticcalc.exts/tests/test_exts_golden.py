"""Golden test: the exts engines reproduce the records recorded from the pre-C-ABI exts (tests/data/exts_golden.json).

Records are compared at abs tolerance 1e-9; the record count (which follows the fixed step count of euler/rk4/verlet) must be
exactly equal.
"""

import json
import logging
import math
import warnings
from pathlib import Path

import pytest

from py_ballisticcalc import Ammo, Angular, Atmo, Calculator, DragModel, Shot, TableG1, TableG7, Unit, Weapon, Wind

GOLDEN = Path(__file__).resolve().parent / "data" / "exts_golden.json"
TOLERANCE = 1e-9

SHOTS = {
    "g1_wind": lambda: Shot(
        weapon=Weapon(sight_height=Unit.Inch(1.5)),
        ammo=Ammo(DragModel(bc=0.759, drag_table=TableG1), mv=Unit.MPS(815)),
        atmo=Atmo.icao(),
        winds=[Wind(Unit.MPS(3), Angular.Degree(90))],
    ),
    "g7_cold_altitude": lambda: Shot(
        weapon=Weapon(sight_height=Unit.Inch(2), twist=Unit.Inch(9)),
        ammo=Ammo(DragModel(bc=0.243, drag_table=TableG7), mv=Unit.MPS(800)),
        atmo=Atmo(altitude=Unit.Meter(1500), temperature=Unit.Celsius(-20)),
        winds=[Wind(Unit.MPS(6), Angular.Degree(45))],
    ),
    "g1_short_300m": lambda: Shot(
        weapon=Weapon(sight_height=Unit.Inch(2), twist=Unit.Inch(12)),
        ammo=Ammo(DragModel(bc=0.4, drag_table=TableG1), mv=Unit.MPS(700)),
        atmo=Atmo.icao(),
        relative_angle=Angular.Mil(1.5),
    ),
}

pytest.importorskip("py_ballisticcalc_exts")
GOLDEN_DATA = json.loads(GOLDEN.read_text())


def _records(method, shot_name):
    rng = Unit.Meter(GOLDEN_DATA["_meta"]["ranges_m"][shot_name])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.CRITICAL)
        try:
            result = Calculator(engine=f"cython+{method}").fire(SHOTS[shot_name](), trajectory_range=rng, extra_data=True)
        finally:
            logging.disable(logging.NOTSET)
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
@pytest.mark.parametrize("method", ["euler", "rk4", "verlet", "rkck", "dopri", "tsitouras"])
def test_exts_matches_golden(shot_name, method):
    fields = GOLDEN_DATA["_meta"]["fields"]
    expected = GOLDEN_DATA["shots"][shot_name][method]
    actual = _records(method, shot_name)
    assert len(actual) == len(expected), f"{len(actual)} records, golden {len(expected)}"
    worst = 0.0
    for i, (a, e) in enumerate(zip(actual, expected)):
        for field, x, y in zip(fields, a, e):
            diff = abs(x - y)
            worst = max(worst, diff)
            assert math.isclose(x, y, rel_tol=0.0, abs_tol=TOLERANCE), f"record {i}, {field}: {x} != golden {y} (diff {diff:g})"
