"""Example: zero, aim and fire through tiny_bclibc running as WebAssembly.

Runs as-is on a desktop (wasmtime, wasm3, Node or WebKitGTK JavaScriptCore, whichever the
`tiny_bclibc` package finds) and in Pythonista on iOS (JavaScriptCore's JSContext).

Desktop, from the repo root:
    uv pip install tiny-bclibc-wasm-py wasmtime     # compiles the .wasm modules; wasmtime is optional
    python examples/tiny_bclibc_wasm/run_example.py
    TINY_BCLIBC_HOST=node python examples/tiny_bclibc_wasm/run_example.py    # pick the host yourself

Pythonista: copy these next to each other into Pythonista's files, then run this script:
    py_ballisticcalc/                    (the package; needs typing_extensions importable too)
    tiny_bclibc/                         (from the tiny-bclibc-wasm-py wheel, with its .wasm files)
    tiny_bclibc_wasm/                    (this directory)
"""

import os
import sys
import time

# Make `tiny_bclibc_wasm` importable as a package when this file is run directly as a script
# (Pythonista's run button, or `python .../run_example.py`), not only via `python -m`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from py_ballisticcalc import Ammo, Calculator, DragModel, Shot, TableG7, Unit, Weapon, Wind
from tiny_bclibc_wasm import TinyBclibcWasmDoubleIntegrationEngine


def main() -> None:
    dm = DragModel(bc=0.310, drag_table=TableG7, weight=Unit.Grain(168), diameter=Unit.Inch(0.308))
    ammo = Ammo(dm=dm, mv=Unit.FPS(2750))
    weapon = Weapon(sight_height=Unit.Inch(1.5), twist=Unit.Inch(11))

    t0 = time.perf_counter()
    calc = Calculator(engine=TinyBclibcWasmDoubleIntegrationEngine)
    shot = Shot(ammo=ammo, weapon=weapon, winds=[Wind(Unit.MPS(3), Unit.Degree(90))])
    calc.set_weapon_zero(shot, Unit.Meter(100))
    t1 = time.perf_counter()
    hold, windage, aim_point = calc.aim(shot, Unit.Meter(300))
    hit = calc.fire(shot, trajectory_range=Unit.Meter(1000), trajectory_step=Unit.Meter(100))
    t2 = time.perf_counter()

    print(f"load + zero: {(t1 - t0) * 1000:.1f} ms, aim + fire: {(t2 - t1) * 1000:.1f} ms")
    print(
        f"aim @ 300 m: hold={hold >> Unit.Mil:+.2f} mil  windage={windage >> Unit.Mil:+.2f} mil  "
        f"velocity={aim_point.velocity >> Unit.MPS:.1f} m/s"
    )
    for row in hit.samples:
        print(
            f"{row.distance >> Unit.Meter:6.0f} m  {row.velocity >> Unit.MPS:7.1f} m/s  "
            f"drop={row.height >> Unit.Centimeter:8.1f} cm  wind={row.windage >> Unit.Centimeter:7.1f} cm"
        )


if __name__ == "__main__":
    main()
