import math
import pytest

from py_ballisticcalc import (
    SciPyEngineConfigDict,
    Calculator,
    DragModel,
    TableG1,
    Weight,
    Distance,
    Velocity,
    Ammo,
    Weapon,
    Shot,
    Temperature,
    TableG7,
    Angular,
    RangeError,
    HitResult,
    TrajFlag,
    OutOfRangeError,
    PreferredUnits,
    loadMetricUnits,
    ZeroFindingError,
)

ANGLE_EPSILON_IN_DEGREES = 0.0009

class PreferredUnitsContextManager:

    def __enter__(self):
         #print("Storing preferred units...")
         #print(f"On Enter: {PreferredUnits=}")
         values_copies= {}
         for field in getattr(PreferredUnits, '__dataclass_fields__'):
            values_copies[field] = getattr(PreferredUnits, field)
         self.preferred_unit_dict = values_copies
         #print(f"{self.preferred_unit_dict=}")

    def __exit__(self, exc_type, exc_value, exc_tb):
        #print("Leaving the context...")
        #print(f"Before restoring: {PreferredUnits=} ")
        #print(exc_type, exc_value, exc_tb, sep="\n")
        PreferredUnits.set(**self.preferred_unit_dict)
        #print(f"After restoring: {PreferredUnits=} ")


def create_zero_velocity_zero_min_altitude_calc(engine_name, method, max_iteration:int=60):
    config = SciPyEngineConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=0,
        integration_method=method,
        cMaxIterations=max_iteration
    )
    return Calculator(config, engine=engine_name)

@pytest.fixture(scope="session")
def scipy_calc():
    return create_zero_velocity_zero_min_altitude_calc("scipy_engine", "RK45")

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

def create_0_308_caliber_shot():
    drag_model = DragModel(
        bc=0.233,
        drag_table=TableG7,
        weight=Weight.Grain(155),
        diameter=Distance.Inch(0.308),
        length=Distance.Inch(1.2),
    )
    ammo = Ammo(drag_model, Velocity.MPS(914.6))
    gun = Weapon()
    shot = Shot(
        weapon=gun,
        ammo=ammo,
    )
    return shot

def find_max_height_robust(scipy_calc, shot_factory):
    shot = shot_factory()
    shot.relative_angle = Angular.Degree(90)
    try:
        hit_result = scipy_calc.fire(shot, Distance.Meter(1), time_step=0.001, extra_data=True)
    except RangeError as e:
        print(f'Range error et vertical shot {e}')
        hit_result = HitResult(shot, e.incomplete_trajectory, extra=True)
    apex_point = hit_result.flag(TrajFlag.APEX)
    return apex_point.height


def get_calc_step(scipy_calc):
    calc_step = scipy_calc._engine_instance.get_calc_step()
    cals_step_meters = Distance.Foot(calc_step) >> Distance.Meter
    print(f'{calc_step=} {cals_step_meters=}')
    assert cals_step_meters == pytest.approx(0.07619999999999999, abs=0.01)
    return cals_step_meters


def check_shot_out_of_range(scipy_calc, shot_factory, point_x, point_y):
    look_angle_in_degrees = math.degrees(math.atan2(point_y, point_x))
    shot = shot_factory()
    shot.look_angle = Angular.Degree(look_angle_in_degrees)
    distance_in_meters = math.sqrt(point_x ** 2 + point_y ** 2)
    # both find_zero_angle and zero_angle should throw OutOfRangeError
    with pytest.raises(OutOfRangeError):
        scipy_calc._engine_instance.find_zero_angle(shot, Distance.Meter(distance_in_meters))
    with pytest.raises(OutOfRangeError):
        scipy_calc._engine_instance.zero_angle(shot, Distance.Meter(distance_in_meters))


