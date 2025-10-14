# distutils: language = c++

from time import perf_counter

cdef extern from "include/v3d.hpp":
    cdef cppclass V3d:
        double x
        double y
        double z

        V3d() except +
        V3d(double, double, double) except +

        V3d operator+(const V3d& other) const
        V3d operator-(const V3d& other) const
        V3d operator*(double scalar) const
        V3d operator/(double scalar) const
        V3d operator-() const

        double dot(const V3d& other) const
        double mag() const
        V3d norm() const

cdef class PyV3d:
    cdef V3d _v3d

    def __cinit__(self, double x=0.0, double y=0.0, double z=0.0):
        self._v3d = V3d(x, y, z)

    # def __dealloc__(self):
    #     if self._v3d is not NULL:
    #         del self.c_v3d

    property x:
        def __get__(self):
            return self._v3d.x

        def __set__(self, double x):
            self._v3d.x = x

    property y:
        def __get__(self):
            return self._v3d.y

        def __set__(self, double y):
            self._v3d.y = y

    property z:
        def __get__(self):
            return self._v3d.z

        def __set__(self, double z):
            self._v3d.z = z

    @staticmethod
    cdef PyV3d from_c(V3d v):
        cdef PyV3d pv = PyV3d.__new__(PyV3d)
        pv._v3d = v
        return pv

    def __add__(self, PyV3d other):
        return PyV3d.from_c(self._v3d + other._v3d)


# ----------------------------------------------------
# Benchmarking Function for V3d
# ----------------------------------------------------

# Benchmarks raw C++ V3d operations using perf_counter for high-resolution timing
def bench_v3d_operations(int num_iterations):
    cdef V3d a = V3d(1.0, 2.0, 3.0)
    cdef V3d b = V3d(4.0, 5.0, 6.0)
    cdef V3d c
    cdef double result_mag = 0.0

    # Use perf_counter() for timing
    cdef double start_time = perf_counter()

    for i in range(num_iterations):
        # Perform a sequence of typical V3d operations
        c = a + b                     # Addition
        c = c - a                     # Subtraction
        c = c * 2.5                   # Scalar multiplication
        c = c.norm()                  # Normalization
        result_mag += c.mag()         # Magnitude
        result_mag += a.dot(b)        # Dot product

    cdef double end_time = perf_counter()
    cdef double duration = end_time - start_time

    # Return duration and result_mag to prevent compiler optimization
    return duration, result_mag


# ----------------------------------------------------
# Main function for demonstration
# ----------------------------------------------------
def main():
    cdef V3d x = V3d(1, 2, 3)
    cdef V3d y = V3d(1, 2, 3)
    cdef V3d r = x + y

    print(f"C++ V3d addition: {r.x=}, {r.y=}, {r.z=}")

    cdef PyV3d v = PyV3d(0, 0, 0)
    cdef PyV3d a = PyV3d(1, 1, 1)

    print(f"PyV3d init: {v.x=}, {v.y=}, {v.z=}")
    print(f"PyV3d init: {a.x=}, {a.y=}, {a.z=}")
    cdef PyV3d b = v + a
    print(f"PyV3d addition: {b.x=}, {b.y=}, {b.z=}")
    
    # Run the benchmark
    ITERATIONS = 1000000
    duration, result = bench_v3d_operations(ITERATIONS)

    print("\n--- V3d Benchmarking ---")
    print(f"Iterations: {ITERATIONS:,}")
    print(f"Time taken (perf_counter): {duration:.6f} seconds")
    print(f"Operations per second (approx): {ITERATIONS / duration * 6:.2f} (6 ops per loop)")
    print(f"Dummy result (to prevent optimization): {result}")
