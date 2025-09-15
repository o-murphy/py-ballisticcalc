"""3D Vector Mathematics.

The Vector class is implemented as an immutable NamedTuple, providing high-performance
vector operations with memory efficiency.

Key Features:
    - Immutable vector implementation for thread safety and performance
    - Comprehensive operator overloading for intuitive mathematical syntax
    - High-precision magnitude calculations using math.hypot()
    - Dot product operations for angle and projection calculations
    - Normalization with numerical stability for near-zero vectors
    - Compatible with both Python and Cython implementations

Typical Usage:
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
"""
from __future__ import annotations

import math
from typing import Union, NamedTuple

__all__ = ('Vector',)


class Vector(NamedTuple):
    """Immutable 3D vector for ballistic trajectory calculations.
    
    Attributes:
        x: Distance/horizontal component (positive = downrange direction).
        y: Vertical component (positive = upward direction).
        z: Horizontal component (positive = right lateral direction).
        
    Examples:
        Basic vector creation and operations:
        
        ```python
        # Create position vector (100m downrange, 10m high)
        position = Vector(100.0, 10.0, 0.0)
        
        # Create velocity vector (800 m/s muzzle velocity)
        velocity = Vector(800.0, 0.0, 0.0)
        
        # Vector arithmetic
        new_pos = position + velocity * 0.1  # Position after 0.1 seconds
        
        # Calculate magnitude
        speed = velocity.magnitude()  # 800.0 m/s
        
        # Create unit vector for direction
        direction = velocity.normalize()  # Vector(1.0, 0.0, 0.0)
        
        # Wind vector (5 m/s crosswind from left)
        wind = Vector(0.0, 0.0, 5.0)
        
        # Calculate wind effect angle
        cos_angle = velocity.mul_by_vector(wind) / (velocity.magnitude() * wind.magnitude())
        
        # Gravity vector
        gravity = Vector(0.0, -9.81, 0.0)  # m/s²
        ```
    """

    x: float
    y: float
    z: float

    def magnitude(self) -> float:
        """Calculate the Euclidean norm (length) of the vector.
        
        Returns:
            The magnitude (length) of the vector as a non-negative float.
            
        Examples:
            ```python
            # Unit vector magnitude
            unit = Vector(1.0, 0.0, 0.0)
            assert unit.magnitude() == 1.0
            
            # Velocity magnitude (speed)
            velocity = Vector(800.0, 100.0, 50.0)
            speed = velocity.magnitude()  # ~806.5
            
            # Distance calculation
            position = Vector(100.0, 50.0, 25.0)
            distance = position.magnitude()  # Distance from origin
            ```
            
        Note:
            Uses math.hypot() for numerical stability with extreme values.
            Equivalent to sqrt(x² + y² + z²) but more robust.
        """
        # return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        return math.hypot(self.x, self.y, self.z)

    def mul_by_const(self, a: float) -> Vector:
        """Multiply vector by a scalar constant.
        
        Args:
            a: Scalar multiplier. Can be positive (same direction), negative
                (opposite direction), or zero (zero vector).
                
        Returns:
            New Vector instance with each component multiplied by the scalar.
            
        Examples:
            ```python
            # Scale velocity vector
            velocity = Vector(800.0, 0.0, 0.0)
            half_velocity = velocity.mul_by_const(0.5)  # Vector(400.0, 0.0, 0.0)
            
            # Reverse direction
            reversed_vel = velocity.mul_by_const(-1.0)  # Vector(-800.0, 0.0, 0.0)
            
            # Time-based scaling for position updates
            delta_pos = velocity.mul_by_const(0.001)  # Position change in 1ms
            ```
            
        Note:
            This operation preserves vector direction for non-zero scalars.
            Multiplying by zero produces a zero vector.
        """
        return Vector(self.x * a, self.y * a, self.z * a)

    def mul_by_vector(self, b: Vector) -> float:
        """Calculate the dot product (scalar product) of two vectors.
        
        Computes the dot product, which represents the projection of one vector
        onto another. The result is a scalar value used in angle calculations,
        projections, and determining vector relationships.
        
        Args:
            b: The other Vector instance to compute dot product with.
            
        Returns:
            Scalar result of the dot product (x₁·x₂ + y₁·y₂ + z₁·z₂).
                Positive values indicate vectors pointing in similar directions,
                negative values indicate opposite directions, zero indicates perpendicular vectors.
            
        Examples:
            ```python
            # Parallel vectors (same direction)
            v1 = Vector(1.0, 0.0, 0.0)
            v2 = Vector(2.0, 0.0, 0.0)
            dot = v1.mul_by_vector(v2)  # 2.0 (positive)
            
            # Perpendicular vectors
            v1 = Vector(1.0, 0.0, 0.0)
            v2 = Vector(0.0, 1.0, 0.0)
            dot = v1.mul_by_vector(v2)  # 0.0 (perpendicular)
            
            # Angle calculation
            velocity = Vector(800.0, 100.0, 0.0)
            wind = Vector(0.0, 0.0, 10.0)
            cos_angle = velocity.mul_by_vector(wind) / (velocity.magnitude() * wind.magnitude())
            
            # Work calculation (force · displacement)
            force = Vector(100.0, 0.0, 0.0)  # Newtons
            displacement = Vector(10.0, 5.0, 0.0)  # meters
            work = force.mul_by_vector(displacement)  # 1000.0 Joules
            ```
            
        Note:
            - The dot product is commutative: a·b = b·a
            - For unit vectors, the dot product equals the cosine of the angle between them.
        """
        return self.x * b.x + self.y * b.y + self.z * b.z

    def add(self, b: Vector) -> Vector:
        """Add two vectors component-wise.
        
        Args:
            b: The other Vector instance to add to this vector.
            
        Returns:
            New Vector instance representing the sum of both vectors.
            
        Examples:
            ```python
            # Position update
            position = Vector(100.0, 10.0, 0.0)
            displacement = Vector(5.0, 1.0, 0.5)
            new_position = position.add(displacement)  # Vector(105.0, 11.0, 0.5)
            
            # Velocity combination
            muzzle_velocity = Vector(800.0, 0.0, 0.0)
            wind_velocity = Vector(0.0, 0.0, 5.0)
            total_velocity = muzzle_velocity.add(wind_velocity)  # Vector(800.0, 0.0, 5.0)
            
            # Trajectory step integration
            old_pos = Vector(50.0, 20.0, 0.0)
            velocity_delta = Vector(8.0, 0.1, 0.0)  # velocity * time_step
            new_pos = old_pos.add(velocity_delta)
            ```
            
        Note:
            - Vector addition is commutative: a + b = b + a
            - Vector addition is associative: (a + b) + c = a + (b + c)
        """
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    def subtract(self, b: Vector) -> Vector:
        """Subtract one vector from another component-wise.
        
        Args:
            b: The Vector instance to subtract from this vector.
            
        Returns:
            New Vector instance representing the difference (self - b).
            
        Examples:
            ```python
            # Relative position calculation
            target_pos = Vector(1000.0, 0.0, 50.0)
            bullet_pos = Vector(500.0, 10.0, 45.0)
            relative_pos = target_pos.subtract(bullet_pos)  # Vector(500.0, -10.0, 5.0)
            
            # Velocity change calculation
            initial_velocity = Vector(800.0, 0.0, 0.0)
            final_velocity = Vector(750.0, -5.0, 2.0)
            velocity_change = final_velocity.subtract(initial_velocity)  # Vector(-50.0, -5.0, 2.0)
            
            # Range vector calculation
            muzzle_pos = Vector(0.0, 1.5, 0.0)  # Scope height
            impact_pos = Vector(1000.0, -2.0, 10.0)
            range_vector = impact_pos.subtract(muzzle_pos)  # Vector(1000.0, -3.5, 10.0)
            ```
            
        Note:
            - Vector subtraction is NOT commutative: a - b ≠ b - a
            - The result represents the vector from b to self.
        """
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    def negate(self) -> Vector:
        """Create a vector with opposite direction (negative vector).
        
        Returns a new vector with all components negated, effectively creating
        a vector pointing in the opposite direction with the same magnitude.
        
        Returns:
            New Vector instance with all components negated (-x, -y, -z).
            
        Examples:
            ```python
            # Reverse velocity direction
            forward_velocity = Vector(800.0, 0.0, 0.0)
            backward_velocity = forward_velocity.negate()  # Vector(-800.0, 0.0, 0.0)
            
            # Opposite force direction
            drag_force = Vector(-25.0, -2.0, 0.0)
            thrust_force = drag_force.negate()  # Vector(25.0, 2.0, 0.0)
            
            # Reflection calculation
            incident_vector = Vector(100.0, -50.0, 25.0)
            reflected_vector = incident_vector.negate()  # Vector(-100.0, 50.0, -25.0)
            ```
            
        Note:
            - The magnitude remains unchanged: |v| = |-v|
            - Negating twice returns the original vector: -(-v) = v
        """
        return Vector(-self.x, -self.y, -self.z)

    def normalize(self) -> Vector:
        """Create a unit vector pointing in the same direction.
        
        Returns:
            New Vector instance with magnitude 1.0 and same direction.
                For near-zero vectors (magnitude < 1e-10), returns a copy of
                the original vector to avoid division by zero.
            
        Examples:
            ```python
            # Create direction vector
            velocity = Vector(800.0, 100.0, 50.0)
            direction = velocity.normalize()  # Unit vector in velocity direction
            
            # Wind direction calculation
            wind_vector = Vector(5.0, 0.0, 3.0)
            wind_direction = wind_vector.normalize()  # Unit vector for wind direction
            
            # Line of sight vector
            los_vector = Vector(1000.0, -10.0, 25.0)
            los_unit = los_vector.normalize()  # Unit vector toward target
            ```
            
        Note:
            For numerical stability, vectors with magnitude < 1e-10 are considered
            zero vectors and returned unchanged rather than normalized.
            The normalized vector preserves direction but has magnitude = 1.0.
        """
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def __mul__(self, other: Union[int, float, Vector]) -> Union[float, Vector]:  # type: ignore[override]
        """Multiplication operator supporting both scalar and vector multiplication.
        
        Provides overloaded multiplication supporting both scalar multiplication
        (vector scaling) and vector multiplication (dot product). The operation
        type is determined by the type of the other operand.
        
        Args:
            other: Either a scalar (int/float) for scaling operations, or another
                Vector instance for dot product calculation.
                
        Returns:
            For scalar multiplication: New Vector scaled by the scalar value.
            For vector multiplication: Float result of dot product operation.
            
        Raises:
            TypeError: If other is not int, float, or Vector instance.
            
        Examples:
            ```python
            # Scalar multiplication (scaling)
            velocity = Vector(800.0, 100.0, 0.0)
            half_speed = velocity * 0.5  # Vector(400.0, 50.0, 0.0)
            double_speed = velocity * 2  # Vector(1600.0, 200.0, 0.0)
            
            # Vector multiplication (dot product)
            v1 = Vector(1.0, 2.0, 3.0)
            v2 = Vector(4.0, 5.0, 6.0)
            dot_product = v1 * v2  # 32.0 (1*4 + 2*5 + 3*6)
            ```
            
        Note:
            Multiplication is commutative for scalars but not for vectors.
        """
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    # Operator overloads - aliases more efficient than wrappers
    def __add__(self, other: Vector) -> Vector:  # type: ignore[override]
        """Addition operator for vector addition.
        
        Provides intuitive syntax for vector addition using the + operator.
        Delegates to the add() method for the actual computation.
        
        Args:
            other: The Vector instance to add to this vector.
            
        Returns:
            New Vector instance representing the sum of both vectors.
            
        Examples:
            ```python
            position = Vector(100.0, 10.0, 0.0)
            velocity_delta = Vector(5.0, 1.0, 0.5)
            new_position = position + velocity_delta  # Vector(105.0, 11.0, 0.5)
            
            # Chained operations
            v1 = Vector(1.0, 2.0, 3.0)
            v2 = Vector(4.0, 5.0, 6.0)
            v3 = Vector(7.0, 8.0, 9.0)
            result = v1 + v2 + v3  # Vector(12.0, 15.0, 18.0)
            ```
        """
        return self.add(other)

    def __radd__(self, other: Vector) -> Vector:  # type: ignore[override]
        """Right addition operator for vector addition.
        
        Enables vector addition when this vector is on the right side of
        the + operator. Since vector addition is commutative, this delegates
        to the standard add() method.
        
        Args:
            other: The Vector instance to add to this vector.
            
        Returns:
            New Vector instance representing the sum of both vectors.
            
        Examples:
            ```python
            v1 = Vector(1.0, 2.0, 3.0)
            v2 = Vector(4.0, 5.0, 6.0)
            result = v1 + v2  # Same as v2.__radd__(v1)
            ```
        """
        return self.add(other)

    def __iadd__(self, other: Vector) -> Vector:  # type: ignore[override]
        """In-place addition operator for vector addition.
        
        Provides += operator support. Since Vector is immutable (NamedTuple),
        this returns a new Vector instance rather than modifying the existing one.
        
        Args:
            other: The Vector instance to add to this vector.
            
        Returns:
            New Vector instance representing the sum.
            
        Examples:
            ```python
            position = Vector(100.0, 10.0, 0.0)
            displacement = Vector(5.0, 1.0, 0.5)
            position += displacement  # Creates new Vector(105.0, 11.0, 0.5)
            ```
        """
        return self.add(other)

    def __sub__(self, other: Vector) -> Vector:  # type: ignore[override]
        """Subtraction operator for vector subtraction.
        
        Provides intuitive syntax for vector subtraction using the - operator.
        Delegates to the subtract() method for the actual computation.
        
        Args:
            other: The Vector instance to subtract from this vector.
            
        Returns:
            New Vector instance representing the difference (self - other).
            
        Examples:
            ```python
            target_pos = Vector(1000.0, 0.0, 50.0)
            bullet_pos = Vector(500.0, 10.0, 45.0)
            range_to_target = target_pos - bullet_pos  # Vector(500.0, -10.0, 5.0)
            
            # Velocity change calculation
            final_vel = Vector(750.0, -5.0, 2.0)
            initial_vel = Vector(800.0, 0.0, 0.0)
            velocity_change = final_vel - initial_vel  # Vector(-50.0, -5.0, 2.0)
            ```
        """
        return self.subtract(other)

    def __isub__(self, other: Vector) -> Vector:  # type: ignore[override]
        """In-place subtraction operator for vector subtraction.
        
        Provides -= operator support. Since Vector is immutable (NamedTuple),
        this returns a new Vector instance rather than modifying the existing one.
        
        Args:
            other: The Vector instance to subtract from this vector.
            
        Returns:
            New Vector instance representing the difference.
            
        Examples:
            ```python
            position = Vector(1000.0, 100.0, 50.0)
            correction = Vector(5.0, 2.0, 1.0)
            position -= correction  # Creates new Vector(995.0, 98.0, 49.0)
            ```
        """
        return self.subtract(other)

    def __rmul__(self, other: Union[int, float, Vector]) -> Union[float, Vector]:  # type: ignore[override]
        """Right multiplication operator for vector operations.

        Enables multiplication when this vector is on the right side of the * operator.
        Delegates to __mul__ since multiplication operations are commutative for the supported types.

        Args:
            other: Either a scalar (int/float) or Vector instance.
            
        Returns:
            For scalar: New Vector scaled by the scalar value.
            For vector: Float result of dot product operation.
            
        Examples:
            ```python
            vector = Vector(800.0, 100.0, 0.0)
            scaled = 0.5 * vector  # Vector(400.0, 50.0, 0.0) - calls __rmul__
            
            # Time-based calculations
            time_step = 0.001  # seconds
            displacement = time_step * velocity  # Uses right multiplication
            ```
        """
        return self.__mul__(other)

    def __imul__(self, other: Union[int, float, Vector]) -> Union[float, Vector]:  # type: ignore[override]
        """In-place multiplication operator for vector operations.
        
        Provides *= operator support. Since Vector is immutable (NamedTuple),
        this returns a new Vector (for scalar) or float (for vector) rather
        than modifying the existing vector.
        
        Args:
            other: Either a scalar (int/float) for scaling, or Vector for dot product.
            
        Returns:
            For scalar: New Vector scaled by the scalar value.
            For vector: Float result of dot product operation.
            
        Examples:
            ```python
            velocity = Vector(800.0, 100.0, 0.0)
            velocity *= 0.9  # Creates new Vector(720.0, 90.0, 0.0)
            
            # Dot product with *=
            v1 = Vector(1.0, 2.0, 3.0)
            v2 = Vector(4.0, 5.0, 6.0)
            result = v1
            result *= v2  # result becomes 32.0 (dot product)
            ```
        """
        return self.__mul__(other)

    def __neg__(self) -> Vector:  # type: ignore[override]
        """Unary negation operator for creating opposite vector.
        
        Provides intuitive syntax for vector negation using the unary - operator.
        Delegates to the negate() method for the actual computation.
        
        Returns:
            New Vector instance with all components negated (opposite direction).
            
        Examples:
            ```python
            velocity = Vector(800.0, -10.0, 5.0)
            opposite_velocity = -velocity  # Vector(-800.0, 10.0, -5.0)
            
            # Wind compensation
            wind_drift = Vector(0.0, 0.0, 5.0)
            compensation = -wind_drift  # Vector(0.0, 0.0, -5.0)
            ```
        """
        return self.negate()
