import math
from dataclasses import dataclass
from typing import Union
from typing_extensions import Self

__all__ = ('Vector',)



Number = Union[int, float]


@dataclass(unsafe_hash=True)
class Vector:
    """
    Attributes:
        x (int, float): Distance component.
        y (int, float): Vertical component.
        z (int, float): Horizontal component.
    """

    x: Number
    y: Number
    z: Number

    # aliases more efficient than wrappers
    def __add__(self, other: 'Vector') -> 'Vector':  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Vector instance - sum of two Vector instances
        """
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __radd__(self, other: 'Vector') -> 'Vector':  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Vector instance - sum of two Vector instances
        """
        return other.add(self)

    def __iadd__(self, other: 'Vector') -> Self:  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Self - sum of two Vector instances
        """
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    def __sub__(self, other: 'Vector') -> 'Vector':  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Vector instance - result of subtract of two Vector instances
        """
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __rsub__(self, other: 'Vector') -> 'Vector':  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Self - result of subtract of two Vector instances
        """
        return other.__sub__(self)

    def __isub__(self, other: 'Vector') -> Self:  # type: ignore[override]
        """
        Args:
            other: Vector instance
        Returns:
            Vector instance - result of subtract of two Vector instances
        """
        self.x -= other.x
        self.y -= other.y
        self.z -= other.z
        return self

    def __mul__(self, other: Union[Number, 'Vector']) -> Union[Number, 'Vector']:  # type: ignore[override]
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    def __rmul__(self, other: Union[Number, 'Vector']) -> Union[Number, 'Vector']:  # type: ignore[override]
        return self.__mul__(other)

    def __imul__(self, other: Union[Number, 'Vector']) -> Union[Number, 'Vector']:  # type: ignore[override]
        if isinstance(other, (int, float)):
            return self.imul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        return self.__mul__(other)

    def __neg__(self) -> 'Vector':  # type: ignore[override]
        """
        Returns:
            Vector instance negative to current
        """
        return Vector(-self.x, -self.y, -self.z)

    def __iter__(self):
        """
        Makes the Vector object iterable.
        Returns an iterator that yields x, y, and z.
        """
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, index: Union[int, slice]):
        """
        Enables item access (v[0]) and slicing (v[0:3]).
        """
        if isinstance(index, int):
            if index == 0:
                return self.x
            elif index == 1:
                return self.y
            elif index == 2:
                return self.z
            else:
                raise IndexError("Vector index out of range (0-2)")
        elif isinstance(index, slice):
            components = [self.x, self.y, self.z]
            return components[index]
        else:
            raise TypeError("Vector indices must be integers or slices")

    def magnitude(self) -> Number:
        """
        Returns:
            magnitude of Vector instance
        """
        # return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        return math.hypot(self.x, self.y, self.z)

    def mul_by_const(self, a: Number) -> 'Vector':
        """
        Args:
            a: float constant
        Returns:
            Vector instance
        """
        return Vector(self.x * a, self.y * a, self.z * a)

    def imul_by_const(self, a: Number) -> Self:
        """
        Args:
            a: float constant
        Returns:
            Vector instance
        """
        self.x *= a
        self.y *= a
        self.z *= a
        return self

    def mul_by_vector(self, other: 'Vector') -> Number:
        """
        Args:
            other: Vector instance
        Returns:
            float multiplication result of two Vector instances
        """
        return self.x * other.x + self.y * other.y + self.z * other.z

    def normalize(self) -> 'Vector':
        """
        Returns:
            Normalized Vector instance
        """
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def inormalize(self) -> 'Vector':
        """
        Returns:
            Normalized Vector instance
        """
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return self
        return self.imul_by_const(1.0 / m)

    def add(self, other: 'Vector') -> 'Vector':
        """
        Fallback to __add__ for backward compatibility
        Args:
            other: Vector instance
        Returns:
            Vector instance - result of adding of two Vector instances
        """
        return self.__add__(other)

    def subtract(self, other: 'Vector') -> 'Vector':
        """
        Fallback to __sub__ for backward compatibility
        Args:
            other: Vector instance
        Returns:
            Vector instance - subtraction result of two Vector instances
        """
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def negate(self) -> 'Vector':
        """
        Fallback to __neg__ for backward compatibility
        Returns:
            Vector instance negative to current
        """
        return self.__neg__()

