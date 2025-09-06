???+ api "API Documentation"

    [`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>

[Ammo][py_ballisticcalc.munition.Ammo] encapsulates projectile characteristics and muzzle velocity, including optional powder temperature sensitivity. Provide a [DragModel][py_ballisticcalc.drag_model.DragModel] (BC + table, or multi-BC) and optionally size/weight to enable spin-drift estimates.

## Ammo initialization

Import the necessary types to create an Ammo instance:
```python
from py_ballisticcalc import Ammo, Unit, DragModel
```

In this example, we use [Unit][py_ballisticcalc.unit.Unit] helpers to initialize [Ammo][py_ballisticcalc.munition.Ammo] fields with specific units. You can also pass raw floats; they’ll be coerced to [PreferredUnits][py_ballisticcalc.unit.PreferredUnits].
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
