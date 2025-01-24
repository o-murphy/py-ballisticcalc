import time
from random import random
from typing import NamedTuple

import pytest
import random

from py_ballisticcalc import Distance, DragModel, TableG1, Weight, Weapon, Ammo, Shot, Velocity, \
    Angular, Calculator

from py_ballisticcalc.helpers import find_index_of_point_for_distance, find_index_for_time_point, find_index_of_apex_point, \
    find_index_of_apex_in_points

from py_ballisticcalc.helpers import calculate_drag_free_range

@pytest.fixture
def one_degree_shot():
    drag_model = DragModel(
        bc=0.759,
        drag_table=TableG1,
        weight=Weight.Gram(108),
        diameter=Distance.Millimeter(23),
        length=Distance.Millimeter(108.2),
    )
    weapon = Weapon()
    muzzle_velocity = Velocity.MPS(930)
    ammo = Ammo(drag_model, muzzle_velocity)
    angle_in_degrees = 1
    shot = Shot(weapon=weapon, ammo=ammo, relative_angle=Angular.Degree(angle_in_degrees))
    max_drag_free_range = calculate_drag_free_range(
        muzzle_velocity>>Velocity.MPS, angle_in_degrees
    )
    calc = Calculator()
    hit_result = calc.fire(shot, Distance.Meter(max_drag_free_range), extra_data=True)
    return hit_result

@pytest.mark.parametrize(
    "velocity,angle,expected_range",
    [
        (10, 45, 10.20),
        (20, 30, 35.31),
        (50, 60, 220.97),
    ],
)
def test_calculate_drag_free_range(
    velocity, angle, expected_range
):
    range = calculate_drag_free_range(velocity, angle)
    assert pytest.approx(range, 0.01) == expected_range


def test_find_index_for_timepoint(one_degree_shot):
    one_second_time_point = 1
    # when strictly_bigger_or_equal is False, we are finding nearest point to the specified time
    index = find_index_for_time_point(
        one_degree_shot, one_second_time_point, strictly_bigger_or_equal=False
    )
    print(f"{index=}")
    assert abs(one_degree_shot.trajectory[index].time - one_second_time_point) <= abs(
        one_degree_shot.trajectory[index + 1].time - one_second_time_point
    )

    # when strictly_bigger_or_equal is Treu, we are finding first existing time point, which is biiger or equal to
    # the specified time
    bigger_index = find_index_for_time_point(
        one_degree_shot, one_second_time_point, strictly_bigger_or_equal=True
    )
    assert bigger_index == index + 1

    shot_max_time_point = one_degree_shot[-1].time

    # Edge case testing - we should be able to find the last available time point in both modes
    last_point_index = find_index_for_time_point(
        one_degree_shot, shot_max_time_point, strictly_bigger_or_equal=False
    )
    assert last_point_index != -1
    # print(f"{shot_max_time_point=} {one_degree_shot.trajectory[last_point_index].time=} {last_point_index=}" )
    # print(f"{shot_max_time_point=} {one_degree_shot.trajectory[len(one_degree_shot.trajectory) - 1].time=} {len(one_degree_shot.trajectory) - 1=}")
    assert last_point_index == len(one_degree_shot.trajectory) - 1

    last_point_index = find_index_for_time_point(
        one_degree_shot, shot_max_time_point, strictly_bigger_or_equal=True
    )
    assert last_point_index != -1
    assert last_point_index == len(one_degree_shot.trajectory) - 1

    # if deviation of searched time point is equal to max_time_deviation_in_seconds, then last point should be found
    index = find_index_for_time_point(
        one_degree_shot,
        shot_max_time_point + 1,
        strictly_bigger_or_equal=False,
        max_time_deviation_in_seconds=1,
    )
    assert index == len(one_degree_shot.trajectory) - 1

    index = find_index_for_time_point(
        one_degree_shot,
        shot_max_time_point + 1,
        strictly_bigger_or_equal=False,
        max_time_deviation_in_seconds=0.5,
    )
    assert index == -1

    # we should be able to find first timepoint in both modes
    index = find_index_for_time_point(
        one_degree_shot, 0, strictly_bigger_or_equal=False
    )
    assert 0 == index

    index = find_index_for_time_point(one_degree_shot, 0, strictly_bigger_or_equal=True)
    assert 0 == index

    # exception should be thrown on negative time
    with pytest.raises(ValueError):
        find_index_for_time_point(one_degree_shot, -1)

    # exception should be thrown on negative max_time_deviation
    with pytest.raises(ValueError):
        find_index_for_time_point(one_degree_shot, 0, max_time_deviation_in_seconds=-1)


def test_find_index_for_distance(one_degree_shot):
    shot = one_degree_shot
    shot_max_distance = shot.trajectory[-1].distance >> Distance.Meter
    print(f"{shot_max_distance=}")
    assert 0 == find_index_of_point_for_distance(shot, 0)

    assert 500 < shot_max_distance
    assert find_index_of_point_for_distance(
        shot, 500
    ) < find_index_of_point_for_distance(shot, 1000)
    assert 1000 < shot_max_distance

    assert len(shot.trajectory) - 1 == find_index_of_point_for_distance(
        shot, shot_max_distance, distance_unit=Distance.Meter
    )
    # for reproducibility
    random.seed(42)
    random_indices = random.sample(range(len(shot.trajectory)), 100)
    start_time = time.time()

    for i in random_indices:
        p = shot.trajectory[i]
        assert find_index_for_time_point(
            shot, p.time
        ) == find_index_of_point_for_distance(
            shot, p.distance >> Distance.Meter, Distance.Meter
        )
    end_time = time.time()
    print(f'Search for {len(random_indices)} random point has taken {end_time-start_time:.1f} s')


def test_find_apex(one_degree_shot):
    index = find_index_of_apex_point(one_degree_shot)
    assert index!=-1
    apex_point_height = one_degree_shot.trajectory[index].height >> Distance.Meter
    assert apex_point_height==9.401238429883138



class TestTrajectoryPoint:
    def __init__(self, height):
        self.height = height

def generate_trajectory_points(height_list):
    return [TestTrajectoryPoint(h) for h in height_list]

@pytest.mark.parametrize("input, expected", [
     # Simple cases
     (generate_trajectory_points([1, 3, 7,  10, 8, 4]), 3),  # Normal case
     (generate_trajectory_points([10]), 0),  # Single element
     # Multiple elements with clear apex
     (generate_trajectory_points([1, 2, 3, 4]), 3),  # Increasing only
     (generate_trajectory_points([4, 3, 2, 1]), 0),  # Decreasing only
     # Edge cases
    (generate_trajectory_points([1, 5, 5, 1]), 1),
    (generate_trajectory_points([1, 5, 5, 7, 5]), 3),  # Plateau before peak
    (generate_trajectory_points(list(range(1, 100))+list(range(99, 0, -1))), 98),  # Peak at 99
     # No valid apex (edge case, behavior depends on definition)
    (generate_trajectory_points([]), -1),  # Empty array
])
def test_find_apex_index(input, expected):
    index = find_index_of_apex_in_points(input)
    assert index == expected