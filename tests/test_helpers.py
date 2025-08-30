import math
import random
import sys
import time

import pytest

from py_ballisticcalc import Distance, DragModel, TableG1, Weight, Ammo, Shot, Velocity, \
    Angular, Calculator, TrajFlag
from py_ballisticcalc.helpers import vacuum_angle_to_zero, vacuum_range, vacuum_time_to_zero, vacuum_velocity_to_zero
from py_ballisticcalc.helpers import find_index_of_point_for_distance, find_index_for_time_point, \
    find_time_for_distance_in_shot
from py_ballisticcalc.logger import logger, disable_file_logging, enable_file_logging


class TestVacuumCalcs:
    @pytest.mark.parametrize(
        "velocity,angle,expected_range",
        [
            (10, 45, 10.20),
            (20, 30, 35.31),
            (50, 60, 220.97),
        ],
    )
    def test_calculate_drag_free_range(self, velocity, angle, expected_range):
        range = vacuum_range(velocity, angle)
        assert pytest.approx(range, 0.01) == expected_range

    def test_vacuum_functions_consistency(self):
        v = 100.0
        angle = 30.0
        g = 9.81
        r = vacuum_range(v, angle, gravity=-g)
        t = vacuum_time_to_zero(v, angle, gravity=-g)
        expected_r = (v * math.cos(math.radians(angle))) * t
        assert r == pytest.approx(expected_r, rel=1e-12)

        # Solve inverse problems
        angle2 = vacuum_angle_to_zero(v, r, gravity=-g)
        assert angle2 == pytest.approx(angle)
        v2 = vacuum_velocity_to_zero(t, angle, gravity=-g)
        assert v2 == pytest.approx(v)


class TestFindIndex:
    @pytest.fixture(autouse=True)
    def one_degree_shot(self, loaded_engine_instance):
        drag_model = DragModel(
            bc=0.759,
            drag_table=TableG1,
            weight=Weight.Gram(108),
            diameter=Distance.Millimeter(23),
            length=Distance.Millimeter(108.2),
        )
        muzzle_velocity = Velocity.MPS(930)
        ammo = Ammo(drag_model, muzzle_velocity)
        angle_in_degrees = 1
        shot = Shot(ammo=ammo, relative_angle=Angular.Degree(angle_in_degrees))
        max_drag_free_range = vacuum_range(
            muzzle_velocity >> Velocity.MPS, angle_in_degrees
        )
        calc = Calculator(engine=loaded_engine_instance)
        hit_result = calc.fire(
            shot,
            Distance.Meter(max_drag_free_range),
            Distance.Meter(max_drag_free_range / 10),
            flags=TrajFlag.ALL
        )
        return hit_result

    def test_find_time_for_distance_returns_nan_when_not_found(self, one_degree_shot):
        # Ask for time at a much larger distance than computed
        tm = find_time_for_distance_in_shot(one_degree_shot, distance_in_unit=10_000)
        assert math.isnan(tm)

    def test_find_index_for_timepoint(self, one_degree_shot):
        one_second_time_point = 1
        # when strictly_bigger_or_equal is False, we are finding nearest point to the specified time
        index = find_index_for_time_point(
            one_degree_shot, one_second_time_point, strictly_bigger_or_equal=False
        )
        print(f"{index=}")
        assert abs(one_degree_shot.trajectory[index].time - one_second_time_point) <= abs(
            one_degree_shot.trajectory[index + 1].time - one_second_time_point
        )

        # when strictly_bigger_or_equal is True, we are finding first existing time point, which is bigger or equal to
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
            shot_max_time_point + (1 - sys.float_info.epsilon),
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

    def test_find_index_for_distance(self, one_degree_shot):
        shot = one_degree_shot
        shot_max_distance = shot.trajectory[-1].distance >> Distance.Meter
        print(f"{shot_max_distance=}")
        assert 0 == find_index_of_point_for_distance(shot, 0)

        assert 500 < shot_max_distance
        assert find_index_of_point_for_distance(shot, 500) < find_index_of_point_for_distance(shot, 1000)
        assert 1000 < shot_max_distance

        assert len(shot.trajectory) - 1 == find_index_of_point_for_distance(
            shot, shot_max_distance, distance_unit=Distance.Meter
        )
        # for reproducibility
        random.seed(42)
        random_indices = random.sample(range(len(shot.trajectory)), min(10, len(shot.trajectory)))
        start_time = time.time()
        for i in random_indices:
            p = shot.trajectory[i]
            assert find_index_for_time_point(
                shot, p.time
            ) == find_index_of_point_for_distance(
                shot, p.distance >> Distance.Meter, Distance.Meter
            )
        end_time = time.time()
        print(f'Search for {len(random_indices)} random point has taken {end_time - start_time:.1f} s')


class TestLogger:
    def test_logger_disable_idempotent(self):
        # Should be safe to call repeatedly when not enabled
        disable_file_logging()
        disable_file_logging()

    def test_file_logger(self, tmp_path):
        # Exercise logger file logging path
        logfile = tmp_path / "ballistics_debug.log"
        enable_file_logging(str(logfile))
        logger.debug("hello file")
        disable_file_logging()
        assert logfile.exists() and logfile.read_text() != ""
