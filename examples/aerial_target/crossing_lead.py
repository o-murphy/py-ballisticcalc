"""Lead (preemption) for an aerial target crossing the line of sight.

The target flies at a constant speed, level and perpendicular to the line of sight.
The bullet takes time `t` to reach the target, and the target moves while the bullet
is in flight, so the bullet must be aimed at the point where the target will be.
That point depends on `t`, and `t` depends on that point, so we iterate:

    1. t = time of flight to the target's current position
    2. move the target forward by `speed * t`
    3. t = time of flight to the new position, repeat until `t` stops changing

`Calculator.aim()` gives the time of flight and the vertical hold for one position
in a single call. The bullet flies in a vertical plane towards the predicted point,
so its look angle and slant distance are recomputed from exact 3D geometry on every
iteration.
"""

import copy
import math
from dataclasses import dataclass

from py_ballisticcalc import *

PreferredUnits.distance = Unit.Meter
PreferredUnits.adjustment = Unit.Mil
PreferredUnits.velocity = Unit.MPS

LOOK_ANGLE_DEG = 45.0  # look angle to the target
TARGET_HEIGHT_M = 500.0  # target height above the shooter
TARGET_SPEED_MPS = 50.0  # target speed, perpendicular to the line of sight
ZERO_DISTANCE_M = 200.0

MAX_ITERATIONS = 10
CONVERGENCE_THRESHOLD_S = 0.001  # stop when the time of flight changes less than this

calc = Calculator()


def get_zero_shot() -> Shot:
    dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
    ammo = Ammo(dm, 850, Temperature.Celsius(15), use_powder_sensitivity=True)
    ammo.calc_powder_sens(820, Temperature.Celsius(0))
    weapon = Weapon(sight_height=9, twist=15)
    atmo = Atmo(altitude=Distance.Meter(1000), temperature=Unit.Celsius(5), humidity=0.5)
    return Shot(weapon=weapon, ammo=ammo, atmo=atmo)


@dataclass
class CrossingLead:
    time_of_flight: float  # seconds
    iterations: int
    converged: bool
    distance: float  # slant distance to the meeting point, m
    lateral_offset: float  # target travel during the time of flight, m
    horizontal_lead: Angular  # to the right of the current line of sight
    vertical_hold: Angular  # above the current line of sight: bullet drop and look angle change
    shot: Shot  # shot aimed at the meeting point, `vertical_hold` already applied


def aim_at(zero: Shot, x: float, y: float, z: float):
    """Aim at the point (x: horizontal distance, y: height, z: lateral offset), meters.

    Returns the trajectory point at that position, the vertical hold relative to the
    weapon zero, the look angle (rad) and the shot with the look angle set.
    """
    horizontal_range = math.hypot(x, z)
    look_angle = math.atan2(y, horizontal_range)
    slant_distance = math.hypot(horizontal_range, y)

    shot = copy.copy(zero)
    shot.look_angle = Angular.Radian(look_angle)
    hold, _windage, point = calc.aim(shot, Distance.Meter(slant_distance))
    return point, hold, look_angle, shot


def calculate_crossing_lead(
    zero: Shot,
    look_angle_deg: float = LOOK_ANGLE_DEG,
    target_height_m: float = TARGET_HEIGHT_M,
    target_speed_mps: float = TARGET_SPEED_MPS,
    max_iterations: int = MAX_ITERATIONS,
    convergence_threshold: float = CONVERGENCE_THRESHOLD_S,
) -> CrossingLead:
    x = target_height_m / math.tan(math.radians(look_angle_deg))  # horizontal distance
    y = target_height_m
    initial_look_angle = math.atan2(y, x)

    point, hold, look_angle, shot = aim_at(zero, x, y, 0.0)
    tof = point.time

    converged = False
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        point, hold, look_angle, shot = aim_at(zero, x, y, target_speed_mps * tof)
        converged = abs(point.time - tof) < convergence_threshold
        tof = point.time
        if converged:
            break

    z = target_speed_mps * tof
    shot.relative_angle = hold
    return CrossingLead(
        time_of_flight=tof,
        iterations=iterations,
        converged=converged,
        distance=math.sqrt(x**2 + y**2 + z**2),
        lateral_offset=z,
        horizontal_lead=Angular.Radian(math.atan2(z, x)),
        vertical_hold=Angular.Radian((hold >> Angular.Radian) + (look_angle - initial_look_angle)),
        shot=shot,
    )


def main():
    zero = get_zero_shot()
    zero_distance = Distance.Meter(ZERO_DISTANCE_M)
    zero_elevation = calc.set_weapon_zero(zero, zero_distance)
    print(f"Zero at {zero_distance}: {zero_elevation << Angular.Mil}")

    lead = calculate_crossing_lead(zero)

    print("\n--- Input ---")
    print(f"Look angle:     {LOOK_ANGLE_DEG:.1f}°")
    print(f"Target height:  {TARGET_HEIGHT_M:.1f} m")
    print(f"Target speed:   {TARGET_SPEED_MPS:.1f} m/s, perpendicular to the line of sight")

    print("\n--- Result ---")
    print(f"Time of flight:           {lead.time_of_flight:.3f} s")
    print(f"Distance to meeting point:{lead.distance:9.2f} m")
    print(f"Target travel in flight:  {lead.lateral_offset:.2f} m")
    print(f"Horizontal lead:          {lead.horizontal_lead >> Angular.Mil:.2f} mil "
          f"({lead.horizontal_lead >> Angular.MOA:.2f} MOA)")
    print(f"Vertical hold:            {lead.vertical_hold >> Angular.Mil:.2f} mil")
    print(f"Iterations:               {lead.iterations} ({'converged' if lead.converged else 'NOT converged'})")

    # Check: fire with the hold applied at the meeting point. The bullet must arrive on the
    # sight line at the same time the target does.
    horizontal_range = Distance.Meter(math.hypot(TARGET_HEIGHT_M / math.tan(math.radians(LOOK_ANGLE_DEG)),
                                                 lead.lateral_offset))
    hit = calc.fire(lead.shot, trajectory_range=horizontal_range, trajectory_step=horizontal_range,
                    flags=TrajFlag.NONE, raise_range_error=False)[-1]
    print(f"\nCheck: bullet time {hit.time:.3f} s vs target time {lead.time_of_flight:.3f} s, "
          f"miss {hit.slant_height >> Distance.Centimeter:.2f} cm from the sight line")


if __name__ == "__main__":
    main()
