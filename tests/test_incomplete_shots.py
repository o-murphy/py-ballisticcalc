import numpy as np
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
    print(f'Length of trajectory: {len(hit_result.trajectory)=}')
    for i, p in enumerate(hit_result.trajectory):
        print(f'{i+1}. ({p.distance>>distance_unit}, {p.height>>distance_unit})')

@pytest.fixture()
def zero_height_calc():
    config = InterfaceConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=Distance.Meter(0),
        cMaximumDrop=Distance.Meter(0),
    )
    calc = Calculator(_config=config)
    return calc

def shot_with_relative_angle_in_degrees(angle_in_degrees: float):
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
        relative_angle=Angular.Degree(angle_in_degrees),
    )
    return shot


def test_shot_incomplete(zero_height_calc):

    angle_in_degrees = 5.219710693607955
    distance = 6937.3716148080375

    shot = shot_with_relative_angle_in_degrees(angle_in_degrees)
    range = Distance.Meter(distance)

    try:
        extra_data = False
        hit_result= zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    print(f"{ last_point_distance=} { last_point_height=}")
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

    try:
        extra_data = False
        hit_result= zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

    try:
        extra_data = True
        hit_result= zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

    try:
        extra_data = True
        hit_result= zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    last_point_distance = hit_result[-1].distance >> Distance.Meter
    last_point_height = hit_result[-1].height >> Distance.Meter
    assert last_point_distance == pytest.approx(3525.0, abs=0.2)
    assert last_point_height == pytest.approx(0.0, abs=0.1)

def test_vertical_shot(zero_height_calc):
    shot = shot_with_relative_angle_in_degrees(90)
    range=Distance.Meter(10)
    try:
        extra_data=False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert hit_result[-1].distance>>Distance.Meter == pytest.approx(0, abs=1e-10)
    assert hit_result[-1].height>>Distance.Meter == pytest.approx(0, abs=0.1)

    try:
        extra_data=True
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert hit_result[-1].distance>>Distance.Meter == pytest.approx(0, abs=1e-10)
    assert hit_result[-1].height>>Distance.Meter == pytest.approx(0, abs=0.1)

def test_no_duplicate_points(zero_height_calc):
    # this is a shot for point (1000, 0)
    shot = shot_with_relative_angle_in_degrees(0.46571949074059704)
    # setting up bigger distance than required by shot
    range=Distance.Meter(1100)
    try:
        extra_data=False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=Distance.Meter(100))
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in[ RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert len(hit_result.trajectory)>=2
    assert hit_result[-2]!=hit_result[-1]
    assert hit_result[-2].distance>>Distance.Meter == pytest.approx(1000, abs=0.2)
    assert hit_result[-2].height>>Distance.Meter == pytest.approx(0, abs=0.01)
    assert hit_result[-1].distance>>Distance.Meter == pytest.approx(1000, abs=0.2)
    assert hit_result[-1].height>>Distance.Meter == pytest.approx(0, abs=0.01)

def test_no_duplicated_point_many_trajectories(zero_height_calc):
    # bigger than max range of weapon
    range = Distance.Meter(8000)
    for extra_data in [False, True]:
        for angle in np.linspace(0, 90, 11):
            shot = shot_with_relative_angle_in_degrees(angle)
            try:
                hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
            except RangeError as e:
                if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
                    print(f'Got range error {e=}')
                    hit_result = HitResult(shot, e.incomplete_trajectory, extra_data)

                else:
                    raise e
            print(f'{len(hit_result.trajectory)=}')
            assert len(hit_result.trajectory)==len(set(hit_result.trajectory))
