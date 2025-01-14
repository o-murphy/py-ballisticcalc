??? api "API Documentation"

    [`py_ballisticcalc.munition.Weapon`][py_ballisticcalc.munition.Weapon]<br>

The way to define `weapon` properties in **py-ballisticcalc** is via Weapon dataclass.
Weapon instances are simply and reusable.

## Weapon initialization

Import the necessary types to create a Weapon instance
```python
from py_ballisticcalc import Weapon, Unit, Sight
```

Then create a weapon
```python
weapon = Weapon(
    sight_height=Unit.Inch(2.),
    twist=Unit.Inch(10.),
    zero_elevation=Unit.Mil(0),
    sight=Sight(
        'FFP', 2,
        h_click_size=Unit.Mil(0.2),
        v_click_size=Unit.Mil(0.2)
    )
)
```
In this example, we use calls to `Unit` to initialize `Weapon` fields with specific unit types.
We also can do it using `float`'s then fields will be initialized with unit types defined in `PreferredUnit` class,
or we can directly specify the dimension with referencing to dimension type class

Fields of a `Weapon` can be accessed as normal attributes of `weapon` instance

Weapon instance is mutable object and field values can be changed through attribute assignment

!!! note
    See the API documentation of [`Weapon`][py_ballisticcalc.munition.Weapon] for the class definition including a full list of methods and attributes.