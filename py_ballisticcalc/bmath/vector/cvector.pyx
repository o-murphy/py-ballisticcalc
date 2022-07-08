from libc.math cimport sqrt, abs

cpdef float magnitude(float x, float y, float z):
    cdef float ret
    ret = sqrt(x * x + y * y + z * z)
    return ret

cpdef float multiply_by_vector(float x, float y, float z, float x1, float y1, float z1):
    return x * x1 + y * y1 + z * z1

cpdef (float, float, float) multiply_by_const(float x, float y, float z, float a):
    return x * a, y * a, z * a

cpdef (float, float, float) add(float x, float y, float z, float x1, float y1, float z1):
    return x + x1, y + y1, z + z1

cpdef (float, float, float) subtract(float x, float y, float z, float x1, float y1, float z1):
    return x - x1, y - y1, z - z1

cpdef (float, float, float) negate(float x, float y, float z):
    return -x, -y, -z

cpdef (float, float, float) normalize (float x, float y, float z):
    cdef float m
    m = magnitude(x, y, z)
    if abs(m) < 1e-10:
        return x, y, z
    return multiply_by_const(x, y, z, 1.0 / m)


# cython
# test_time_1 0.5331406999999999
# test_time_2 1.0104932999999998
# test_time_3 0.4101440999999997

# pure python
# test_time_1 0.6663539999999999
# test_time_2 1.3299572
# test_time_3 0.48653330000000006
