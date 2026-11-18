"""Binding-layer cost: calls with almost no C work, engine methods called directly (same shot, same module state)."""
import sys, time, statistics as st, gc
sys.path.insert(0, "scripts")
from benchmark import _build_shot
from py_ballisticcalc import Calculator, Distance, TrajFlag
KINDS = {"cy(C++)": "py_ballisticcalc_exts:Cythonized{n}IntegrationEngine", "cy(C-ABI)": "bcy:Native{n}IntegrationEngine",
         "ctypes": "py_ballisticcalc_ctypes:Native{n}IntegrationEngine"}
def mk(spec):
    c = Calculator(engine=spec); return c, c._engine_factory(c.config)
def per_call(f, n):
    for _ in range(300): f()
    gc.collect(); gc.disable()
    t = time.perf_counter()
    for _ in range(n): f()
    r = (time.perf_counter() - t) / n * 1e6
    gc.enable(); return r
cases = {}
for n in ("DormandPrince",):
    engines = {k: mk(v.format(n=n)) for k, v in KINDS.items()}
    shot = _build_shot(True); shot_t = _build_shot(False)
    for k, (c, e) in engines.items():
        cases.setdefault((n, "raw_at(t=0.2s) small C work"), {})[k] = lambda e=e, s=shot_t: e.integrate_raw_at(s, "time", 0.2)
        cases.setdefault((n, "zero_angle(100 m)"), {})[k] = lambda e=e, s=shot: e.zero_angle(s, Distance.Meter(100))
        cases.setdefault((n, "fire(10 m)  full path"), {})[k] = lambda c=c, s=shot_t: c.fire(shot=s, trajectory_range=Distance.Meter(10), trajectory_step=Distance.Meter(10), flags=TrajFlag.ALL)
res = {}
for rnd in range(7):
    for key, fs in cases.items():
        for k, f in fs.items():
            res.setdefault((key, k), []).append(per_call(f, 4000))
print(f"{'engine':14}{'case':28}" + "".join(f"{k:>14}" for k in KINDS) + "   (min of 7 rounds, µs/call; ratio to cy(C++))")
for key in cases:
    v = {k: min(res[(key, k)]) for k in KINDS}
    print(f"{key[0]:14}{key[1]:28}" + "".join(f"{v[k]:9.1f}" + (f" ({v[k]/v['cy(C++)']:4.2f})" if k != "cy(C++)" else "       ") for k in KINDS))
