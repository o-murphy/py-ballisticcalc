# Units and Dimensions

This project provides a comprehensive type-safe unit conversion system for the following dimensions and units:

* [Angle][py_ballisticcalc.unit.Angular]: `radian`, `degree`, `MOA`, `mil`, `mrad`, `thousandth`, `inch/100yd`, `cm/100m`, `o'clock`
* [Distance][py_ballisticcalc.unit.Distance]: `inch`, `foot`, `yard`, `mile`, `nautical mile`, `mm`, `cm`, `m`, `km`, `line`
* [Energy][py_ballisticcalc.unit.Energy]: `foot-pound`, `joule`
* [Pressure][py_ballisticcalc.unit.Pressure]: `mmHg`, `inHg`, `bar`, `hPa`, `PSI`
* [Temperature][py_ballisticcalc.unit.Temperature]: `Fahrenheit`, `Celsius`, `Kelvin`, `Rankine`
* [Time][py_ballisticcalc.unit.Time]: `second`, `minute`, `millisecond`, `microsecond`, `nanosecond`, `picosecond`
* [Velocity][py_ballisticcalc.unit.Velocity]: `m/s`, `km/h`, `ft/s`, `mph`, `knots`
* [Weight][py_ballisticcalc.unit.Weight]: `grain`, `ounce`, `gram`, `pound`, `kilogram`, `newton`

The system uses a base class [`GenericDimension`][py_ballisticcalc.unit.GenericDimension] with specialized subclasses for each physical dimension. Each dimension maintains its values internally in a fixed raw unit (e.g., inches for distance, m/s for velocity) and provides conversion methods to any supported unit within that dimension.

## Features
* Type-safe unit conversions and arithmetic operators
* Flexible conversion syntax with operator overloading
* String parsing and unit alias resolution
* Default/Preferred units are configurable via [PreferredUnits][py_ballisticcalc.unit.PreferredUnits] singleton.

## Examples
```python
>>> # ----------------- Creation and conversion -----------------
>>> d = Distance.Yard(100)  
>>> d.convert(Unit.Meter)      # Conversion method -> Distance
<Distance: 91.4m (3600.0)>
>>> d << Distance.Feet         # Conversion operator -> Distance
<Distance: 300.0ft (3600.0)>
>>> d.get_in(Distance.Foot)    # Conversion method -> float
300.0
>>> d >> Distance.Inch         # Conversion operator -> float
3600.0
>>> # ----------------------- Arithmetic -----------------------
>>> d - 30
<Distance: 70.0yd (2520.0)>
>>> d + Distance.Feet(2)
<Distance: 100.7yd (3624.0)>
>>> 3 * d
<Distance: 300.0yd (10800.0)>
>>> d / 2
<Distance: 50.0yd (1800.0)>
>>> d / Unit.Foot(3)
100.0
```    
