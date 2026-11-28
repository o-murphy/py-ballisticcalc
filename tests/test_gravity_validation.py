"""cGravityConstant must be a finite negative number (acceleration along -y, ft/s^2).

Zero or positive gravity made the pure-Python engines fail deep inside with "math domain error" and the C++ core of
the cythonized engines loop forever, so the sign is validated up front (config construction and every later change of
the config field), the same way for all engines.
"""

import math
import os
import subprocess
import sys
import textwrap

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.engines.base_engine import BaseEngineConfig, create_base_engine_config
from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import Distance, Velocity

BAD_VALUES = [0.0, 32.17405, 1e-9, math.nan, math.inf, -math.inf]
MOON_FPS2 = -1.62 / 0.3048  # Moon surface gravity in ft/s^2 (negative: pointing down)
MATCH = r"cGravityConstant must be a finite negative number"
ENGINES = ["rk4_engine", "euler_engine", "scipy_engine", "cythonized_rk4_engine", "cythonized_euler_engine"]


# No subprocesses: Pyodide and iOS have none, and on Android sys.executable is "" (see .github/scripts/cibw_run_engines.py)
NO_SUBPROCESS = sys.platform in ("emscripten", "ios", "android")


def _load(name):
    if name == "scipy_engine":  # the engine loads without SciPy/NumPy and fails on construction ("Numpy is required")
        pytest.importorskip("numpy", exc_type=ImportError)
        pytest.importorskip("scipy", exc_type=ImportError)
    try:
        return _EngineLoader.load(name)
    except Exception as e:  # noqa: BLE001 - engine not installed
        pytest.skip(f"{name} not available: {e}")


def _shot():
    return Shot(weapon=Weapon(sight_height=Distance.Inch(2)), ammo=Ammo(DragModel(0.3, TableG7), Velocity.FPS(2800)))


@pytest.mark.parametrize("value", BAD_VALUES)
def test_config_rejects_bad_gravity(value):
    with pytest.raises(ValueError, match=MATCH):
        create_base_engine_config({"cGravityConstant": value})
    with pytest.raises(ValueError, match=MATCH):
        BaseEngineConfig(cGravityConstant=value)


@pytest.mark.parametrize("value", BAD_VALUES)
def test_config_rejects_later_change(value):
    config = BaseEngineConfig()
    with pytest.raises(ValueError, match=MATCH):
        config.cGravityConstant = value
    assert config.cGravityConstant < 0  # unchanged


def test_message_states_convention_and_value():
    with pytest.raises(ValueError, match=r"ft/s.*got 5\.0"):
        create_base_engine_config({"cGravityConstant": 5.0})


@pytest.mark.parametrize("engine_name", ENGINES)
@pytest.mark.parametrize("value", BAD_VALUES)
def test_engine_rejects_bad_gravity_at_construction(engine_name, value):
    engine = _load(engine_name)
    with pytest.raises(ValueError, match=MATCH):
        engine({"cGravityConstant": value})


@pytest.mark.parametrize("engine_name", ENGINES)
def test_engine_rejects_gravity_changed_after_construction(engine_name):
    engine = engine_name and _load(engine_name)({})
    with pytest.raises(ValueError, match=MATCH):
        engine._config.cGravityConstant = 0.0


@pytest.mark.parametrize(
    "engine_name", ["rk4_engine", "scipy_engine", "cythonized_rk4_engine", "cythonized_euler_engine"]
)
def test_default_and_moon_gravity_work(engine_name):
    engine = _load(engine_name)
    earth = Calculator(engine=engine).fire(_shot(), Distance.Yard(300))
    moon = Calculator(engine=engine, config={"cGravityConstant": MOON_FPS2}).fire(_shot(), Distance.Yard(300))
    assert earth[-1].distance >> Distance.Yard == pytest.approx(300, abs=1)
    assert moon[-1].distance >> Distance.Yard == pytest.approx(300, abs=1)
    # Less gravity, less drop (the height is negative)
    assert (moon[-1].height >> Distance.Inch) > (earth[-1].height >> Distance.Inch)


@pytest.mark.skipif(NO_SUBPROCESS, reason="no subprocesses on this platform (Pyodide, iOS, Android)")
@pytest.mark.parametrize("engine_name", ["cythonized_rk4_engine", "cythonized_euler_engine"])
def test_cythonized_does_not_hang(engine_name):
    """A subprocess with a timeout, so a regression (infinite loop in C++) fails instead of blocking the suite."""
    code = textwrap.dedent(f"""
        from py_ballisticcalc.interface import _EngineLoader
        eng = _EngineLoader.load("{engine_name}")
        try:
            eng({{"cGravityConstant": 0.0}})
        except ValueError as e:
            assert "cGravityConstant must be a finite negative number" in str(e), e
            raise SystemExit(0)
        raise SystemExit(3)
    """)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    try:
        r = subprocess.run(
            [sys.executable, "-c", code], check=False, capture_output=True, text=True, timeout=60, env=env
        )
    except subprocess.TimeoutExpired:
        pytest.fail("cythonized engine hung on gravity == 0")
    if r.returncode == 1 and "No module" in r.stderr:
        pytest.skip("cythonized engines not importable in isolated subprocess")
    assert r.returncode == 0, r.stderr
