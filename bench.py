import time

from py_ballisticcalc import Angular, Calculator, Distance
from tests.test_zeros import create_ukrop_338lm_shots

en = "py_ballisticcalc:SciPyIntegrationEngine"

ds = list(range(100, 3001, 100))
zero, shot = create_ukrop_338lm_shots()
setup = Calculator(engine=en)
setup.set_weapon_zero(zero, Distance.Meter(100))


def _tc(engine):
    return engine.trajectory_count if hasattr(engine, "trajectory_count") else 0


def sweep(method, meters, use_previous):
    calc = Calculator(engine=en)
    engine = calc._engine_instance
    solve = getattr(engine, method)
    previous = None
    values = {}
    max_error = 0.0
    start_count = _tc(engine)
    start = time.perf_counter()
    for meter in meters:
        result = solve(shot, Distance.Meter(meter), initial_angle=previous if use_previous else None)
        angle, point = result if method == "zero_point" else (result, None)
        values[meter] = angle
        if point is not None:
            max_error = max(max_error, abs(point.slant_height >> Distance.Foot))
        if use_previous:
            previous = angle
    return values, time.perf_counter() - start, _tc(engine) - start_count, max_error


for method in ("zero_angle", "zero_point"):
    base, bt, bc, be = sweep(method, ds, False)
    forward, ft, fc, fe = sweep(method, ds, True)
    reverse, rt, rc, re = sweep(method, list(reversed(ds)), True)
    print(method)
    print(f"  no guess: {bt:.3f}s, {bc} integrations")
    print(
        f"  forward: {ft:.3f}s, {fc} integrations, max delta={max(abs((forward[d] >> Angular.Radian) - (base[d] >> Angular.Radian)) for d in ds):.3e} rad, max point error={fe:.3e} ft"
    )
    print(
        f"  reverse: {rt:.3f}s, {rc} integrations, max delta={max(abs((reverse[d] >> Angular.Radian) - (base[d] >> Angular.Radian)) for d in ds):.3e} rad, max point error={re:.3e} ft"
    )