def check_shot_result_equivalent(scipy_calc, shot_factory, point_x, point_y):
    distance, look_angle = compute_look_angle_and_distance_for_point(point_x, point_y)
    print(f'{distance>>Distance.Meter=} {look_angle>>Angular.Degree=}')
    shot = shot_factory()
    shot.look_angle =look_angle

    # both find_zero_angle and zero_angle should throw OutOfRangeError
    find_zero_angle_error_flag = False
    find_zero_angle_error = None
    zero_angle_error_flag = False
    zero_angle_error = None
    find_zero_angle_result_degrees = float('NaN')
    zero_angle_result_degrees = float('NaN')

    try:
        find_zero_angle_result = scipy_calc._engine_instance.find_zero_angle(shot, distance)
        find_zero_angle_result_degrees = find_zero_angle_result>>Angular.Degree
        print(f"{find_zero_angle_result_degrees=}")
    except (OutOfRangeError, ZeroFindingError) as e:
        find_zero_angle_error_flag = True
        find_zero_angle_error = e
    try:
        zero_angle_result  = scipy_calc._engine_instance.zero_angle(shot, distance)
        zero_angle_result_degrees = zero_angle_result>>Angular.Degree
        print(f'{zero_angle_result_degrees=}')
    except  (OutOfRangeError, ZeroDivisionError) as e:
        print(f"zero_angle raised unexpected {e}")
        zero_angle_error_flag = True
        zero_angle_error = e
    if not find_zero_angle_error_flag and not zero_angle_error_flag:
        assert find_zero_angle_result_degrees == pytest.approx(zero_angle_result_degrees, abs = ANGLE_EPSILON_IN_DEGREES)
    else:
        assert find_zero_angle_error == zero_angle_error_flag, f"Error should occur both in find_zero_error:{find_zero_angle_error_flag=} and zero_angle:{zero_angle_error_flag=}"
        assert type(find_zero_angle_error)==type(zero_angle_error), f"Type of error should match: {find_zero_angle_error=} {zero_angle_error=}"


def check_shot_angle_equals(scipy_calc, shot_factory, point_x, point_y):
    distance, look_angle = compute_look_angle_and_distance_for_point(point_x, point_y)
    print(f'{distance>>Distance.Meter=} {look_angle>>Angular.Degree=}')
    shot = shot_factory()
    shot.look_angle =look_angle

    # both find_zero_angle and zero_angle should throw OutOfRangeError
    unexpected_find_zero_angle_error_flag = False
    unexpected_find_zero_angle_error = None
    unexpected_zero_angle_error_flag = False
    unexpected_zero_angle_error = None
    find_zero_angle_result_degrees = float('NaN')
    zero_angle_result_degrees = float('NaN')

    try:

        find_zero_angle_result = scipy_calc._engine_instance.find_zero_angle(shot, distance)
        find_zero_angle_result_degrees = find_zero_angle_result>>Angular.Degree
        print(f"{find_zero_angle_result_degrees=}")
    except (OutOfRangeError, ZeroFindingError) as e:
        print(f"find_zero_angle raised unexpected {e}")
        unexpected_find_zero_angle_error_flag = True
        unexpected_find_zero_angle_error = e
    try:
        zero_angle_result  = scipy_calc._engine_instance.zero_angle(shot, distance)
        zero_angle_result_degrees = zero_angle_result>>Angular.Degree
        print(f'{zero_angle_result_degrees=}')
    except  (OutOfRangeError, ZeroFindingError) as e:
        print(f"zero_angle raised unexpected {e}")
        unexpected_zero_angle_error_flag = True
        unexpected_zero_angle_error = e
    assert (not unexpected_find_zero_angle_error_flag) and (not unexpected_zero_angle_error_flag), f"{unexpected_find_zero_angle_error_flag=} != {unexpected_zero_angle_error_flag}"
    # at this point either both errors are present or both are absent
    if unexpected_find_zero_angle_error:
        assert type(unexpected_find_zero_angle_error)==type(unexpected_zero_angle_error)
    else:
        assert find_zero_angle_result_degrees == pytest.approx(zero_angle_result_degrees, abs = ANGLE_EPSILON_IN_DEGREES)


