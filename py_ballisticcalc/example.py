"""Example of ballistic calculation library usage.

The example demonstrates:
    - Setting preferred units for consistent calculations
    - Creating drag models with ballistic coefficients
    - Configuring ammunition with powder temperature sensitivity
    - Setting up weapon characteristics (sight height, twist rate)
    - Defining atmospheric conditions (pressure, temperature, humidity, altitude)
    - Adding wind conditions for realistic trajectory calculation
    - Performing zero calculation and trajectory firing
    - Displaying formatted trajectory results

Example:
    Run this script directly to see a complete ballistic calculation:
        $ python -m py_ballisticcalc.example
    This will output rows of trajectory data points.

See Also:
    - py_ballisticcalc.interface.Calculator: Main calculation interface
    - py_ballisticcalc.conditions.Shot: Shot configuration class
    - py_ballisticcalc.munition: Weapon and ammunition classes
    - py_ballisticcalc.unit.PreferredUnits: Default unit configuration
"""
from typing import List

from py_ballisticcalc import (Ammo, Atmo, Calculator, Distance, DragModel,
        PreferredUnits, Shot, TableG7, TrajectoryData, Unit, Weapon, Wind
)

# Modify default Units
PreferredUnits.velocity = Unit.FPS
PreferredUnits.temperature = Unit.Celsius
PreferredUnits.distance = Unit.Meter
PreferredUnits.sight_height = Unit.Centimeter

# Define ammunition parameters
weight: float = 168  # Projectile weight in grains (PreferredUnits.weight)
diameter: float = 0.308  # Bullet diameter in inches (PreferredUnits.diameter)
length: Distance = Unit.Inch(1.282)
dm: DragModel = DragModel(0.223, TableG7, weight, diameter, length)
ammo: Ammo = Ammo(dm, 2750, 15, use_powder_sensitivity=True)
ammo.calc_powder_sens(2723, 0)  # Calibrate powder temperature sensitivity
gun: Weapon = Weapon(sight_height=6, twist=12)
# Define atmospheric conditions
current_atmo: Atmo = Atmo(
    altitude=110,      # meters above sea level (PreferredUnits.distance)
    pressure=29.8,     # barometric pressure in "Hg (PreferredUnits.pressure)
    temperature=15,    # degrees Celsius
    humidity=72        # relative humidity (%)
)

# Define wind conditions
current_winds: List[Wind] = [Wind(
    velocity=2,         # wind speed in PreferredUnits.velocity
    direction_from=90   # wind direction in degrees (90 = left to right crosswind)
)]

# Create shot configuration
shot: Shot = Shot(
    weapon=gun,
    ammo=ammo,
    atmo=current_atmo,
    winds=current_winds
)

# Initialize calculator and set zero
calc: Calculator = Calculator()
calc.set_weapon_zero(shot, Unit.Meter(100))

# Calculate trajectory
shot_result = calc.fire(
    shot,
    trajectory_range=1000,  # meters (PreferredUnits.distance)
    trajectory_step=100     # meter intervals (PreferredUnits.distance)
)

# Display results
print(tuple(TrajectoryData._fields))
for p in shot_result:
    print(p.formatted())
