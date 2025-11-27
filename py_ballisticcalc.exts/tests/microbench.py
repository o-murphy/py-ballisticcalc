import time
from statistics import mean

from py_ballisticcalc_exts.traj_data import CythonizedBaseTrajSeq


def bench_append(n, reserve_first=False):
    seq = CythonizedBaseTrajSeq()
    if reserve_first:
        seq.reserve(n)
    t0 = time.perf_counter()
    for i in range(n):
        seq.append(float(i), float(i * 0.01), 0.0, 0.0, 0.0, 0.0, 0.0, 0.5)
    t1 = time.perf_counter()
    return t1 - t0


def run_many(n=200000, repeats=5):
    results_no_reserve = [bench_append(n, reserve_first=False) for _ in range(repeats)]
    results_with_reserve = [bench_append(n, reserve_first=True) for _ in range(repeats)]
    print(f"append {n} repeats={repeats}")
    print("no reserve:", [f"{t:.4f}s" for t in results_no_reserve], "mean=", f"{mean(results_no_reserve):.4f}s")
    print("with reserve:", [f"{t:.4f}s" for t in results_with_reserve], "mean=", f"{mean(results_with_reserve):.4f}s")


if __name__ == "__main__":
    run_many(200000, repeats=3)
