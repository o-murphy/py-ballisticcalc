# Vector

???+ api "API Documentation"

    [`py_ballisticcalc.vector.Vector`][py_ballisticcalc.vector.Vector]<br>

Immutable 3D vector used for positions and velocities in internal engine calculations. Provides magnitude, dot product, normalization, and arithmetic.

## Key Features
- Immutable vector implementation for thread safety and performance
- Comprehensive operator overloading for intuitive mathematical syntax
- High-precision magnitude calculations using math.hypot()
- Dot product operations for angle and projection calculations
- Normalization with numerical stability for near-zero vectors
- Compatible with both Python and Cython implementations

## Sample Usage
    ```python
    from py_ballisticcalc import Vector
    
    # Create position vector
    position = Vector(100.0, 50.0, 0.0)
    
    # Create velocity vector
    velocity = Vector(800.0, 0.0, 0.0)  # m/s
    
    # Vector arithmetic
    new_position = position + velocity * time_step
    
    # Calculate distance
    distance = position.magnitude()
    
    # Unit vector for direction
    direction = velocity.normalize()
    
    # Dot product for angle calculations
    cos_angle = velocity.mul_by_vector(wind_vector) / (velocity.magnitude() * wind_vector.magnitude())
    ```
