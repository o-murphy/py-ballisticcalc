"""Example of library usage"""
import math

from py_ballisticcalc import *
from py_ballisticcalc.trajectory_calc import Vector

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter


def get_trajectory(look_angle):
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

    shot = Shot(look_angle=look_angle, weapon=weapon, ammo=ammo, atmo=zero_atmo)
    shot_result = calc.fire(shot, Distance.Meter(1001), Distance.Meter(100))
    return shot_result



    
target_speed = Unit.MPS(50)
target_size = Unit.Meter(3)
#max_lead_angle = Unit.Degree(6.21)
look_angle = Unit.Degree(20)
target_direction = Unit.Degree(45)
target_azimuth = Unit.Degree(15)

shot_result = get_trajectory(look_angle)


def target_trajectory(target_speed, target_length, initial_target_look_distance, time_of_flight, direction_rad, look_angle_rad, azimuth_rad):
    
    t_length_vector = Vector(
        x=math.sin(direction_rad) * target_length,
        y=math.cos(direction_rad) * target_length,
        z=0
    )
    
    t_distance_vector = Vector(
        x=0,
        y=math.cos(look_angle_rad) * initial_target_look_distance,
        z=math.sin(look_angle_rad) * initial_target_look_distance
    )
    
    t_velocity_vector = Vector(
        x=math.sin(direction_rad) * target_speed,
        y=math.cos(direction_rad) * target_speed,
        z=0
    )
    
    #print(f'{t_velocity_vector=}')
    t_traveled_vector = t_velocity_vector * time_of_flight
    #print(f'{t_traveled_vector=}')
    #print(f'{t_distance_vector=}')
    #t_pos_at_time = t_distance_vector - #t_length_vector - t_traveled_vector
    t_pos_at_time = t_distance_vector - t_traveled_vector
    #print(time_of_flight, f'{t_pos_at_time.x:.02f}  {t_pos_at_time.y:.02f}  {t_pos_at_time.z:.02f}')
    #print(t_pos_at_time)
    #print()
    
    look_angle_at_time = math.atan(t_pos_at_time.z/t_pos_at_time.y)
    
    distance = t_pos_at_time.z / math.sin(look_angle_at_time)
    
    
    
    x_shift = -math.atan(t_pos_at_time.x / distance)
    
    azimuth_at_time = azimuth_rad-x_shift
    
    if x_shift != 0:
        distance = t_pos_at_time.x / math.sin(x_shift)
        
    y_shift = -(look_angle_at_time-look_angle_rad)
    
    print(dict(
        time=time_of_flight,
        x_shift=Unit.Radian(x_shift),
        y_shift=Unit.Radian(y_shift),
        distance=Unit.Meter(distance),
        elevation=Unit.Radian(look_angle_at_time),
        azimuth=Unit.Radian(azimuth_at_time)
    ))
    

print(f"{target_size << Unit.Meter}, {target_speed << Unit.MPS}")
print("lead angle, time, distance, velocity\n")
for i in range(10):
    time = i/10
    target_trajectory(
        target_speed >> Unit.MPS, 
        target_size >> Unit.Meter,
        500,
        time,
        target_direction >> Unit.Radian,
        look_angle >> Unit.Radian,
        target_azimuth >> Unit.Radian
    )

#print('\n', (Unit.Thousandth(5) >> Unit.CmPer100m) / (1 / 5))
