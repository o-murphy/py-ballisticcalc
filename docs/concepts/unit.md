# Units and Dimensions

This project uses a lightweight, explicit unit system with strongly-typed quantities like `Distance`, `Velocity`, and `Angular`. Preferred display/IO units are configurable via `PreferredUnits`.

Common patterns:

- Arithmetic between compatible dimensions returns the same type.
- Use shift operators to convert: `distance >> Unit.Yard`.
- Create values with helpers: `Distance.Yard(100)`, `Velocity.FPS(2600)`.

See the full API reference:

??? api "API Reference: py_ballisticcalc.unit"

    [`py_ballisticcalc.unit`][py_ballisticcalc.unit]