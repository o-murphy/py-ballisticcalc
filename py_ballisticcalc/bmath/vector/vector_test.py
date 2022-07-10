import math
import unittest
from py_ballisticcalc.bmath import Vector
# from py_ballisticcalc.bmath.vector.vector_c_ed import VectorCed
# import cvector

import timeit


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

    def test_vectorced(self):
        v1 = VectorCed(0.1, 0.2, 0.3)
        v2 = VectorCed(0.1, 0.2, 0.3)

        def magnitude():
            return v1.magnitude()

        def multiply():
            return v1.multiply_by_vector(v2)

        def multiply_const():
            return v1.multiply_by_const(10)

        def add():
            return v1.add(v2)

        print('ced magnitude', timeit.timeit(magnitude, number=50000))
        print('ced multiply', timeit.timeit(multiply, number=50000))
        print('ced multiply const', timeit.timeit(multiply_const, number=50000))
        print('ced add', timeit.timeit(add, number=50000))
        print()
        # self.assertGreater(abs(0.37416577339172363 - magnitude()), 1e-8)

    def test_pure(self):

        v1 = Vector(0.1, 0.2, 0.3)
        v2 = Vector(0.1, 0.2, 0.3)

        def magnitude():
            return v1.magnitude()

        def multiply():
            return v1.multiply_by_vector(v2)

        def multiply_const():
            return v1.multiply_by_const(10)

        def add():
            return v1.add(v2)

        def subtract():
            return v1.subtract(v2)

        def negate():
            return v1.negate()

        def normalize():
            return v1.normalize()

        print('pure magnitude', magnitude(), timeit.timeit(magnitude, number=50000))
        print('pure multiply', multiply(), timeit.timeit(multiply, number=50000))
        print('pure multiply const', multiply_const(), timeit.timeit(multiply_const, number=50000))
        print('pure add', add(), timeit.timeit(add, number=50000))
        print('pure subtract', subtract(), timeit.timeit(subtract, number=50000))
        print('pure negate', negate(), timeit.timeit(negate, number=50000))
        print('pure normalize', normalize(), timeit.timeit(normalize, number=50000))

        print()
        # self.assertGreater(abs(0.37416577339172363 - magnitude()), 1e-8)

    def test_cython(self):

        v1 = (0.1, 0.2, 0.3)
        v2 = (0.1, 0.2, 0.3)

        def magnitude():
            return cvector.magnitude(*v1)

        def multiply():
            return cvector.multiply_by_vector(*v1, *v2)

        def multiply_const():
            return cvector.multiply_by_const(*v1, 10)

        def add():
            return cvector.add(*v1, *v2)

        def subtract():
            return cvector.subtract(*v1, *v2)

        def negate():
            return cvector.negate(*v1)

        def normalize():
            return cvector.normalize(*v1)

        print('cython magnitude', magnitude(), timeit.timeit(magnitude, number=50000))
        print('cython multiply', multiply(), timeit.timeit(multiply, number=50000))
        print('cython multiply const', multiply_const(), timeit.timeit(multiply_const, number=50000))
        print('cython add', add(), timeit.timeit(add, number=50000))
        print('cython subtract', subtract(), timeit.timeit(subtract, number=50000))
        print('cython negate', negate(), timeit.timeit(negate, number=50000))
        print('cython normalize', normalize(), timeit.timeit(normalize, number=50000))

        print()
        # self.assertGreater(abs(0.37416577339172363 - magnitude()), 1e-8)




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