def compute_look_angle_and_distance_for_point(point_x_in_meters: float, point_y_in_meters: float):
    look_angle_in_degrees = math.degrees(math.atan2(point_y_in_meters, point_y_in_meters))
    distance_in_meters = (point_x_in_meters**2+point_y_in_meters**2)**0.5
    look_angle = Angular.Degree(look_angle_in_degrees)
    distance = Distance.Meter(distance_in_meters)
    # print(f'{point_x_in_meters=} {point_y_in_meters=} {sight_height_meters=} {sight_height_y=} {height_diff=} {look_angle=} {distance_in_meters=}')
    return distance, look_angle

def check_almost_max_height(scipy_calc, shot_factory):
    cals_step_meters = get_calc_step(scipy_calc)
    max_height = find_max_height_robust(scipy_calc, shot_factory)
    max_height_in_meters = max_height >> Distance.Meter
    point_x = cals_step_meters
    point_y = max_height_in_meters
    check_shot_out_of_range(scipy_calc, shot_factory, point_x, point_y)

def check_reachable_almost_max_height(scipy_calc, shot_factory):
    cals_step_meters = get_calc_step(scipy_calc)
    assert cals_step_meters == pytest.approx(0.07619999999999999, abs=0.01)
    max_height = find_max_height_robust(scipy_calc, shot_factory)
    max_height_in_meters = max_height >> Distance.Meter
    diffs = [2, 8.7, 10, 22]
    for diff in diffs:
        point_x = cals_step_meters
        point_y = max_height_in_meters - diff
        check_shot_result_equivalent(scipy_calc, shot_factory, point_x, point_y)

def check_find_angles_max_range(scipy_calc, shot_factory):
    shot = shot_factory()
    max_range, max_range_launch_angle = scipy_calc._engine_instance.find_max_range(shot)
    max_range_launch_angle_in_degrees = max_range_launch_angle >> Angular.Degree
    max_range_in_meters = max_range >> Distance.Meter
    print(f'for {shot_factory.__name__} { max_range_in_meters=} { max_range_launch_angle_in_degrees=}')
    zero_angle_shot = shot_factory()
    zero_launch_angle = scipy_calc.set_weapon_zero(zero_angle_shot, max_range)
    zero_launch_angle_in_degrees = zero_launch_angle >> Angular.Degree
    print(f"Zero for { max_range_in_meters=} m is elevation={zero_launch_angle_in_degrees} degree")
    assert max_range_launch_angle_in_degrees == pytest.approx(zero_launch_angle_in_degrees,
                                                              abs=ANGLE_EPSILON_IN_DEGREES)
    find_zero_angle_shot = shot_factory()
    max_launch_angle = scipy_calc.find_zero_angle(find_zero_angle_shot, max_range)
    find_zero_max_launch_angle_in_degrees = max_launch_angle >> Angular.Degree
    find_zero_max_launch_angle_in_degrees == pytest.approx(max_range_launch_angle_in_degrees,
                                                           abs=ANGLE_EPSILON_IN_DEGREES)


def check_handling_zero_point(scipy_calc, shot_factory):
    check_shot_angle_equals(scipy_calc, shot_factory, 0, 0)

def check_calc_same_step_shots(scipy_calc, shot_factory, step):
    check_shot_angle_equals(scipy_calc, shot_factory, step, step)

def test_find_max_height_23_mm(scipy_calc):
    shot_factory = create_23_mm_shot
    shot = shot_factory()
    shot.look_angle  = Angular.Degree(90)
    max_height, max_angle = scipy_calc._engine_instance.find_max_range(shot)
    max_height_in_meters_1 = max_height >> Distance.Meter
    print(f"1. { max_height_in_meters_1=} {max_angle>>Angular.Degree=}")
    max_height_2 = find_max_height_robust(scipy_calc, shot_factory)
    max_height_in_meters_2 = max_height_2 >> Distance.Meter
    print(f'2. {max_height_in_meters_2=}')
    assert max_height_in_meters_1==max_height_in_meters_2

