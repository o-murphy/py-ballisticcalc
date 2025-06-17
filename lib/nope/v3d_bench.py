# Assuming 'v3d.py' contains your original code (V3d class and all function definitions)
# Make sure v3d.py is in the same directory or on your Python path.
import timeit
from lib.nope.v3d import set, add, sub, mulS, dot, mag, norm, V3d, _v3d_lib # Import all necessary components
from py_ballisticcalc import Vector

if _v3d_lib:
    print("\n--- Running Benchmarks ---")

    # Setup for benchmarks
    # We now directly import the functions and V3d from the v3d module
    # within the setup_code.
    setup_code = """
from v3d import set, add, sub, mulS, dot, mag, norm, V3d
vA = set(1.0, 2.0, 3.0)
vB = set(4.0, 5.0, 6.0)
vF = set(1.0, 1.0, 0.0)
"""

    number_of_runs = 1000000  # Number of times to execute each operation

    benchmarks = {
        "set": "set(1.0, 2.0, 3.0)",
        "add": "add(vA, vB)",
        "sub": "sub(vA, vB)",
        "mulS": "mulS(vA, 2.5)",
        "dot": "dot(vA, vB)",
        "mag": "mag(vA)",
        "norm": "norm(vF)", # norm modifies vF in place
    }

    results = {}
    for func_name, stmt in benchmarks.items():
        print(f"Benchmarking {func_name}...")
        # For norm, we need to re-initialize vF for each run to ensure it's not already normalized
        if func_name == "norm":
            timer = timeit.Timer(stmt, setup=setup_code + "\nvF = set(1.0, 1.0, 0.0)")
        else:
            timer = timeit.Timer(stmt, setup=setup_code)
        
        try:
            time_taken = timer.timeit(number=number_of_runs)
            results[func_name] = time_taken
            print(f"  {func_name}: {time_taken:.6f} seconds for {number_of_runs} runs ({time_taken/number_of_runs*1e6:.3f} µs per operation)")
        except Exception as e:
            results[func_name] = f"Error: {e}"
            print(f"  Error benchmarking {func_name}: {e}")


    print("\n--- Benchmark Summary ---")
    for func_name, time_taken in results.items():
        if isinstance(time_taken, float):
            print(f"{func_name:<8}: {time_taken:.6f} seconds for {number_of_runs} runs ({time_taken/number_of_runs*1e6:.3f} µs per operation)")
        else:
            print(f"{func_name:<8}: {time_taken}")

else:
    print("\nCannot run benchmarks: C library was not loaded.")




print("\n--- Running Python Vector Benchmarks ---")

# Setup for benchmarks
# We ensure the Vector class is available in the timeit environment
setup_code = """
from __main__ import Vector
vA = Vector(1.0, 2.0, 3.0)
vB = Vector(4.0, 5.0, 6.0)
vF = Vector(1.0, 1.0, 0.0)
"""

number_of_runs = 1000000  # Increased runs for potentially faster Python operations

# Define benchmarks for each operation
# Using both method calls and operator overloads where appropriate
benchmarks = {
    "init": "Vector(1.0, 2.0, 3.0)",
    "magnitude": "vA.magnitude()",
    "mul_by_const (method)": "vA.mul_by_const(2.5)",
    "mul_by_const (operator *)": "vA * 2.5", # Tests __mul__ with scalar
    "mul_by_vector (method)": "vA.mul_by_vector(vB)",
    "mul_by_vector (operator *)": "vA * vB", # Tests __mul__ with Vector (dot product)
    "add (method)": "vA.add(vB)",
    "add (operator +)": "vA + vB", # Tests __add__
    "subtract (method)": "vA.subtract(vB)",
    "subtract (operator -)": "vA - vB", # Tests __sub__
    "negate": "vA.negate()",
    "negate (operator -)": "-vA", # Tests __neg__
    "normalize": "vF.normalize()", # normalize returns a new Vector, not in-place
}

results = {}
for func_name, stmt in benchmarks.items():
    print(f"Benchmarking {func_name}...")
    # For normalize, we need to re-initialize vF for each run
    # as it returns a new vector, but we want to ensure the original state
    # if it were to be accidentally modified or if we benchmarked it repeatedly
    # without re-creation. For this specific implementation, it's not strictly
    # necessary as normalize returns a *new* vector, but it's good practice
    # for clarity and consistency with the ctypes benchmark where `norm` was in-place.
    if func_name == "normalize":
        timer = timeit.Timer(stmt, setup=setup_code + "\nvF = Vector(1.0, 1.0, 0.0)")
    else:
        timer = timeit.Timer(stmt, setup=setup_code)
    
    try:
        time_taken = timer.timeit(number=number_of_runs)
        results[func_name] = time_taken
        print(f"  {func_name}: {time_taken:.6f} seconds for {number_of_runs} runs ({time_taken/number_of_runs*1e6:.3f} µs per operation)")
    except Exception as e:
        results[func_name] = f"Error: {e}"
        print(f"  Error benchmarking {func_name}: {e}")

print("\n--- Benchmark Summary ---")
for func_name, time_taken in results.items():
    if isinstance(time_taken, float):
        print(f"{func_name:<30}: {time_taken:.6f} seconds for {number_of_runs} runs ({time_taken/number_of_runs*1e6:.3f} µs per operation)")
    else:
        print(f"{func_name:<30}: {time_taken}")