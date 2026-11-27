"""A vacuum is drag-free flight, not an error.

``Atmo.get_density_and_mach_for_altitude`` scaled the density ratio by ``p / p0`` away from the base altitude, so a
`Vacuum` (base pressure ``p0 = 0``) raised ``ZeroDivisionError`` as soon as the shot was 30 ft or more from the muzzle
altitude (closer than that the cached values are used).  The density ratio of a vacuum is 0 at every altitude, and the speed
of sound stays finite (it depends on temperature only).

The CIPM density formula divided by the pressure too, so ``Atmo(pressure=Pressure.hPa(0))`` raised on construction; it now
yields density 0. A plain ``pressure=0`` is a vacuum too (``None`` is what means "default"; ``0`` is a value, not a missing argument).
"""

import math

import pytest

from py_ballisticcalc import Atmo, BaseEngineConfigDict, Calculator, Vacuum
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

G = 32.17405  # ft/s^2, cGravityImperial
V0 = 1000.0  # fps
ANGLE_DEG = 30.0
VX = V0 * math.cos(math.radians(ANGLE_DEG))
VY = V0 * math.sin(math.radians(ANGLE_DEG))
APEX_FT = VY**2 / (2 * G)  # ~ 777 ft, far beyond the 30 ft fast path of the atmosphere lookup
APEX_X_FT = VX * VY / G

# Flight vs the closed-form parabola, ft: exact integrators vs the finite-step Euler/Verlet limit.
# The adaptive engines (CashKarp, DormandPrince, Tsitouras, SciPy) and the native tiny_bclibc engine are held to the
# same 1e-3 ft as RK4 (the bclibc C++ vacuum test uses 1e-3 ft for rk4/verlet/adaptive); the dry run passed
# every one of these tests on all of them at that tolerance.
TOL_FT = {
    "RK4": 1e-3,
    "SciPy": 1e-3,
    "CashKarp": 1e-3,
    "DormandPrince": 1e-3,
    "Tsitouras": 1e-3,
    "TinyBclibc": 1e-3,
    "Euler": 0.5,
    "Verlet": 5e-2,
}


def _skip_if_native(engine):
    if engine.__module__.startswith("tiny_bclibc"):
        pytest.skip("tiny_bclibc vacuum is not covered here (revisit separately)")


def _family(engine) -> str:
    # SciPy first: "SciPyRK45IntegrationEngine" also contains "RK4".
    for key in ("SciPy", *TOL_FT):
        if key in engine.__name__:
            return key
    raise AssertionError(
        f"no vacuum tolerance for engine class {engine.__name__!r}: add its family to TOL_FT in tests/test_vacuum.py"
    )


def _shot(angle_deg: float = ANGLE_DEG, v0: float = V0) -> Shot:
    dm = DragModel(0.31, TableG7)
    return Shot(
        weapon=Weapon(sight_height=Distance.Foot(0)),
        ammo=Ammo(dm, Velocity.FPS(v0)),
        atmo=Vacuum(),
        relative_angle=Angular.Degree(angle_deg),
    )


def _calc(engine) -> Calculator:
    return Calculator(config=BaseEngineConfigDict(cMinimumVelocity=0), engine=engine)


def test_vacuum_construction():
    """`Vacuum` has zero density at all altitudes and a finite speed of sound; so has `Atmo(pressure=0)`."""
    from py_ballisticcalc import Atmo

    vac = Vacuum()
    for alt in (0.0, 29.0, 31.0, 1000.0, 20000.0, -500.0):
        density, mach = vac.get_density_and_mach_for_altitude(alt)
        assert density == 0.0
        assert math.isfinite(mach) and mach > 0
    # A zero Pressure object is a vacuum request too (it used to raise ZeroDivisionError in the CIPM density formula)...
    zero_p = Atmo(pressure=Pressure.hPa(0), humidity=50)
    assert zero_p.density_ratio == 0.0
    assert zero_p.get_density_and_mach_for_altitude(5000.0)[0] == 0.0
    # ...and so is a plain 0 (it used to be silently replaced by the standard pressure).
    for atmo in (Atmo(pressure=0), Atmo(pressure=0.0, humidity=50), Atmo(altitude=Distance.Meter(1000), pressure=0)):
        assert atmo.density_ratio == 0.0
        assert atmo._p0 == 0.0
        assert (atmo.pressure >> Pressure.hPa) == 0.0
        for alt in (0.0, 31.0, 20000.0):
            density, mach = atmo.get_density_and_mach_for_altitude(alt)
            assert density == 0.0
            assert math.isfinite(mach) and mach > 0
    # None still means "standard pressure".
    assert Atmo(pressure=None).density_ratio > 0.9


