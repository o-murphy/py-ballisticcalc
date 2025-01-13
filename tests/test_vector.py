import math
import unittest

from py_ballisticcalc import Vector


class TestVector(unittest.TestCase):
    """Test for methods available on Vector in python, in order to ensure that they work as well in cython."""
    def test_magnitude_available(self):
        unit_vector = Vector(1, 0, 0)
        self.assertEqual(1, unit_vector.magnitude())  # add assertion here

    def test_mul_by_constant(self):
        vector = Vector(-1, -2, -3)
        multiplied= vector.mul_by_const(2)
        self.assertEqual(multiplied, Vector(-2, -4, -6))

    def test_mul_by_vector(self):
        vector = Vector(-1, -2, -3)
        dot_product= vector.mul_by_vector(Vector(4, 5, 6))
        self.assertEqual(dot_product, -32)

    def test_add(self):
        vector = Vector(-1, -2, -3)
        result= vector.add(Vector(4, 6, 8))
        self.assertEqual(result, Vector(3, 4, 5))

    def test_subtract(self):
        vector = Vector(-1, -2, -3)
        result = vector.subtract(Vector(4, 5, 6))
        self.assertEqual(result, Vector(-5, -7, -9))

    def test_negate(self):
        vector = Vector(-1, -2, -3)
        negated = vector.negate()
        self.assertEqual(negated, Vector(1, 2, 3))

    def test_normalize(self):
        vector = Vector(-3, -3, -3)
        normalized = vector.normalize()
        expected = Vector(-1/math.sqrt(3), -1/math.sqrt(3), -1/math.sqrt(3))
        self.assertAlmostEqual(normalized.x, expected.x)
        self.assertAlmostEqual(normalized.y, expected.y)
        self.assertAlmostEqual(normalized.z, expected.z)
        zero_vector = Vector(0, 0, 0)
        zero_normalized = zero_vector.normalize()
        self.assertEqual(zero_vector, zero_normalized)