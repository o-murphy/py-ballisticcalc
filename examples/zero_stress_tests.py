"""Extreme tests of zero-finding logic in scipy_engine."""
import datetime
import math
import random

from py_ballisticcalc import Calculator, SciPyEngineConfigDict, Distance, Velocity, DragModel, TableG1, \
    Weight, Ammo, Weapon, Shot, Angular, RangeError, TrajFlag, HitResult, OutOfRangeError, ZeroFindingError


def create_zero_velocity_zero_min_altitude_calc(engine_name, method):
    config = SciPyEngineConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=0,
        integration_method=method
    )
    calc = Calculator(config, engine=engine_name)
    return calc

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

def check_one_shot(calc, shot, point_x, point_y, expect_zero_finding_exception: bool=False):
    look_angle_in_degrees = math.degrees(math.atan2(point_y, point_x))
    shot.look_angle = Angular.Degree(look_angle_in_degrees)
    distance_in_meters = math.sqrt(point_x ** 2 + point_y ** 2)
    print(f"\nScenario: x={float(point_x)} y={float(point_y)} {distance_in_meters=:.2f} at {look_angle_in_degrees=:.4f}")
    try:
        shot_angle = calc._engine_instance.find_zero_angle(shot, Distance.Meter(distance_in_meters))
        print(f'\tZero elevation = {shot_angle>>Angular.Degree} degrees')
        test_shot = create_23_mm_shot()
        test_shot.relative_angle = shot_angle
        try:
            if point_x==0:
                fire_distance = 0.1
                time_step = 0.001
                extra = True
            else:
                fire_distance = point_x
                time_step = 0.
                extra = False
            hit_results = calc.fire(test_shot, Distance.Meter(fire_distance), time_step=time_step, extra_data=extra)
        except RangeError as e:
            hit_results = HitResult(test_shot, e.incomplete_trajectory, extra=extra)

        if point_x==0:
            apex_point = hit_results.flag(TrajFlag.APEX)
            apex_point_index = None
            if apex_point is not None:
                for index, p in enumerate(hit_results.trajectory):
                    if p == apex_point:
                        apex_point_index = index
                        break
                assert apex_point_index
                ascending_trajectory = hit_results.trajectory[:apex_point_index+1]
                min_dev_point = None
                min_diff = float('inf')
                for p in ascending_trajectory:
                    diff = abs((p.height>>Distance.Meter)-point_y)
                    if diff<min_diff:
                        min_diff = diff
                        min_dev_point = p
                test_shot_x = min_dev_point.distance >> Distance.Meter
                test_shot_y = min_dev_point.height >> Distance.Meter
        else:
            test_shot_x = hit_results[-1].distance >> Distance.Meter
            test_shot_y = hit_results[-1].height >> Distance.Meter
        print(f"\tConfirmation shot reached x={float(test_shot_x)} y={float(test_shot_y)}")
        assert abs(point_x - test_shot_x) < 1e-2
        assert abs(point_y - test_shot_y) < 1e-2
    except OutOfRangeError as e:
        print(f"\tOutOfRangeError {e}")
        max_range, max_angle = calc._engine_instance.find_max_range(shot)
        assert distance_in_meters > max_range >> Distance.Meter
    except ZeroFindingError as e:
        if expect_zero_finding_exception:
            print(f"Obtained expected zero finding error")
        else:
            raise e

if __name__=="__main__":
    attempt_count = 10  # Number of random shots to test
    engine_name = "scipy_engine"
    method = 'RK45'

    calc = create_zero_velocity_zero_min_altitude_calc(engine_name, method)
    print(f'{calc=}')
    print(f'\nENGINE {engine_name} {method=}\n')
    shot = create_23_mm_shot()
    max_range, max_angle = calc._engine_instance.find_max_range(shot)
    max_range_in_meters = max_range >> Distance.Meter
    print(f'Baseline shot max horizontal range: '
          f'{max_range_in_meters:.2f}m at elevation {(max_angle >> Angular.Degree):.4f} degrees')

    shot.relative_angle = Angular.Degree(90)
    try:
        hit_result = calc.fire(shot, Distance.Meter(1), time_step=0.001, extra_data=True)
    except RangeError as e:
        hit_result = HitResult(shot, e.incomplete_trajectory, extra=True)
    apex_point = hit_result.flag(TrajFlag.APEX)
    max_height_in_meters = apex_point.height >> Distance.Meter
    print(f'Vertical shot reaches height {max_height_in_meters:.2f}m')

    # checking extreme scenarios
    check_one_shot(calc, create_23_mm_shot(), max_range_in_meters, 0)
    check_one_shot(calc, create_23_mm_shot(), 0, max_height_in_meters)
    check_one_shot(calc, create_23_mm_shot(), 0, 0, expect_zero_finding_exception=True)
    check_one_shot(calc, create_23_mm_shot(), max_range_in_meters, max_height_in_meters)

    start_time = datetime.datetime.now()
    random.seed(42)  # For reproducibility
    for _ in range(attempt_count):
        shot = create_23_mm_shot()
        point_x = random.random() * max_range_in_meters
        point_y = random.random() * max_height_in_meters
        check_one_shot(calc, shot, point_x, point_y)
    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    print(f'\nFinding {attempt_count} random angles took {elapsed_time} seconds: '
          f'({(elapsed_time/attempt_count)} seconds per shot)')
