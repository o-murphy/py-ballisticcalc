??? api "API Documentation"

    [`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>

`Ammo` encapsulates projectile characteristics and muzzle velocity, including optional powder temperature sensitivity. Provide a `DragModel` (BC + table, or multi-BC) and optionally size/weight to enable spin-drift estimates.

## Ammo initialization

Import the necessary types to create a Weapon instance
```python
from py_ballisticcalc import Ammo, Unit, DragModel
```

Then create ammo
```python
ammo = Ammo(
    dm=DragModel(
        bc=0.381,
        drag_table=TableG7,
        weight=Unit.Grain(300),
        length=Unit.Inch(1.7),
        diameter=Unit.Inch(0.338),
    ),
    mv=Unit.MPS(815),
    powder_temp=Unit.Celsius(15),
    temp_modifier=0.123,
    use_powder_sensitivity=True,
)
```
In this example, we use `Unit` helpers to initialize `Ammo` fields with specific units. You can also pass raw floats; they’ll be coerced to `PreferredUnits`.

Fields of an `Ammo` are accessible as attributes. `Ammo` is mutable; changing fields updates behavior accordingly.

!!! warning
    Avoid bypassing property setters for complex fields; use provided attributes and helpers to ensure consistent state.

Ammo attributes and helpers:

* [`dm`][py_ballisticcalc.munition.Ammo.dm]: DragModel for projectile
* [`mv`][py_ballisticcalc.munition.Ammo.mv]: Muzzle Velocity
* [`powder_temp`][py_ballisticcalc.munition.Ammo.powder_temp]: Baseline temperature that produces the given mv
* [`temp_modifier`][py_ballisticcalc.munition.Ammo.temp_modifier]: Change in velocity w temperature: % per 15°C.
* [`use_powder_sensitivity`][py_ballisticcalc.munition.Ammo.use_powder_sensitivity]: Flag to enable adjusting muzzle velocity to powder temperature
* [`calc_powder_sens`][py_ballisticcalc.munition.Ammo.calc_powder_sens]: Method to calculate powder temperature sensitivity coefficient
* [`get_velocity_for_temp`][py_ballisticcalc.munition.Ammo.get_velocity_for_temp]: Method to get adjusted muzzle velocity to powder sensitivity

!!! note
    See the API documentation of [`Ammo`][py_ballisticcalc.munition.Ammo] for the class definition including a full list of methods and attributes.