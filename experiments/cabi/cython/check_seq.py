"""CythonizedBaseTrajSeq / CythonizedBaseTrajData of py_ballisticcalc_exts (C++ API) against the ones of bcy (C ABI): the same
calls on the same points, equal results or the same exception type, on ordinary and edge cases.

    PYTHONPATH=build python check_seq.py          (py_ballisticcalc_exts must be installed)
"""
import math
import random
import warnings

import bcy
from py_ballisticcalc_exts import traj_data as cxx

KEYS = ["time", "mach", "position.x", "position.y", "position.z", "velocity.x", "velocity.y", "velocity.z", "bogus"]
SEQS = {}


def build(mod, rows):
    s = mod.CythonizedBaseTrajSeq()
    for r in rows:
        s.append(*r)
    return s


def rows_of(n, rnd, mono=True):
    t = x = 0.0
    out = []
    for i in range(n):
        t += rnd.uniform(0.01, 0.2)
        x += rnd.uniform(1, 30)
        out.append((t, x, rnd.uniform(-5, 5), rnd.uniform(-2, 2), rnd.uniform(100, 900), rnd.uniform(-9, 9), rnd.uniform(-3, 3),
                    rnd.uniform(0.3, 2.5) if not mono else 2.5 - 0.01 * i))
    return out


def val(p):
    return None if p is None else (p.time, tuple(p.position), tuple(p.velocity), p.mach)


def run(fn):
    try:
        return ("ok", val(fn()))
    except Exception as e:
        return ("err", type(e).__name__)


def main():
    rnd = random.Random(7)
    bad = total = 0

    def compare(label, f_cxx, f_abi):
        nonlocal bad, total
        total += 1
        a, b = run(f_cxx), run(f_abi)
        if a != b:
            bad += 1
            print("DIFF", label, "\n   C++ :", a, "\n   ABI :", b)

    cases = {"empty": [], "one": rows_of(1, rnd), "two": rows_of(2, rnd), "three": rows_of(3, rnd), "ten": rows_of(10, rnd),
             "many": rows_of(300, rnd), "dup-time": [(1.0, 0, 0, 0, 0, 0, 0, 0.5), (1.0, 5, 0, 0, 0, 0, 0, 0.6), (2.0, 9, 0, 0, 0, 0, 0, 0.7)]}
    for name, rows in cases.items():
        a, b = build(cxx, rows), build(bcy, rows)
        compare(f"{name} len", lambda: len(a) and None, lambda: len(b) and None)
        assert len(a) == len(b)
        n = len(rows)
        for idx in {-n - 1, -n, -2, -1, 0, 1, 2, n - 2, n - 1, n, n + 1} if n else {0, 1, -1}:
            compare(f"{name} [{idx}]", lambda: a[idx], lambda: b[idx])
            for key in KEYS:
                lo = min((r[1] for r in rows), default=0)
                for v in (0.5, 1.0, 7.3, lo + 1.0):
                    compare(f"{name} interpolate_at({idx},{key},{v})", lambda: a.interpolate_at(idx, key, v), lambda: b.interpolate_at(idx, key, v))
        for key in KEYS:
            cols = {"time": 0, "position.x": 1, "position.y": 2, "position.z": 3, "velocity.x": 4, "velocity.y": 5, "velocity.z": 6, "mach": 7}
            if rows and key in cols:
                c = [r[cols[key]] for r in rows]
                targets = [min(c), max(c), (min(c) + max(c)) / 2, min(c) - 1e-12, max(c) + 1e-12, min(c) - 1e6, max(c) + 1e6] + [rnd.uniform(min(c), max(c)) for _ in range(20)] + c[:3]
            else:
                targets = [0.0, 1.0, 5.0]
            for v in targets:
                for st in (None, 0.0, 0.5, 2.0, -1.0):
                    compare(f"{name} get_at({key},{v},{st})", lambda: a.get_at(key, v, st), lambda: b.get_at(key, v, st))
        for ang in (0.0, 0.1, -0.3, math.pi / 2):
            for v in (-50.0, -1.0, 0.0, 3.0, 25.0, 1e6):
                compare(f"{name} get_at_slant_height({ang},{v})", lambda: a.get_at_slant_height(ang, v), lambda: b.get_at_slant_height(ang, v))

    # CythonizedBaseTrajData: constructor-free API, interpolate, repr, iteration, equality
    def mk(m, row):
        return m.CythonizedBaseTrajData if False else None

    from py_ballisticcalc_exts import _test_helpers as th
    for _ in range(300):
        rr = rows_of(3, rnd)
        for key in KEYS:
            v = rnd.uniform(0, 80)
            compare(f"data.interpolate({key})", lambda: cxx.CythonizedBaseTrajData.interpolate(key, v, *[th.make_base_traj_data(*r) for r in rr]),
                    lambda: bcy.CythonizedBaseTrajData.interpolate(key, v, *[bcy.make_base_traj_data(*r) for r in rr]))
    d1, d2 = th.make_base_traj_data(*rr[0]), bcy.make_base_traj_data(*rr[0])
    assert repr(d1).replace("Cythonized", "") == repr(d2).replace("Cythonized", ""), (repr(d1), repr(d2))
    assert str(d1) == str(d2) and len(d1) == len(d2) == 4 and tuple(d1) == tuple(d2) and d2 == d1 and d2 == tuple(d1)
    assert [d1[i] for i in (-4, -1, 0, 3)] == [d2[i] for i in (-4, -1, 0, 3)] and d1[1:3] == d2[1:3]
    for bad_idx in (4, -5):
        for d in (d1, d2):
            try:
                d[bad_idx]
            except IndexError:
                pass
            else:
                raise AssertionError("no IndexError")
    print(f"{total} calls compared, {bad} differences")
    return 1 if bad else 0


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    raise SystemExit(main())
