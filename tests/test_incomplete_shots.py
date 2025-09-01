import pytest
import time

from py_ballisticcalc import (
    BaseEngineConfigDict,
    Calculator,
    Distance,
    TrajFlag
)
from py_ballisticcalc.unit import Angular, PreferredUnits
from tests.fixtures_and_helpers import print_out_trajectory_compact, zero_height_calc, \
    shot_with_relative_angle_in_degrees, create_5_56_mm_shot

pytestmark = pytest.mark.engine

def test_shot_incomplete(zero_height_calc):
    angle_in_degrees = 5.0
    distance = Distance.Feet(6500.0)

    shot = shot_with_relative_angle_in_degrees(angle_in_degrees)

    def check_end_point(hit_result):
        last_point_distance = hit_result[-1].distance >> Distance.Foot
        last_point_height = hit_result[-1].height >> Distance.Foot
        print(f"{ last_point_distance=} { last_point_height=}")
        assert last_point_distance > 6416.0
        assert last_point_height < 1e-9  # Basically zero; allow for rounding

    flags = TrajFlag.NONE
    hit_result = zero_height_calc.fire(shot, distance, flags=flags, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    check_end_point(hit_result)

    hit_result = zero_height_calc.fire(shot, distance, flags=flags, trajectory_step=distance, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    check_end_point(hit_result)

    flags = TrajFlag.ALL
    hit_result = zero_height_calc.fire(shot, distance, flags=flags, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    check_end_point(hit_result)

    hit_result = zero_height_calc.fire(shot, distance, flags=flags, trajectory_step=distance, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    check_end_point(hit_result)


def test_vertical_shot(zero_height_calc, loaded_engine_instance):
    shot = create_5_56_mm_shot()
    shot.relative_angle = Angular.Degree(90)
    range = Distance.Meter(10)
    hit_result = zero_height_calc.fire(shot, range, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    # In this case all we know is we should have two points, and the last point should be below zero.
    assert len(hit_result) == 2, "With no flags, calculator should return exactly 2 points"
    assert hit_result[-1].height.raw_value < 1e-9, "Last point's height should be at or below zero"

    flags = TrajFlag.ALL
    # To get a ZERO_DOWN point we have to allow engine to cross the zero:
    config = BaseEngineConfigDict(
        cMinimumVelocity=0.0,
        cMinimumAltitude=-1.0,
        cMaximumDrop=-1.0,
    )
    calc = Calculator(config=config, engine=loaded_engine_instance)
    hit_result = calc.fire(shot, range, flags=flags, raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    z = hit_result.flag(TrajFlag.ZERO_DOWN)
    assert z is not None
    assert z.distance.raw_value == pytest.approx(0, abs=1e-10)
    assert z.height >> Distance.Meter == pytest.approx(0, abs=1e-6)
    assert hit_result[-1].time != hit_result[-2].time, "Don't duplicate points"


def test_no_duplicate_points(loaded_engine_instance):
    # this is a shot for point (1000ft, 0)
    shot = shot_with_relative_angle_in_degrees(0.1385398904676405)
    zero_distance = Distance.Foot(1000)
    # setting up bigger distance than required by shot
    range = Distance.Foot(1100)
    config = BaseEngineConfigDict(
        cMinimumVelocity=0.0,
        cMinimumAltitude=-10.0,
        cMaximumDrop=-10.0,
    )
    calc = Calculator(config=config, engine=loaded_engine_instance)
    hit_result = calc.fire(shot, range, trajectory_step=Distance.Foot(100), raise_range_error=False)
    print_out_trajectory_compact(hit_result)
    assert len(hit_result.trajectory) >= 2
    assert hit_result[-2] != hit_result[-1]
    result_at_zero = hit_result.get_at('distance', zero_distance)
    assert result_at_zero is not None
    assert result_at_zero.distance >> Distance.Foot == pytest.approx(1000, abs=0.2)
    assert result_at_zero.height >> Distance.Foot == pytest.approx(0, abs=0.01)
    assert hit_result[-1].distance >> Distance.Foot > hit_result[-2].distance >> Distance.Foot
    assert hit_result[-1].height >> Distance.Foot < hit_result[-2].height >> Distance.Foot


# def test_no_duplicated_point_many_trajectories(zero_height_calc):
#     # bigger than max range of weapon
#     range = Distance.Meter(8000)
#     for flags in [TrajFlag.NONE, TrajFlag.ALL]:
#         angle = 0
#         while angle <= 90:
#             shot = shot_with_relative_angle_in_degrees(angle)
#             hit_result = zero_height_calc.fire(shot, range, flags=flags, raise_range_error=False)
#             if hit_result.error is not None:
#                 print(f'Got {hit_result.error=}')
#             print(f'{len(hit_result.trajectory)=}')
#             assert len(hit_result.trajectory) == len(set(hit_result.trajectory))
#             angle += 30

test_points = [
    (400, 300, 37.018814944137404),
    # (1200, 900, 37.5653274152026),
    # (1200, 1500, 52.1940023594277),
    # (1682.0020070293451, 3979.589760371905, 70.6834782844347),
    # (4422.057278753554, 1975.0518929482573, 34.6455781039671),
    # (5865.263344484814, 1097.7312160636257, 30.1865144767384),
    # (564.766336537204, 1962.27673604624, 74.371041637992),
    # (5281.061059442218, 2529.348893994985, 46.2771485569329),
    # (2756.3221111683733, 4256.441991651934, 65.7650037845664),
    # (63.11845014860512, 4215.811071201791, 89.2734502050901),
    # (3304.002996878733, 4187.8846508525485, 65.48673417912764),
    # (6937.3716148080375, 358.5414845184736, 38.98449130666212),
    (7126.0478000569165, 0.001, 38.58299087491584),
]


@pytest.mark.parametrize("distance, height, angle_in_degrees", test_points)
def test_end_points_are_included(distance, height, angle_in_degrees, zero_height_calc):
    """Make sure that we get the same result with and without extra data"""
    shot = shot_with_relative_angle_in_degrees(angle_in_degrees)
    calc = zero_height_calc
    range = Distance.Meter(distance)
    print(f'\nDistance: {distance:.2f} Height: {height:.2f}')

    flags = TrajFlag.ALL
    start_time_extra_data = time.time()
    hit_result_extra_data = calc.fire(shot, range, flags=flags, raise_range_error=False)
    end_time_extra_data = time.time()
    print(f'{flags=} {len(hit_result_extra_data.trajectory)=} {(end_time_extra_data-start_time_extra_data)=:.3f}s')
    print_out_trajectory_compact(hit_result_extra_data, f"{flags=}")
    last_point_extra_data = hit_result_extra_data[-1]
    distance_extra_data = last_point_extra_data.distance >> Distance.Meter
    height_extra_data = last_point_extra_data.height >> Distance.Meter
    print(f"{flags=} Distance {distance_extra_data:.02f} Height {height_extra_data:.02f}")

    flags = TrajFlag.NONE
    start_time_no_extra_data = time.time()
    hit_result_no_extra_data = calc.fire(shot, range, flags=flags, raise_range_error=False)
    end_time_no_extra_data = time.time()
    print(f'{flags=} {len(hit_result_no_extra_data.trajectory)=} {(end_time_no_extra_data-start_time_no_extra_data)=:.3f}s')
    print_out_trajectory_compact(hit_result_no_extra_data, f"extra_data={flags=}")

    last_point_no_extra_data = hit_result_no_extra_data[-1]
    distance_no_extra_data = last_point_no_extra_data.distance >> Distance.Meter
    height_no_extra_data = last_point_no_extra_data.height >> Distance.Meter

    distance_difference = abs(distance_extra_data - distance_no_extra_data)
    height_difference = abs(height_extra_data - height_no_extra_data)
    print(f'Difference in results Distance: {distance_difference :.02f} '
          f'Height {height_difference :.02f}')

    assert distance_difference <= (PreferredUnits.distance(1.0) >> Distance.Meter)


def test_time_step_recording_and_range_steps(loaded_engine_instance):
    calc = Calculator(engine=loaded_engine_instance)
    shot = create_5_56_mm_shot()
    # tiny range; request time sampling so we get RANGE flags even if dist_step not set
    res = calc.integrate(shot, Distance.Yard(5), None, time_step=0.001)
    assert len(res.trajectory) >= 2
    assert res.trajectory[1].flag & TrajFlag.RANGE


def test_mach_and_zero_flags_found(loaded_engine_instance):
    calc = Calculator(engine=loaded_engine_instance)
    shot = create_5_56_mm_shot()
    shot.weapon.sight_height = Distance.Inch(1.5)
    shot.relative_angle = Angular.Degree(0.5)
    res = calc.fire(shot, Distance.Yard(1000), flags=TrajFlag.ALL)
    z = res.flag(TrajFlag.ZERO)
    assert z is not None and z.flag & TrajFlag.ZERO
    m = res.flag(TrajFlag.MACH)
    assert m is not None and m.flag & TrajFlag.MACH
    a = res.flag(TrajFlag.APEX)
    assert a is not None and a.flag & TrajFlag.APEX
