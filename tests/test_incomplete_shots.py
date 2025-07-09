import time

import pytest

from py_ballisticcalc import (
    Distance,
    RangeError,
    HitResult,
)
from tests.fixtures_and_helpers import print_out_trajectory_compact, zero_height_calc, \
    shot_with_relative_angle_in_degrees


def test_shot_incomplete(zero_height_calc):
    angle_in_degrees = 5.219710693607955
    distance = 6937.3716148080375

    shot = shot_with_relative_angle_in_degrees(angle_in_degrees)
    range = Distance.Meter(distance)

    def check_end_point(hit_result):
        last_point_distance = hit_result[-1].distance >> Distance.Meter
        last_point_height = hit_result[-1].height >> Distance.Meter
        print(f"{ last_point_distance=} { last_point_height=}")
        assert last_point_distance > 3525.0
        assert last_point_height < 1e-10  # Basically zero; allow for rounding

    try:
        extra_data = False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    check_end_point(hit_result)

    try:
        extra_data = False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    check_end_point(hit_result)

    try:
        extra_data = True
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    check_end_point(hit_result)

    try:
        extra_data = True
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=range)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)

    check_end_point(hit_result)


def test_vertical_shot(zero_height_calc):
    shot = shot_with_relative_angle_in_degrees(90)
    range = Distance.Meter(10)
    try:
        extra_data = False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert hit_result[-1].distance >> Distance.Meter == pytest.approx(0, abs=1e-10)
    assert hit_result[-1].height >> Distance.Meter == pytest.approx(0, abs=0.1)

    try:
        extra_data = True
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data)
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert hit_result[-1].distance >> Distance.Meter == pytest.approx(0, abs=1e-10)
    assert hit_result[-1].height >> Distance.Meter == pytest.approx(0, abs=0.1)


def test_no_duplicate_points(zero_height_calc):
    # this is a shot for point (1000, 0)
    shot = shot_with_relative_angle_in_degrees(0.46571949074059704)
    zero_distance = Distance.Meter(1000)
    # setting up bigger distance than required by shot
    range = Distance.Meter(1100)
    try:
        extra_data = False
        hit_result = zero_height_calc.fire(shot, range, extra_data=extra_data, trajectory_step=Distance.Meter(100))
    except RangeError as e:
        print(f'{e.reason} {len(e.incomplete_trajectory)=}')
        if e.reason in [RangeError.MaximumDropReached, RangeError.MinimumAltitudeReached]:
            hit_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
    print_out_trajectory_compact(hit_result)
    assert len(hit_result.trajectory) >= 2
    assert hit_result[-2] != hit_result[-1]
    result_at_zero = hit_result.get_at_distance(zero_distance)
    assert result_at_zero is not None
    assert result_at_zero.distance >> Distance.Meter == pytest.approx(1000, abs=0.2)
    assert result_at_zero.height >> Distance.Meter == pytest.approx(0, abs=0.01)
    assert hit_result[-1].distance >> Distance.Meter > hit_result[-2].distance >> Distance.Meter
    assert hit_result[-1].height >> Distance.Meter < hit_result[-2].height >> Distance.Meter


def test_no_duplicated_point_many_trajectories(zero_height_calc):
    # bigger than max range of weapon
    range = Distance.Meter(8000)
    for extra_data in [False, True]:
        angle = 0
        while angle <= 90:
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
            assert len(hit_result.trajectory) == len(set(hit_result.trajectory))
            angle += 10


test_points = [
    (400, 300, 37.018814944137404),
    (1200, 900, 37.5653274152026),
    (1200, 1500, 52.1940023594277),
    (1682.0020070293451, 3979.589760371905, 70.6834782844347),
    (4422.057278753554, 1975.0518929482573, 34.6455781039671),
    (5865.263344484814, 1097.7312160636257, 30.1865144767384),
    (564.766336537204, 1962.27673604624, 74.371041637992),
    (5281.061059442218, 2529.348893994985, 46.2771485569329),
    (2756.3221111683733, 4256.441991651934, 65.7650037845664),
    (63.11845014860512, 4215.811071201791, 89.2734502050901),
    (3304.002996878733, 4187.8846508525485, 65.48673417912764),
    (6937.3716148080375, 358.5414845184736, 38.98449130666212),
    (7126.0478000569165, 0.001, 38.58299087491584),
]


@pytest.mark.parametrize("distance, height, angle_in_degrees", test_points)
def test_end_points_are_included(distance, height, angle_in_degrees, zero_height_calc):
    """Make sure that we get the same result with and without extra data"""
    shot = shot_with_relative_angle_in_degrees(angle_in_degrees)
    calc = zero_height_calc
    range = Distance.Meter(distance)
    print(f'\nDistance: {distance:.2f} Height: {height:.2f}')

    extra_data_flag = True

    start_time_extra_data = time.time()
    try:
        hit_result_extra_data = calc.fire(shot, range, extra_data=extra_data_flag)
    except RangeError as e:
        print(f'Got range error {e=}')
        hit_result_extra_data = HitResult(shot, e.incomplete_trajectory, extra=extra_data_flag)
    end_time_extra_data = time.time()
    print(
        f'{extra_data_flag=} {len(hit_result_extra_data.trajectory)=} {(end_time_extra_data-start_time_extra_data)=:.3f}s')
    print_out_trajectory_compact(hit_result_extra_data, f"extra_data={extra_data_flag}")
    last_point_extra_data = hit_result_extra_data[-1]
    distance_extra_data = last_point_extra_data.distance >> Distance.Meter
    height_extra_data = last_point_extra_data.height >> Distance.Meter
    print(f"{extra_data_flag=} Distance {distance_extra_data:.02f} Height {height_extra_data:.02f}")
    no_extra_data_flag = False
    start_time_no_extra_data = time.time()
    try:
        hit_result_no_extra_data = calc.fire(shot, range, extra_data=no_extra_data_flag)
    except RangeError as e:
        print(f'Got range error {e=}')
        hit_result_no_extra_data = HitResult(shot, e.incomplete_trajectory, extra=no_extra_data_flag)
    end_time_no_extra_data = time.time()
    print(
        f'{no_extra_data_flag=} {len(hit_result_no_extra_data.trajectory)=} {(end_time_no_extra_data-start_time_no_extra_data)=:.3f}s')
    print_out_trajectory_compact(hit_result_no_extra_data, f"extra_data={no_extra_data_flag}")

    last_point_no_extra_data = hit_result_no_extra_data[-1]
    distance_no_extra_data = last_point_no_extra_data.distance >> Distance.Meter
    height_no_extra_data = last_point_no_extra_data.height >> Distance.Meter

    print(f"Extra data={no_extra_data_flag}  Distance {distance_no_extra_data} Height {height_no_extra_data}")
    print(f"Extra data={no_extra_data_flag}  Distance {distance_no_extra_data:.02f} Height {height_no_extra_data:.02f}")
    distance_difference = abs(distance_extra_data - distance_no_extra_data)
    height_difference = abs(height_extra_data - height_no_extra_data)
    print(f'Difference in results Distance: {distance_difference :.02f} '
          f'Height {height_difference :.02f}')

    assert distance_difference <= Distance.Foot(0.2) >> Distance.Meter
