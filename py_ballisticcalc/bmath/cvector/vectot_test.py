import timeit
import unittest
import pyximport

# try:
#     import vector
# except ImportError:
pyximport.install()
from py_ballisticcalc.bmath.cvector import vector


class TestVector(unittest.TestCase):

    def test_create(self):
        v = vector.Vector(1, 2, 3)
        mag = v.magnitude()
        mc = v.multiply_by_const(10)

        b = vector.Vector(1, 2, 3)
        mv = v.multiply_by_vector(b)
        a = v.add(b)
        s = v.subtract(b)
        neg = v.negate()
        norm = v.normalize()
        # print('\n'.join([str(i) for i in [mag, mc, mv, a, s, neg, norm]]))
        x = v.x

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)
