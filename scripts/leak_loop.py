"""Repeat a trajectory calculation on one engine: the workload of scripts/test-leaks-engine.sh (Linux, under Valgrind).

Usage: python scripts/leak_loop.py <engine> <iterations>
Each iteration makes a fresh Calculator and two trajectories (a G1 and a G7 shot, with a wind), so every engine allocation
path runs on every iteration.
"""

import sys
import warnings

from py_ballisticcalc import (Angular, Atmo, Calculator, DragModel, Shot, TableG1, TableG7, Unit, Ammo, Weapon, Wind)


def once(engine):
    calc = Calculator(engine=engine)
    shot = Shot(weapon=Weapon(sight_height=Unit.Inch(1.5)),
                ammo=Ammo(DragModel(bc=0.759, drag_table=TableG1), mv=Unit.MPS(815)),
                atmo=Atmo.icao(), winds=[Wind(Unit.MPS(3), Angular.Degree(90))])
    calc.fire(shot, trajectory_range=Unit.Meter(1000), extra_data=True)
    shot = Shot(weapon=Weapon(), ammo=Ammo(DragModel(bc=0.243, drag_table=TableG7), mv=Unit.MPS(800)), atmo=Atmo.icao())
    calc.fire(shot, trajectory_range=Unit.Meter(300), extra_data=True)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    engine, iterations = sys.argv[1], int(sys.argv[2])
    for _ in range(iterations):
        once(engine)
    print(f"{engine}: {iterations} iterations done")
