import math
import pytest
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG1
from py_ballisticcalc.munition import Ammo
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *
from py_ballisticcalc import (
    Calculator,
    BaseEngineConfigDict,
    RK4IntegrationEngine,
    VelocityVerletIntegrationEngine
)
from py_ballisticcalc.generics import EngineFactoryProtocol
from tests.fixtures_and_helpers import create_23_mm_shot, create_5_56_mm_shot

pytestmark = pytest.mark.engine

DISTANCES_FOR_CHECKING = (
    # list(range(100, 1000, 100)) +
    # list(range(1000, 3000, 1000)) +
    # list(range(3000, 4000, 100)) +
    # list(range(4000, 7000, 500)) +
    # list(range(6600, 7100, 100)) +
    [7126.05]
)

# @pytest.mark.parametrize("distance", DISTANCES_FOR_CHECKING)
# def test_set_weapon_zero(distance, loaded_engine_instance):
#     """This is a very slow and demanding test, so it should be run separately."""
#     shot = create_23_mm_shot()
#     config = BaseEngineConfigDict(cMinimumVelocity=0)
#     calc = Calculator(config=config, engine=loaded_engine_instance)
#     calc.set_weapon_zero(shot, Distance.Meter(distance))
#     print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree}")
#     hit_result = calc.fire(shot, Distance.Meter(distance))
#     # print(
#     #     f"{hit_result[-1].distance >> Distance.Meter=} "
#     #     f"{hit_result[-1].time=} "
#     #     f"{hit_result[-1].velocity >> Velocity.MPS=}"
#     # )
#     assert abs(hit_result[-1].height.raw_value) < 1e+1

def create_slow_shot():
    """Long-range shots take too long to compute with pure Python engines."""
    dm = DragModel(bc=0.1, drag_table=TableG1)
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(50)))

def test_find_max_range(loaded_engine_instance):
    """Test .find_max_range() on horizontal."""
    distance = Distance.Meter(194.1)  # Max horizontal range
    shot = create_slow_shot()
    if callable(loaded_engine_instance) and isinstance(loaded_engine_instance, EngineFactoryProtocol):
        config = BaseEngineConfigDict(cMinimumVelocity=0)
    elif issubclass(loaded_engine_instance, (RK4IntegrationEngine, VelocityVerletIntegrationEngine)):
        # These engines run slowly at their default step size, and don't need as much precision to pass here
        config = BaseEngineConfigDict(cMinimumVelocity=0, cStepMultiplier=5.0)
    else:
        config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    d, a = calc.find_max_range(shot)
    assert abs(d.raw_value - distance.raw_value) < 1e+1

def test_zero_at_max_range(loaded_engine_instance):
    """Test zero finding at maximum range."""
    distance = Distance.Meter(159.0)
    shot = create_slow_shot()
    shot.slant_angle = Angular.Degree(15)  # Max horizontal range 159.4
    if callable(loaded_engine_instance) and isinstance(loaded_engine_instance, EngineFactoryProtocol):
        config = BaseEngineConfigDict(cMinimumVelocity=0)
    elif issubclass(loaded_engine_instance, (RK4IntegrationEngine, VelocityVerletIntegrationEngine)):
        # These engines run slowly at their default step size, and don't need as much precision to pass here
        config = BaseEngineConfigDict(cMinimumVelocity=0, cStepMultiplier=5.0)
    else:
        config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    zero_angle = calc.find_zero_angle(shot, distance)
    # Verify by shooting at this angle
    shot.barrel_elevation = zero_angle
    hit_result = calc.fire(shot, trajectory_range=distance, flags=TrajFlag.ZERO_DOWN)
    zero_down = hit_result.flag(TrajFlag.ZERO_DOWN)
    assert zero_down is not None, "ZERO_DOWN flag not found in hit_result"
    assert abs(zero_down.slant_height.raw_value) < 1e+1

def test_zero_with_look_angle(loaded_engine_instance):
    """Test zero finding with a high look angle."""
    target_distance = Distance.Meter(1000)
    shot = create_5_56_mm_shot()
    shot.look_angle = Angular.Degree(30)
    # config = BaseEngineConfigDict(cMinimumVelocity=0)
    # calc = Calculator(config=config, engine=loaded_engine_instance)
    calc = Calculator(engine=loaded_engine_instance)
    calc.set_weapon_zero(shot, target_distance)
    print(f"Zero for slant {target_distance=} is elevation={shot.barrel_elevation >> Angular.Degree} degrees")
    horizontal_distance = Distance.Meter((target_distance >> Distance.Meter) * math.cos(shot.look_angle >> Angular.Radian))
    hit_result = calc.fire(shot, trajectory_range=horizontal_distance, flags=TrajFlag.ZERO_DOWN)
    # TrajFlag.ZERO_DOWN marks the point at which bullet crosses down through sight line
    zero_down = hit_result.flag(TrajFlag.ZERO_DOWN)
    assert zero_down is not None, "ZERO_DOWN flag not found in hit_result"
    assert abs(zero_down.slant_distance.raw_value - target_distance.raw_value) < 1e+1

def test_vertical_shot_zero(loaded_engine_instance):
    """Test zero finding for a vertical shot."""
    distance = Distance.Meter(1000)
    shot = create_5_56_mm_shot()
    shot.look_angle = Angular.Degree(90)
    config = BaseEngineConfigDict(cMinimumVelocity=0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    zero_angle = calc.set_weapon_zero(shot, distance)
    assert abs(zero_angle >> Angular.Radian) < calc.APEX_IS_MAX_RANGE_RADIANS

# def test_zero_degenerate(loaded_engine_instance):
#     """Test zero finding when initial shot hits minimum altitude immediately."""
#     distance = Distance.Meter(300)
#     shot = create_23_mm_shot()
#     shot.atmo = Atmo(altitude=0)
#     config = BaseEngineConfigDict(cMinimumVelocity=0, cMinimumAltitude=0)
#     calc = Calculator(config=config, engine=loaded_engine_instance)
#     calc.set_weapon_zero(shot, distance)
#     print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree} degrees")
#     hit_result = calc.fire(shot, trajectory_range=distance, raise_range_error=False)
#     result_at_zero = hit_result.get_at('distance', distance)
#     assert result_at_zero is not None
#     assert result_at_zero.distance.raw_value == pytest.approx(distance.raw_value, abs=1e-1)
#     assert result_at_zero.height >> Distance.Meter == pytest.approx(0, abs=1e-2)

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
