"""Unit test for zero finding in ballistic calculator."""
# mypy: ignore - mypy overhead is not worth it for test code
import pytest

from py_ballisticcalc.unit import *
from py_ballisticcalc import (
    Atmo,
    Calculator,
    SciPyEngineConfigDict,
    BaseEngineConfigDict,
    RangeError,
    HitResult,
    DragModel,
    TableG1,
    Ammo,
    Weapon,
    Shot,
)
from py_ballisticcalc.trajectory_data import TrajFlag

DISTANCES_FOR_CHECKING = (
    # list(range(100, 1000, 100)) +
    # list(range(1000, 3000, 1000)) +
    # list(range(3000, 4000, 100)) +
    # list(range(4000, 7000, 500)) +
    # list(range(6600, 7100, 100)) +
    [7126.05]
)

def create_zero_velocity_zero_min_altitude_calc(engine_name, method, max_iteration:int=60):
    config = SciPyEngineConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=0,
        integration_method=method,
        cMaxIterations=max_iteration
    )
    return Calculator(config, engine=engine_name)

@pytest.fixture(scope="session")
def scipy_calc():
    return create_zero_velocity_zero_min_altitude_calc("scipy_engine", "RK45")

def create_23_mm_shot():
    drag_model = DragModel(
        bc=0.759,
        drag_table=TableG1,
        weight=Weight.Gram(108),
        diameter=Distance.Millimeter(23),
        length=Distance.Millimeter(108.2),
    )
    ammo = Ammo(drag_model, Velocity.MPS(930))
    gun = Weapon()
    shot = Shot(
        weapon=gun,
        ammo=ammo,
    )
    return shot


def create_7_62_mm_shot():
    diameter = Distance.Millimeter(7.62)
    length: Distance = Distance.Millimeter(32.5628)
    weight = Weight.Grain(180)
    dm = DragModel(bc=0.2860,
                   drag_table=TableG1,
                   weight=weight,
                   diameter=diameter,
                   length=length)
    ammo = Ammo(dm, mv=Velocity.MPS(800), powder_temp=Temperature.Celsius(20), use_powder_sensitivity=False)
    ammo.calc_powder_sens(other_velocity=Velocity.MPS(805), other_temperature=Temperature.Celsius(15))
    current_atmo = Atmo(altitude=Distance.Meter(400), pressure=Pressure.hPa(967.24), temperature=Temperature.Celsius(20),
                        humidity=60)
    gun = Weapon(sight_height=Distance.Millimeter(-100), twist=Distance.Millimeter(300))
    return Shot(weapon=gun, ammo=ammo, atmo=current_atmo)


@pytest.mark.parametrize("distance", DISTANCES_FOR_CHECKING)
def test_set_weapon_zero(distance, loaded_engine_instance):
    shot = create_23_mm_shot()
    config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    calc.set_weapon_zero(shot, Distance.Meter(distance))
    print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree}")
    hit_result = calc.fire(shot, Distance.Meter(distance))
    # print(
    #     f"{hit_result[-1].distance >> Distance.Meter=} "
    #     f"{hit_result[-1].time=} "
    #     f"{hit_result[-1].velocity >> Velocity.MPS=}"
    # )
    assert abs(hit_result[-1].height.raw_value) < 1e+1


def test_zero_with_look_angle(loaded_engine_instance):
    """Test zero finding with a high look angle."""
    distance = Distance.Meter(1000)
    shot = create_23_mm_shot()
    shot.look_angle = Angular.Degree(30)
    config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    calc.set_weapon_zero(shot, distance)
    print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree} degrees")
    hit_result = calc.fire(shot, trajectory_range=distance, extra_data=True)
    # TrajFlag.ZERO_DOWN marks the point at which bullet crosses down through sight line
    assert abs(hit_result.flag(TrajFlag.ZERO_DOWN).look_distance.raw_value - distance.raw_value) < 1e+1


def test_vertical_shot_zero(loaded_engine_instance):
    """Test zero finding for a vertical shot."""
    distance = Distance.Meter(1000)
    shot = create_23_mm_shot()
    shot.look_angle = Angular.Degree(90)
    config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    zero_angle = calc.set_weapon_zero(shot, distance)
    assert abs(zero_angle >> Angular.Radian) < calc.VERTICAL_ANGLE_EPSILON_DEGREES


def test_zero_degenerate(loaded_engine_instance):
    """Test zero finding when initial shot hits minimum altitude immediately."""
    distance = Distance.Meter(300)
    shot = create_23_mm_shot()
    shot.atmo = Atmo(altitude=0)
    config = BaseEngineConfigDict(cMinimumVelocity=0, cMinimumAltitude=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    calc.set_weapon_zero(shot, distance)
    print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree} degrees")
    try:
        hit_result = calc.fire(shot, trajectory_range=distance)
    except RangeError as e:
        if e.last_distance is None:
            raise e
        hit_result = HitResult(shot, e.incomplete_trajectory)
    result_at_zero = hit_result.get_at_distance(distance)
    assert result_at_zero is not None
    assert result_at_zero.distance.raw_value == pytest.approx(distance.raw_value, abs=1e-2)
    assert result_at_zero.height >> Distance.Meter == pytest.approx(0, abs=1e-2)


def test_zero_too_close(loaded_engine_instance):
    """When initial shot is too close to make sense, return look_angle."""
    distance = Distance.Meter(0)
    shot = create_23_mm_shot()
    calc = Calculator(engine=loaded_engine_instance)
    zero_angle = calc.set_weapon_zero(shot, distance)
    assert zero_angle.raw_value == shot.look_angle.raw_value


def test_negative_sight_height(loaded_engine_instance):
    """Test zero finding with negative sight height."""
    shot = create_23_mm_shot()
    shot.weapon.sight_height = Distance.Millimeter(-100)
    calc = Calculator(engine=loaded_engine_instance)
    zero_angle = calc.set_weapon_zero(shot, Distance.Millimeter(100))
    assert (zero_angle >> Angular.Degree) == pytest.approx(45.0, abs=1e-4)
