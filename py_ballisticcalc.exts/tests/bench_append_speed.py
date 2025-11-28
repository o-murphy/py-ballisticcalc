import time

from py_ballisticcalc_exts.traj_data import CythonizedBaseTrajSeq


def bench(n=100000):
    seq = CythonizedBaseTrajSeq()
    t0 = time.time()
    for i in range(n):
        seq.append(float(i), float(i * 0.1), 0.0, 0.0, 0.0, 0.0, 0.0, 0.5)
    t1 = time.time()
    print(f"append {n}: {t1 - t0:.4f}s")


if __name__ == "__main__":
    bench(200000)
