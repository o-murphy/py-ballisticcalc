"""Example: run a trajectory through the tiny_bclibc single- and double-precision engines.

Prerequisite: build the shared libraries and point the env vars at them.
    cd examples/tiny_bclibc
    ./build_tiny_bclibc.sh                 # single precision
    ./build_tiny_bclibc.sh bclibc double    # double precision
    export PYBALLISTICCALC_TINY_BCLIBC_LIB=$(pwd)/bclibc/tiny_bclibc/build/libtiny_bclibc.so
    export PYBALLISTICCALC_TINY_BCLIBC_DP_LIB=$(pwd)/bclibc/tiny_bclibc/build_double/libtiny_bclibc.so

Then, from the `examples` directory (this is a package, run with `-m` so the relative
imports in sp.py/dp.py/_common.py resolve):
    cd ..
    python -m tiny_bclibc.run_example
"""

from py_ballisticcalc import Ammo, Calculator, DragModel, Shot, TableG7, Unit, Weapon

from tiny_bclibc.dp import TinyBclibcDoubleIntegrationEngine
from tiny_bclibc.sp import TinyBclibcSingleIntegrationEngine


def main() -> None:
    dm = DragModel(bc=0.310, drag_table=TableG7, weight=Unit.Grain(168), diameter=Unit.Inch(0.308))
    ammo = Ammo(dm=dm, mv=Unit.FPS(2750))
    weapon = Weapon(sight_height=Unit.Inch(1.5))

    for engine, label in (
        ("rk4_engine", "rk4_engine (Python, double)"),
        (TinyBclibcDoubleIntegrationEngine, "tiny_bclibc (double)"),
        (TinyBclibcSingleIntegrationEngine, "tiny_bclibc (single)"),
    ):
        calc = Calculator(engine=engine)
        shot = Shot(ammo=ammo, weapon=weapon)
        calc.set_weapon_zero(shot, Unit.Meter(100))
        hit = calc.fire(shot, trajectory_range=Unit.Meter(300), trajectory_step=Unit.Meter(50))
        print(f"\n{label}:")
        for row in hit.trajectory:
            print(
                f"  {row.distance >> Unit.Meter:6.1f} m  "
                f"{row.velocity >> Unit.FPS:8.2f} fps  "
                f"drop={row.height >> Unit.Centimeter:8.3f} cm"
            )


if __name__ == "__main__":
    main()
