"""Example: run a trajectory through the tiny_bclibc single- and double-precision engines.

Prerequisite: build the shared libraries (from the repo root) and point the env vars at them.
    git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc
    cmake -B examples/tiny_bclibc_ctypes/build -S examples/tiny_bclibc_ctypes
    cmake --build examples/tiny_bclibc_ctypes/build
    export PYBALLISTICCALC_TINY_BCLIBC_LIB=$(pwd)/examples/tiny_bclibc_ctypes/build/single/libtiny_bclibc.so
    export PYBALLISTICCALC_TINY_BCLIBC_DP_LIB=$(pwd)/examples/tiny_bclibc_ctypes/build/double/libtiny_bclibc.so

Then, from the `examples` directory (this is a package, run with `-m` so the relative
imports in __init__.py/_common.py resolve):
    cd examples
    python -m tiny_bclibc_ctypes.run_example
"""

from py_ballisticcalc import Ammo, Calculator, DragModel, Shot, TableG7, Unit, Weapon

from tiny_bclibc_ctypes import TinyBclibcDoubleIntegrationEngine, TinyBclibcSingleIntegrationEngine


def main() -> None:
    dm = DragModel(bc=0.310, drag_table=TableG7, weight=Unit.Grain(168), diameter=Unit.Inch(0.308))
    ammo = Ammo(dm=dm, mv=Unit.FPS(2750))
    weapon = Weapon(sight_height=Unit.Inch(1.5))

    for engine, label in (
        ("python.rk4", "python.rk4 (Python, double)"),
        (TinyBclibcDoubleIntegrationEngine, "tiny_bclibc (double)"),
        (TinyBclibcSingleIntegrationEngine, "tiny_bclibc (single)"),
    ):
        calc = Calculator(engine=engine)
        shot = Shot(ammo=ammo, weapon=weapon)
        calc.set_weapon_zero(shot, Unit.Meter(100))
        hold, windage, aim_point = calc.aim(shot, Unit.Meter(300))
        hit = calc.fire(shot, trajectory_range=Unit.Meter(300), trajectory_step=Unit.Meter(50))
        print(f"\n{label}:")
        print(
            f"  aim @ 300 m: hold={hold >> Unit.MOA:+.3f} moa  "
            f"windage={windage >> Unit.MOA:+.3f} moa  "
            f"velocity={aim_point.velocity >> Unit.FPS:.2f} fps"
        )
        for row in hit.trajectory:
            print(
                f"  {row.distance >> Unit.Meter:6.1f} m  "
                f"{row.velocity >> Unit.FPS:8.2f} fps  "
                f"drop={row.height >> Unit.Centimeter:8.3f} cm"
            )


if __name__ == "__main__":
    main()
