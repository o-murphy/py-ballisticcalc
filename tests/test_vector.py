import math

import pytest

from py_ballisticcalc import Vector


class TestVector:
    """Test for methods available on Vector in python, in order to ensure that they work as well in cython."""

    def test_magnitude_available(self):
        unit_vector = Vector(1, 0, 0)
        assert unit_vector.magnitude() == 1

    def test_mul_by_constant(self):
        vector = Vector(-1, -2, -3)
        multiplied = vector.mul_by_const(2)
        assert multiplied == Vector(-2, -4, -6)

    def test_mul_by_vector(self):
        vector = Vector(-1, -2, -3)
        dot_product = vector.mul_by_vector(Vector(4, 5, 6))
        assert dot_product == -32

    def test_add(self):
        vector = Vector(-1, -2, -3)
        result = vector.add(Vector(4, 6, 8))
        assert result == Vector(3, 4, 5)

    def test_subtract(self):
        vector = Vector(-1, -2, -3)
        result = vector.subtract(Vector(4, 5, 6))
        assert result == Vector(-5, -7, -9)

    def test_negate(self):
        vector = Vector(-1, -2, -3)
        negated = vector.negate()
        assert negated == Vector(1, 2, 3)

    def test_normalize(self):
        vector = Vector(-3, -3, -3)
        normalized = vector.normalize()
        expected = Vector(-1 / math.sqrt(3), -1 / math.sqrt(3), -1 / math.sqrt(3))
        assert pytest.approx(normalized.x) == expected.x
        assert pytest.approx(normalized.y) == expected.y
        assert pytest.approx(normalized.z) == expected.z
        zero_vector = Vector(0, 0, 0)
        zero_normalized = zero_vector.normalize()
        assert zero_vector == zero_normalized
