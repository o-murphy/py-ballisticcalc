??? api "API Documentation"

    [`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>

The way to define `projectile` properties in **py-ballisticcalc** is via Ammo dataclass.
Ammo instances are simply and reusable.

## Ammo initialization

Import the necessary types to create a Weapon instance
```python
from py_ballisticcalc import Ammo, Unit, DragModel
```

Then create a weapon
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
In this example, we use calls to `Unit` to initialize `Ammo` fields with specific unit types.
We also can do it using `float`'s then fields will be initialized with unit types defined in `PreferredUnit` class,
or we can directly specify the dimension with referencing to dimension type class

Fields of a `Ammo` can be accessed as normal attributes of `ammo` instance

Ammo instance is mutable object and field values can be changed through attribute assignment

!!! warning
    Direct assignment to access to attributes of `ammo` is restricted and not recommended, it can be not reinitialized properly after that

!!! note
    See the API documentation of [`Ammo`][py_ballisticcalc.munition.Ammo] for the class definition including a full list of methods and attributes.