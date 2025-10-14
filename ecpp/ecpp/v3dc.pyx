# distutils: language = c
# NOTE: Цей файл містить Cython-обгортку PyV3dT для C-структури V3dT (Pass-by-Value)
# та функцію бенчмарку.

from libc.math cimport sqrt, fabs
from time import perf_counter

# ----------------------------------------------------
# 1. Декларації C-функцій з v3d.h
# ----------------------------------------------------

cdef extern from "include/v3d.h" nogil:
    # Декларація C-структури
    ctypedef struct V3dT:
        double x
        double y
        double z

    # Декларації C-функцій (Pass-by-Value)
    V3dT vec(double x, double y, double z) noexcept nogil
    V3dT add(V3dT v1, V3dT v2) noexcept nogil
    V3dT sub(V3dT v1, V3dT v2) noexcept nogil
    V3dT mulS(V3dT v, double scalar) noexcept nogil
    double dot(V3dT v1, V3dT v2) noexcept nogil
    double mag(V3dT v) noexcept nogil
    V3dT norm(V3dT v) noexcept nogil
    void iNorm(V3dT *v) noexcept nogil
    void print_vec(const char* name, V3dT v) noexcept nogil

# ----------------------------------------------------
# 2. Cython-обгортка PyV3dT
# ----------------------------------------------------

cdef class PyV3dT:
    cdef V3dT _v3d # Внутрішня C-структура

    def __cinit__(self, double x=0.0, double y=0.0, double z=0.0):
        # Використовуємо C-функцію vec для ініціалізації
        self._v3d = vec(x, y, z)

    property x:
        def __get__(self): return self._v3d.x
        def __set__(self, double x): self._v3d.x = x

    property y:
        def __get__(self): return self._v3d.y
        def __set__(self, double y): self._v3d.y = y

    property z:
        def __get__(self): return self._v3d.z
        def __set__(self, double z): self._v3d.z = z

    @staticmethod
    cdef PyV3dT from_c(V3dT v):
        # Створення PyV3dT з існуючої C-структури V3dT
        cdef PyV3dT pv = PyV3dT.__new__(PyV3dT)
        pv._v3d = v
        return pv

    # Перевантаження оператора додавання
    def __add__(self, PyV3dT other):
        # Виклик C-функції add, передаючи внутрішні структури за значенням
        return PyV3dT.from_c(add(self._v3d, other._v3d))

    # Додайте інші оператори за потребою (__sub__, __mul__, etc.)
    # ...

# ----------------------------------------------------
# 3. Функція бенчмарку
# ----------------------------------------------------

# Бенчмарк сирих C V3dT операцій (Pass-by-Value)
def bench_v3dt_operations(int num_iterations):
    cdef V3dT a = vec(1.0, 2.0, 3.0)
    cdef V3dT b = vec(4.0, 5.0, 6.0)
    cdef V3dT c # Акумулятор
    cdef double result_mag = 0.0

    cdef double start_time = perf_counter()

    for i in range(num_iterations):
        # 1. Addition: c = add(a, b)
        c = add(a, b)
        
        # 2. Subtraction: c = sub(c, a)
        c = sub(c, a)
        
        # 3. Scalar multiplication: c = mulS(c, 2.5)
        c = mulS(c, 2.5)
        
        # 4. Normalization (Non-in-place): c = norm(c)
        c = norm(c)
        
        # 5. Magnitude: result_mag += mag(c)
        result_mag += mag(c)
        
        # 6. Dot product: result_mag += dot(a, b)
        result_mag += dot(a, b)

    cdef double end_time = perf_counter()
    cdef double duration = end_time - start_time

    # Повертаємо тривалість і результат для уникнення оптимізації
    return duration, result_mag

# ----------------------------------------------------
# 4. Основна функція для демонстрації
# ----------------------------------------------------

def main():
    cdef PyV3dT v1 = PyV3dT(1.0, 2.0, 3.0)
    cdef PyV3dT v2 = PyV3dT(4.0, 5.0, 6.0)
    
    print("--- PyV3dT Wrapper Test ---")
    print(f"v1: ({v1.x}, {v1.y}, {v1.z})")
    print(f"v2: ({v2.x}, {v2.y}, {v2.z})")
    
    cdef PyV3dT sum_v = v1 + v2
    print(f"v1 + v2: ({sum_v.x}, {sum_v.y}, {sum_v.z})")
    
    # Запуск бенчмарку C-коду
    ITERATIONS = 1000000
    duration, result = bench_v3dt_operations(ITERATIONS)

    print("\n--- V3dT (C) Benchmarking - Pass-by-Value ---")
    print(f"Iterations: {ITERATIONS:,}")
    print(f"Time taken (perf_counter): {duration:.6f} seconds")
    print(f"Operations per second (approx): {ITERATIONS / duration * 6:.2f} (6 ops per loop)")
    print(f"Dummy result (to prevent optimization): {result}")
