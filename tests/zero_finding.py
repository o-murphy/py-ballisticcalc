"""Unit test for zero finding in ballistic calculator."""
# mypy: ignore - mypy overhead is not worth it for test code
import pytest

from py_ballisticcalc import (
    Angular,
    Distance,
    DragModel,
    TableG1,
    Weight,
    Velocity,
    Ammo,
    Weapon,
    Shot,
)
from .fixtures_and_helpers import zero_min_velocity_calc

DISTANCES_FOR_CHECKING = (
    list(range(100, 1000, 100)) +
    list(range(1000, 3000, 1000)) +
    list(range(3000, 4000, 100)) +
    list(range(4000, 7000, 500)) +
    list(range(6600, 7100, 100)) +
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


@pytest.mark.parametrize("distance", DISTANCES_FOR_CHECKING)
def test_set_weapon_zero(distance, zero_min_velocity_calc):
    shot = create_shot()
    zero_min_velocity_calc.set_weapon_zero(shot, Distance.Meter(distance))
    print(f"Zero for {distance=} is elevation={shot.barrel_elevation >> Angular.Degree}")
    hit_result = zero_min_velocity_calc.fire(
        shot, Distance.Meter(distance), extra_data=True
    )
    # print(
    #     f"{hit_result[-1].distance >> Distance.Meter=} "
    #     f"{hit_result[-1].time=} "
    #     f"{hit_result[-1].velocity >> Velocity.MPS=}"
    # )
    assert abs((hit_result[-1].distance >> Distance.Meter) - distance) <= 1.0