def test_zero_arguments_are_values_not_defaults():
    """A plain 0 for temperature / powder temperature is 0 in the preferred unit; only `None` selects the default."""
    std_t = Atmo.standard_temperature(Distance.Foot(0))
    t0 = Atmo(temperature=0)
    assert (t0.temperature >> PreferredUnits.temperature) == 0.0
    assert t0.temperature != std_t
    assert t0._t0 == pytest.approx(Temperature.Fahrenheit(0) >> Temperature.Celsius)
    assert (Atmo(altitude=Distance.Meter(2000), temperature=0).temperature >> PreferredUnits.temperature) == 0.0
    assert (Atmo(temperature=None).temperature >> Temperature.Celsius) == pytest.approx(std_t >> Temperature.Celsius)
    # Powder temperature: 0 is 0, None follows the ambient temperature.
    assert (Atmo(temperature=Temperature.Celsius(20), powder_t=0).powder_temp >> PreferredUnits.temperature) == 0.0
    warm = Atmo(temperature=Temperature.Celsius(20), powder_t=None)
    assert warm.powder_temp == warm.temperature
    # Ammo: a plain 0 powder temperature is 0 in the preferred unit; None is the 15 C default.
    dm = DragModel(0.31, TableG7)
    assert (Ammo(dm, Velocity.FPS(800), powder_temp=0).powder_temp >> PreferredUnits.temperature) == 0.0
    assert Ammo(dm, Velocity.FPS(800)).powder_temp >> Temperature.Celsius == pytest.approx(15)
    # Same for the ICAO factory
    assert (Atmo.icao(temperature=0).temperature >> PreferredUnits.temperature) == 0.0
    # Humidity 0 is 0 (that default was already explicit).
    assert Atmo(humidity=0).humidity == 0.0
    # altitude 0 is sea level, with or without None
    assert Atmo(altitude=0).altitude == Atmo(altitude=None).altitude


@pytest.mark.parametrize("make", [lambda: Atmo(pressure=0), lambda: Atmo(pressure=Pressure.hPa(0)), Vacuum])
def test_zero_pressure_is_the_same_vacuum(make):
    ref = Vacuum()
    atmo = make()
    assert atmo.density_ratio == ref.density_ratio == 0.0
    assert atmo.mach >> Velocity.FPS == pytest.approx(ref.mach >> Velocity.FPS)


def test_vacuum_trajectory_is_parabola(loaded_engine_instance):
    _skip_if_native(loaded_engine_instance)
    calc = _calc(loaded_engine_instance)
    tol = TOL_FT[_family(loaded_engine_instance)]
    hit = calc.fire(_shot(), Distance.Foot(20000), trajectory_step=Distance.Foot(2000), raise_range_error=False)
    rows = hit.trajectory
    assert len(rows) >= 10
    assert max(r.height >> Distance.Foot for r in rows) > 30  # really leaves the fast path
    for r in rows:
        x = r.distance >> Distance.Foot
        y = r.height >> Distance.Foot
        assert math.isfinite(y) and math.isfinite(r.time)
        expected = x * VY / VX - G * x**2 / (2 * VX**2)
        assert y == pytest.approx(expected, abs=tol), f"x={x}"
        assert r.time == pytest.approx(x / VX, abs=tol / VX + 1e-4)


def test_vacuum_integrate_finite_rows(loaded_engine_instance):
    _skip_if_native(loaded_engine_instance)
    calc = _calc(loaded_engine_instance)
    tol = TOL_FT[_family(loaded_engine_instance)]
    hit = calc.fire(_shot(), Distance.Foot(20000), time_step=1.0, raise_range_error=False)
    assert hit.trajectory
    for r in hit.trajectory:
        t = r.time
        x = r.distance >> Distance.Foot
        y = r.height >> Distance.Foot
        assert all(math.isfinite(v) for v in (x, y, t))
        assert x == pytest.approx(VX * t, abs=tol + 1e-3)
        assert y == pytest.approx(VY * t - G * t * t / 2, abs=tol)


def test_vacuum_find_apex(loaded_engine_instance):
    _skip_if_native(loaded_engine_instance)
    apex = _calc(loaded_engine_instance).find_apex(_shot())
    tol = TOL_FT[_family(loaded_engine_instance)]
    assert apex.height >> Distance.Foot == pytest.approx(APEX_FT, abs=max(tol, 1e-2))
    assert apex.time == pytest.approx(VY / G, abs=1e-2)


@pytest.mark.slow
def test_vacuum_find_max_range(loaded_engine_instance):
    _skip_if_native(loaded_engine_instance)
    calc = _calc(loaded_engine_instance)
    shot = _shot(0.0)
    max_range, angle = calc.find_max_range(shot)
    assert (angle >> Angular.Degree) == pytest.approx(45.0, abs=0.1)
    assert max_range >> Distance.Foot == pytest.approx(V0**2 / G, rel=2e-3)


def test_vacuum_zero_angle_hits_300_m(loaded_engine_instance):
    _skip_if_native(loaded_engine_instance)
    calc = _calc(loaded_engine_instance)
    shot = _shot(0.0)
    target = Distance.Meter(300)
    angle = calc.set_weapon_zero(shot, target)
    expected = 0.5 * math.asin(G * (target >> Distance.Foot) / V0**2)
    assert angle >> Angular.Radian == pytest.approx(expected, rel=2e-3)
    # Physical check: fire with that elevation and read the height at the target.
    hit = calc.fire(shot, target, trajectory_step=target)
    assert hit.trajectory[-1].height >> Distance.Foot == pytest.approx(0.0, abs=0.05)


def test_atmo_zero_pressure_flies_like_vacuum(loaded_engine_instance):
    """`Atmo(pressure=0)` (a plain number) is the same drag-free flight as `Vacuum()`."""
    _skip_if_native(loaded_engine_instance)
    calc = _calc(loaded_engine_instance)
    shot = _shot()
    shot.atmo = Atmo(pressure=0)
    apex = calc.find_apex(shot)
    tol = TOL_FT[_family(loaded_engine_instance)]
    assert (apex.height >> Distance.Foot) == pytest.approx(APEX_FT, abs=tol)
