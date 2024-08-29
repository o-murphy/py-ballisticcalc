import math

from py_ballisticcalc import *
from aerial_targets_shooting.aerial_target import *
from math import cos

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Thousandth
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter
PreferredUnits.angular = Angular.Degree
PreferredUnits.pressure = Pressure.hPa

weapon = Weapon(sight_height=9.5, twist=15)
dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
ammo = Ammo(dm, 900)
zero_atmo = Atmo(altitude=150, pressure=1000, temperature=15, humidity=50)
zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
calc = Calculator()
calc.set_weapon_zero(zero, 500)


def get_trajectory_for_look_angle(distance, look_angle):
    shot = Shot(look_angle=look_angle,
                weapon=weapon,
                ammo=ammo,
                atmo=zero_atmo)
    shot_result = calc.fire(shot, distance + 0.1, distance)
    return shot_result


look_angle = Angular.Degree(20)
look_distance = 1000
target = AerialTarget(Velocity.MPS(50),
                      look_distance,
                      Angular.Degree(90),
                      Angular.Degree(look_angle), Angular.Degree(0),
                      Distance.Meter(3))

# we calculate the minimum flight time of the bullet to the target, the actual distance and lead angle for this time. This is not necessary, but it reduces the number of iterations for finding the point of intersection of trajectories
shot_result = get_trajectory_for_look_angle(
    look_distance * cos(look_angle >> Unit.Radian), look_angle
)
flight_time = shot_result[-1].time
_, pos = target.at_time(flight_time)
print(pos)

# initial data to find trajectories crossing point
initial_look_angle = pos.look_angle >> Unit.Radian
initial_distance = (pos.look_distance >> Unit.Meter) * cos(look_angle >> Unit.Radian)

# minimal time delta to have a possibility to shoot the target
time_delta_coeff = 1 / 5
time_delta = (target.length >> Unit.Meter) * time_delta_coeff / (target.speed >> Unit.MPS)

# calculate look_angle and distance change for time Delta
_, pos = target.at_time(time_delta)
look_angle_delta = pos.y_shift >> Unit.Radian
look_distance_delta = ((pos.look_distance >> Unit.Meter) - look_distance)
distance_delta = look_distance_delta * cos(look_angle >> Unit.Radian)
print(pos)

# find trajectories crossing point
crossing_radius = 1e6
while True:
    initial_distance += distance_delta
    initial_look_angle += look_angle_delta

    shot_result = get_trajectory_for_look_angle(
        initial_distance, initial_look_angle
    )

    flight_time = shot_result[-1].time
    _, pos = target.at_time(flight_time)

    cur_shot_distance = shot_result[-1].distance >> Unit.Meter
    cur_target_distance = (pos.look_distance >> Unit.Meter) * cos(pos.look_angle >> Unit.Radian)
    print(cur_shot_distance, cur_target_distance)

    if abs(pos.look_angle >> Unit.Degree) > 90:
        raise RuntimeError('Impossible look angle')

    if abs(pos.x_shift >> Unit.Degree) > 180:
        raise RuntimeError('Impossible horizontal preemption angle')

    if cur_shot_distance <= cur_target_distance:
        if abs(cur_target_distance - cur_shot_distance) >= crossing_radius:
            raise RuntimeError('Impossible target for this ammo')
        crossing_radius = abs(cur_target_distance - cur_shot_distance)
        continue

    print("Found:")
    print(f"{flight_time:.3f}, {cur_shot_distance:.2f}, {cur_target_distance:.2f}, "
          f"{cur_shot_distance / math.cos(look_angle >> Unit.Radian):.2f}, "
          f"{cur_target_distance / math.cos(look_angle >> Unit.Radian):.2f}")
    break

# print preemption and adjustment
print(pos)
# print(shot_result[-1])

