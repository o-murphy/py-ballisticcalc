import math
import unittest
from py_ballisticcalc.bmath import Vector


class TestVectorCreation(unittest.TestCase):

    def test_create(self):
        v = Vector(1, 2, 3)

        self.assertTrue(v.x == 1 and v.y == 2 and v.z == 3, "Create failed")

        c = v.__copy__()
        self.assertTrue(c.x == 1 and c.y == 2 and c.z == 3, "Copy failed")


class TestUnary(unittest.TestCase):

    def test_unary(self):
        v1 = Vector(1, 2, 3)

        self.assertFalse(math.fabs(v1.magnitude() - 3.74165738677) > 1e-7, "Magnitude failed")

        v2 = v1.negate()
        self.assertTrue(v2.x == -1 and v2.y == -2 and v2.z == -3, "Negate failed")

        v2 = v1.normalize()
        self.assertFalse(v2.x > 1 or v2.y > 1 or v2.z > 1, "Normalize failed")

        v1 = Vector(0, 0, 0)
        v2 = v1.normalize()
        self.assertFalse(v2.x != 0 or v2.y != 0 or v2.z != 0, "Normalize failed")


class TestBinary(unittest.TestCase):

    def test_binary(self):
        v1 = Vector(1, 2, 3)

        v2 = v1.add(v1.__copy__())
        self.assertFalse(v2.x != 2 or v2.y != 4 or v2.z != 6, "Add failed")

        v2 = v1.subtract(v2)
        self.assertFalse(v2.x != -1 or v2.y != -2 or v2.z != -3, "Subtract failed")

        self.assertFalse(v1.multiply_by_vector(v1.__copy__()) != (1 + 4 + 9), "MultiplyByVector failed")

        v2 = v1.multiply_by_const(3)
        self.assertFalse(v2.x != 3 or v2.y != 6 or v2.z != 9, "MultiplyByConst failed")
