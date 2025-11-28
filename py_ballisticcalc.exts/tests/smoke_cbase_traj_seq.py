import time

from py_ballisticcalc_exts.traj_data import CythonizedBaseTrajSeq


def smoke_run():
    seq = CythonizedBaseTrajSeq()
    n = 100000
    t0 = time.time()
    for i in range(n):
        seq.append(float(i), float(i * 0.1), 0.0, 0.0, 0.0, 0.0, 0.0, 0.5)
    t1 = time.time()
    print(f"Appended {n} entries in {t1 - t0:.3f}s")

    # Do a few interpolations
    for idx in [10, n // 2, n - 10]:
        try:
            res = seq.interpolate_at(idx, "time", float(idx) + 0.5)
            print("interp", idx, res.time)
        except Exception as e:
            print("interp failed", idx, e)


if __name__ == "__main__":
    smoke_run()
