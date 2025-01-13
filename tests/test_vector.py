import unittest

from py_ballisticcalc import Vector

class TestVector(unittest.TestCase):
    def test_magnitude_available(self):
        unit_vector = Vector(1, 0, 0)
        self.assertEqual(1, unit_vector.magnitude())  # add assertion here
