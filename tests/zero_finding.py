"""Unit test for zero finding in ballistic calculator."""
# mypy: ignore - mypy overhead is not worth it for test code
import math
import pytest

from py_ballisticcalc import (
    Distance,
    BaseEngineConfigDict,
    Calculator,
    DragModel,
    TableG1,
    Weight,
    Velocity,
    Ammo,
    Weapon,
    Shot,
)
from py_ballisticcalc.helpers import find_index_of_apex_point

DISTANCES_FOR_CHECKING = (
    # list(range(100, 1000, 100)) +
    # list(range(1000, 3000, 1000)) +
    # list(range(3000, 4000, 100)) +
    # list(range(4000, 7000, 500)) +
    # list(range(6600, 7100, 100)) +
    #list(range(7000, 7100, 100)) +
    [7126.05]
)


def create_shot():
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


@pytest.fixture(autouse=True)
def zero_min_velocity_calc(loaded_engine_instance):
    config = BaseEngineConfigDict(
        cMinimumVelocity=0,
    )
    return Calculator(engine=loaded_engine_instance, config=config)


@pytest.mark.parametrize("distance", DISTANCES_FOR_CHECKING)
def test_set_weapon_zero(distance, zero_min_velocity_calc):
    shot = create_shot()
    zero_min_velocity_calc.set_weapon_zero(shot, Distance.Meter(distance))
    print(f"{math.degrees(shot.barrel_elevation)=}")
    hit_result = zero_min_velocity_calc.fire(
        shot, Distance.Meter(distance), extra_data=True
    )
    # print(
    #     f"{hit_result[-1].distance >> Distance.Meter=} "
    #     f"{hit_result[-1].time=} "
    #     f"{hit_result[-1].velocity >> Velocity.MPS=}"
    # )
    # index_of_apex_point = find_index_of_apex_point(hit_result)
    # apex_point = hit_result.trajectory[index_of_apex_point]
    # print(
    #     f"{apex_point.height >> Distance.Meter=} "
    #     f"{apex_point.distance >> Distance.Meter=} "
    #     f"{apex_point.time=} "
    #     f"{apex_point.velocity >> Velocity.MPS=}"
    # )
    assert abs((hit_result[-1].distance >> Distance.Meter) - distance) <= 1.0
