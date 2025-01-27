import pytest
from py_ballisticcalc import (
    DragModel,
    TableG1,
    Weight,
    Distance,
    Ammo,
    Velocity,
    Weapon,
    InterfaceConfigDict,
    Calculator,
    Shot,
    Angular,
    RangeError,
    HitResult,
)

def print_out_trajectory_compact(hit_result:HitResult, distance_unit: Distance=Distance.Meter):
    for i, p in enumerate(hit_result.trajectory):
        print(f'{i+1}. ({p.distance>>distance_unit}, {p.height>>distance_unit})')

def test_shot_incomplete():
    drag_model = DragModel(
        bc=0.759,
        drag_table=TableG1,
        weight=Weight.Gram(108),
        diameter=Distance.Millimeter(23),
        length=Distance.Millimeter(108.2),
    )
    ammo = Ammo(drag_model, Velocity.MPS(930))

    gun = Weapon()
    config = InterfaceConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=Distance.Meter(0),
        cMaximumDrop=Distance.Meter(0),
    )
    angle_in_degrees = 5.219710693607955
    distance = 6937.3716148080375
    shot = Shot(
        weapon=gun,
        ammo=ammo,
        relative_angle=Angular.Degree(angle_in_degrees),
    )

    range = Distance.Meter(distance)

    calc = Calculator(_config=config)
    try:
        extra_data = False
        hit_result=calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print(f'{len(hit_result.trajectory)=}')
    print_out_trajectory_compact(hit_result)
#    print(f'{hit_result.trajectory=}')

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    print(f"{ last_point_distance=} { last_point_height=}")
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

    try:
        extra_data = False
        hit_result=calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print(f'{len(hit_result.trajectory)=}')
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    print(f"{ last_point_distance=} { last_point_height=}")
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)


    calc = Calculator(_config=config)
    try:
        extra_data = True
        hit_result=calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print(f'{len(hit_result.trajectory)=}')
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    print(f"{ last_point_distance=} { last_point_height=}")
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

    calc = Calculator(_config=config)
    try:
        extra_data = True
        hit_result=calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print(f'{len(hit_result.trajectory)=}')
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    print(f"{ last_point_distance=} { last_point_height=}")
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)
