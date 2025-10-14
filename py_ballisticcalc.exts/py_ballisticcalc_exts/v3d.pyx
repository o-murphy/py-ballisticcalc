# distutils: language = c

from time import perf_counter

# ----------------------------------------------------
# Benchmarking Function for V3dT (C Style)
# ----------------------------------------------------

# Benchmarks raw C V3dT operations using const pointers for input and
# returning V3dT by value, mirroring the C function prototypes.
def bench_v3dt_operations(int num_iterations):
    # Initialize V3dT structs using the C 'vec' function
    cdef V3dT a = vec(1.0, 2.0, 3.0)
    cdef V3dT b = vec(4.0, 5.0, 6.0)
    cdef V3dT c
    cdef double result_mag = 0.0

    # Use perf_counter() for high-resolution, monotonic timing
    cdef double start_time = perf_counter()

    for i in range(num_iterations):
        # 1. Addition: c = add(&a, &b)
        c = add(&a, &b)
        
        # 2. Subtraction: c = sub(&c, &a)
        c = sub(&c, &a)
        
        # 3. Scalar multiplication: c = mulS(&c, 2.5)
        c = mulS(&c, 2.5)
        
        # 4. Normalization (Non-in-place): c = norm(&c)
        c = norm(&c)
        
        # 5. Magnitude: result_mag += mag(&c)
        result_mag += mag(&c)
        
        # 6. Dot product: result_mag += dot(&a, &b)
        result_mag += dot(&a, &b)

    cdef double end_time = perf_counter()
    cdef double duration = end_time - start_time

    # Return duration and result_mag to prevent compiler optimization
    return duration, result_mag

# ----------------------------------------------------
# Main function for demonstration
# ----------------------------------------------------
def main():
    cdef V3dT x = vec(1, 2, 3)
    cdef V3dT y = vec(1, 2, 3)
    cdef V3dT r = add(&x, &y)

    print("C V3dT addition test:")
    print(f"r.x={r.x}, r.y={r.y}, r.z={r.z}")
    
    # Run the benchmark
    ITERATIONS = 1000000
    duration, result = bench_v3dt_operations(ITERATIONS)

    print("\n--- V3dT (C) Benchmarking ---")
    print(f"Iterations: {ITERATIONS:,}")
    print(f"Time taken (perf_counter): {duration:.6f} seconds")
    print(f"Operations per second (approx): {ITERATIONS / duration * 6:.2f} (6 ops per loop)")
    print(f"Dummy result (to prevent optimization): {result}")