def test_find_max_range_23_mm(scipy_calc):
    shot_factory = create_23_mm_shot
    shot = shot_factory()
    max_range, max_range_launch_angle = scipy_calc._engine_instance.find_max_range(shot)
    max_range_launch_angle_in_degrees = (max_range_launch_angle >> Angular.Degree)
    max_range_in_meters = (max_range >> Distance.Meter)
    print(f"{max_range_in_meters=} {max_range_launch_angle_in_degrees=}")
    assert max_range_in_meters==pytest.approx(7136.255, abs=0.01)
    assert max_range_launch_angle_in_degrees==pytest.approx(38.8236, abs=ANGLE_EPSILON_IN_DEGREES)

def create_7_62_mm_shot():
    diameter = Distance.Millimeter(7.62)
    length: Distance = Distance.Millimeter(32.5628)
    weight = Weight.Grain(180)
    dm = DragModel(bc=0.2860,
                   drag_table=TableG1,
                   weight=weight,
                   diameter=diameter,
                   length=length)
    ammo = Ammo(dm, mv=Velocity.MPS(800), powder_temp=Temperature.Celsius(20))
    gun = Weapon(sight_height=Distance.Millimeter(-100), twist=Distance.Millimeter(300))
    new_shot = Shot(weapon=gun, ammo=ammo)
    return new_shot

def test_7_62_point_mismatch(scipy_calc):
    point_x = 67.79956401327206
    point_y = 83.47708433996526
    shot = create_7_62_mm_shot()
    look_angle_wo_sight_degrees = math.degrees(math.atan2(point_y, point_x))
    sight_height_meters = shot.weapon.sight_height>>Distance.Meter
    height_diff_target_trajectory_start = point_y + sight_height_meters
    angle_from_start_degrees = math.degrees(math.atan2(height_diff_target_trajectory_start, point_x))
    print(f"{point_x=} {point_y=} {sight_height_meters=} { height_diff_target_trajectory_start=}")
    print(f"{look_angle_wo_sight_degrees=} {angle_from_start_degrees=}")
    print(f"{(point_x**2+height_diff_target_trajectory_start**2)**0.5=}")
    check_shot_angle_equals(scipy_calc, create_7_62_mm_shot, point_x, point_y)

TESTED_SHOTS = [create_23_mm_shot, create_0_308_caliber_shot, create_7_62_mm_shot]

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_set_weapon_zero_max_range(shot_factory, scipy_calc):
    check_find_angles_max_range(scipy_calc, shot_factory)

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_find_almost_max_height(shot_factory, scipy_calc):
    check_almost_max_height(scipy_calc, shot_factory)

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_handling_zero_point(shot_factory, scipy_calc):
    check_handling_zero_point(scipy_calc, shot_factory)

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_reachable_almost_max_height(shot_factory, scipy_calc):
    with PreferredUnitsContextManager():
        loadMetricUnits()
        print(f"{PreferredUnits=}")
        check_reachable_almost_max_height(scipy_calc, shot_factory)

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_calc_step_point_shots(shot_factory, scipy_calc):
    calc_step = get_calc_step(scipy_calc)
    check_calc_same_step_shots(scipy_calc, shot_factory, calc_step)

@pytest.mark.parametrize("shot_factory", TESTED_SHOTS)
def test_half_calc_step_point_shots(shot_factory, scipy_calc):
    calc_step = get_calc_step(scipy_calc)
    check_calc_same_step_shots(scipy_calc, shot_factory, calc_step/2)

def test_0_308_runtime_warning_point(scipy_calc):
    # this point leads to the situation, when one gets division by zero and NaN correction
    check_shot_out_of_range(scipy_calc, create_0_308_caliber_shot, 4733.942049290925, 3463.4247025051754)
