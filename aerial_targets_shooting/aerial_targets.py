"""Example of library usage"""
import math

from py_ballisticcalc import *

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter


def get_trajectory(pitch):
    # set_global_use_powder_sensitivity(True)  # enable muzzle velocity correction my powder temperature

    # define params with default prefer_units
    length = Distance.Inch(2.3)

    weapon = Weapon(sight_height=Unit.Centimeter(9.5), twist=15)
    dm = DragModel(0.62, TableG1, 661, 0.51, length=length)
    ammo = Ammo(dm, 900)

    zero_atmo = Atmo(
        altitude=Unit.Meter(150),
        pressure=Unit.hPa(1000),
        temperature=Unit.Celsius(15),
        humidity=50
    )
    zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
    zero_distance = Distance.Meter(500)

    calc = Calculator()
    calc.set_weapon_zero(zero, zero_distance)

    shot = Shot(look_angle=pitch, weapon=weapon, ammo=ammo, atmo=zero_atmo)
    shot_result = calc.fire(shot, Distance.Meter(1001), Distance.Meter(100))
    return shot_result


def calculate_vertical_preemption(target_speed, target_size, initial_target_distance, time_of_flight,
                                  target_azimuth_rad,
                                  pitch_rad):
    ## pitch change depends on target flight direction (now not depends on x travel)

    # x - horizontal move
    # y - distance to shooter
    # z - altitude

    target_altitude_z = math.sin(pitch_rad) * initial_target_distance
    initial_target_distance_y = math.cos(pitch_rad) * initial_target_distance

    target_nose_travel_distance = target_speed * time_of_flight + target_size
    target_nose_travel_distance_y = math.cos(target_azimuth_rad) * target_nose_travel_distance

    target_nose_travel_distance_projected_y = initial_target_distance_y - target_nose_travel_distance_y

    pitch_projected_rad = math.atan(target_altitude_z / target_nose_travel_distance_projected_y)

    return pitch_rad - pitch_projected_rad


def calculate_horizontal_preemption(target_speed, target_size, initial_target_distance_y, time_of_flight,
                                    target_azimuth_rad,
                                    pitch_rad):
    # FIXME: have also depends on pitch

    target_nose_travel_distance = target_speed * time_of_flight + target_size
    target_nose_travel_distance_y = math.cos(target_azimuth_rad) * target_nose_travel_distance
    target_nose_travel_distance_x = math.sin(target_azimuth_rad) * target_nose_travel_distance

    target_nose_travel_distance_projected_y = initial_target_distance_y - target_nose_travel_distance_y

    preemption_rad = math.atan(target_nose_travel_distance_x / target_nose_travel_distance_projected_y)
    return preemption_rad


def calculate_preemption(target_speed, target_size, initial_distance, time_of_flight, target_azimuth, pitch):
    """
    Розрахунок кута упередження маючи швидкість і розмір цілі, початкову відстань до цілі.

    :param target_speed: Швидкість цілі (м/с)
    :param target_size: Довжина цілі (м)
    :param initial_distance: Початкова відстань до цілі (м)
    :return: Кут упередження в градусах
    """

    target_azimuth_rad = math.radians(target_azimuth)
    pitch_rad = math.radians(pitch)  # FIXME: have also depends on pitch

    preemption_x = calculate_horizontal_preemption(target_speed, target_size, initial_distance, time_of_flight,
                                                   target_azimuth_rad, pitch_rad)
    preemption_y = calculate_vertical_preemption(target_speed, target_size, initial_distance, time_of_flight,
                                                 target_azimuth_rad,
                                                 pitch_rad)

    return Unit.Radian(preemption_x), Unit.Radian(preemption_y)


def get_one(target_speed, target_size, hor_target_angle, pitch):
    shot_result = get_trajectory(pitch)

    print(f"{target_size=}m, {target_speed=}m/s")
    print("lead angle, time, distance, velocity")
    for p in shot_result[1:]:
        time = p.time
        lax, lay = calculate_preemption(target_speed >> Unit.MPS,
                                        target_size >> Unit.Meter,
                                        p.distance >> Unit.Meter,
                                        p.time,
                                        hor_target_angle >> Unit.Degree,
                                        p.angle >> Unit.Degree)
        # if a > max_lead_angle:
        #     continue
        print(f"{lax << Unit.Degree} ({lax << Unit.Thousandth}), "
              f"{lay << Unit.Degree} ({lay << Unit.Thousandth}), "
              f"{time:.02f}s, {p.distance >> Unit.Meter:.0f}m, "
              f"{p.velocity >> Unit.MPS:.0f}m/s")


target_speed = Unit.MPS(50)
target_size = Unit.Meter(3)
max_lead_angle = Unit.Degree(6.21)

get_one(target_speed, target_size, hor_target_angle=Unit.Degree(90), pitch=Unit.Degree(20))
get_one(target_speed, target_size, hor_target_angle=Unit.Degree(90), pitch=Unit.Degree(30))

print((Unit.Thousandth(5) >> Unit.CmPer100m) / (1 / 5))
