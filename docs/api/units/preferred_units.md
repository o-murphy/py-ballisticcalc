::: py_ballisticcalc.unit.PreferredUnits
    options:
        show_signature: false
        separate_signature: false


### Unit Presets

You can define and load `PreferredUnits` presets from `toml` files.  There are three such preset files in `/assets` that have predefined loader functions that can be invoked as follows:

```python
from py_ballisticcalc import loadImperialUnits, loadMetricUnits, loadMixedUnits

loadImperialUnits()
loadMetricUnits()
loadMixedUnits()
```

(Use just one of these methods – only the last one called counts.)

#### Imperial Units

From **`assets/.pybc-imperial.toml`**:

```toml
--8<-- "py_ballisticcalc/assets/.pybc-imperial.toml:pybc-imperial"
```

#### Metric Units

From **`assets/.pybc-metrics.toml`**:

```toml
--8<-- "py_ballisticcalc/assets/.pybc-metrics.toml:pybc-metric"
```

#### Mixed Units

*Mixed* sets:

* metric units for distance, velocity, target, atmosphere
* imperial for bullet and gun dimensions.

From **`assets/.pybc-mixed.toml`**:

```toml
--8<-- "py_ballisticcalc/assets/.pybc-mixed.toml:pybc-mixed"
```


::: py_ballisticcalc.unit.UnitProps

::: py_ballisticcalc.unit.UnitPropsDict
    options:
        show_signature: false
        separate_signature: false
        show_attribute_values: false
        show_signature_annotations: false

```python
--8<-- "py_ballisticcalc/unit.py:UnitPropsDict"
```
