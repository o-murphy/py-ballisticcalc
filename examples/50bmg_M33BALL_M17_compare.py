"""Example of library usage"""
# import RKballistic

import logging
import math
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger
from matplotlib import pyplot as plt

logger.setLevel(logging.DEBUG)

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter

ENGINE = "cythonized_rk4_engine"
TRAJECTORY_STEP = Unit.Meter(10.0)

TRAJECTORY_LINEWIDTH = 2
REFERENCE_LINEWIDTH = 1
SIGHT_LINE_STYLE = {"linestyle": "--", "color": "tab:purple", "linewidth": REFERENCE_LINEWIDTH, "label": "Sight line"}
ADJUSTED_SIGHT_LINE_STYLE = {
    "linestyle": "--", "color": "tab:pink", "linewidth": REFERENCE_LINEWIDTH, "label": "Adjusted sight line (hold)"
}
BARREL_LINE_STYLE = {"linestyle": ":", "color": "tab:red", "linewidth": REFERENCE_LINEWIDTH, "label": "Barrel line"}


class TestCase:
    sh = Unit.Centimeter(15.0)
    ptemp = Unit.Celsius(15.0)
    zero = Unit.Meter(500.0)
    twist = Unit.Inch(15.0)
    target = Unit.Meter(1000.0)
    # Slant angle of the shot to the target (zeroing itself is still done on level ground).
    look_angle = Unit.Degree(5.0)


class M33BALL(TestCase):
    label = "M33 BALL"
    weight = Unit.Grain(647.0)
    diameter = Unit.Inch(0.51)
    length = Unit.Inch(2.28)
    bc = 0.336
    model = TableG7
    psens = 0.01
    mv = Unit.MPS(838.2)


class M17(TestCase):
    label = "M17"
    weight = Unit.Grain(643.0)
    diameter = Unit.Inch(0.51)
    length = Unit.Inch(2.31)
    bc = 0.407
    model = TableG7
    psens = 0.01
    mv = Unit.MPS(885.4)


def make_shot(data, zero_elevation: Angular | None = None, hold: Angular | None = None):
    """Build and fire a shot for `data`.

    If `zero_elevation` / `hold` are given, the weapon is set to that flat zero
    and holdover (i.e. someone else's firing solution) instead of computing
    its own for this load.
    """
    weapon = Weapon(sight_height=data.sh, twist=data.twist)
    ammo = Ammo(
        dm=DragModel(data.bc, data.model, data.weight, data.diameter, data.length),
        mv=data.mv,
        powder_temp=data.ptemp,
        temp_modifier=data.psens,
        use_powder_sensitivity=True,
    )

    atmo = Atmo.icao()
    calc = Calculator(engine=ENGINE)

    if zero_elevation is None:
        zero_shot = Shot(weapon=weapon, ammo=ammo, atmo=atmo)
        zero_elevation = calc.set_weapon_zero(zero_shot, data.zero)
    weapon.zero_elevation = zero_elevation

    if hold is None:
        # Firing solution for this load at the inclined target, on top of the flat zero.
        aim_shot = Shot(weapon=weapon, ammo=ammo, atmo=atmo, look_angle=data.look_angle)
        aim_elevation = calc.barrel_elevation_for_target(aim_shot, data.target)
        hold = Angular.Radian((aim_elevation >> Angular.Radian) - (zero_elevation >> Angular.Radian))

    shot = Shot(weapon=weapon, ammo=ammo, atmo=atmo, look_angle=data.look_angle, relative_angle=hold)
    shot_result = calc.fire(shot, data.target, trajectory_step=TRAJECTORY_STEP)
    return shot_result, zero_elevation, hold


def compare(base, *comparisons):
    base_result, base_zero_elevation, base_hold = make_shot(base)
    comparison_results = [make_shot(load, zero_elevation=base_zero_elevation, hold=base_hold)[0] for load in comparisons]
    loads_and_results = [(base, base_result), *zip(comparisons, comparison_results)]

    def label_for(data):
        return f"{data.label} (base)" if data is base else data.label

    fig, ax = plt.subplots()
    for data, result in loads_and_results:
        df = result.dataframe()
        ax.plot(df.distance, df.height, label=label_for(data), linewidth=TRAJECTORY_LINEWIDTH)

    max_distance = max(result.dataframe().distance.max() for _, result in loads_and_results)
    max_distance_drop = PreferredUnits.distance(max_distance) >> PreferredUnits.drop
    look_angle_rad = TestCase.look_angle >> Angular.Radian
    hold_rad = base_hold >> Angular.Radian
    zero_elevation_rad = base_zero_elevation >> Angular.Radian
    sight_height_drop = TestCase.sh >> PreferredUnits.drop

    # Raw sight line: where the scope's optical axis points (look_angle only, no holdover)
    ax.plot([0, max_distance], [0, max_distance_drop * math.tan(look_angle_rad)], **SIGHT_LINE_STYLE)

    # Adjusted sight line: point of aim including the holdover dialed/held for this shot
    ax.plot(
        [0, max_distance], [0, max_distance_drop * math.tan(look_angle_rad + hold_rad)], **ADJUSTED_SIGHT_LINE_STYLE
    )

    # Barrel line: physical bore direction, offset below the sight line by sight_height
    barrel_elevation_rad = look_angle_rad + zero_elevation_rad + hold_rad
    ax.plot(
        [0, max_distance],
        [-sight_height_drop, max_distance_drop * math.tan(barrel_elevation_rad) - sight_height_drop],
        **BARREL_LINE_STYLE,
    )

    ax.set_xlabel(f"Distance, {PreferredUnits.distance.symbol}")
    ax.set_ylabel(f"Height, {PreferredUnits.drop.symbol}")
    load_labels = " vs ".join(label_for(data) for data, _ in loads_and_results)
    ax.set_title(f"{load_labels} - same zero ({TestCase.zero}), {TestCase.target} target, look angle {TestCase.look_angle}")
    ax.legend()
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)

    plt.show()


if __name__ == '__main__':
    # Whichever load is BASE gets zeroed and gets its own firing solution (hold) worked
    # out for the inclined target. The others are fired with that exact same zero + hold,
    # to see how far they land from the point BASE was actually aimed at.
    # To compare from the other load's perspective, just swap which one is BASE.
    BASE = M33BALL
    COMPARISONS = [M17]
    compare(BASE, *COMPARISONS)