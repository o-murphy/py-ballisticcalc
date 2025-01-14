import math
from dataclasses import dataclass
from typing import Union

__all__ = ('Vector',)

@dataclass
class Vector:
    x: float
    y: float
    z: float

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def mul_by_const(self, a: float) -> 'Vector':
        return Vector(self.x * a, self.y * a, self.z * a)

    def mul_by_vector(self, b: 'Vector') -> float:
        return self.x * b.x + self.y * b.y + self.z * b.z

    def add(self, b: 'Vector') -> 'Vector':
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    def subtract(self, b: 'Vector') -> 'Vector':
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    def negate(self) -> 'Vector':
        return Vector(-self.x, -self.y, -self.z)

    def normalize(self) -> 'Vector':
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def __mul__(self, other: Union[int, float, 'Vector']) -> Union[float, 'Vector']:
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    # aliases more efficient than wrappers
    __add__ = add
    __radd__ = add
    __iadd__ = add
    __sub__ = subtract
    __rsub__ = subtract
    __isub__ = subtract
    __rmul__ = __mul__
    __imul__ = __mul__
    __neg__ = negate
