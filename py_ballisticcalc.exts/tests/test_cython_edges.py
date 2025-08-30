import math
import random
import gc
import pytest

from py_ballisticcalc import (
    BaseEngineConfigDict,
    Calculator,
    Ammo,
    Shot,
    Distance,
    DragModel,
    Angular,
    TableG7,
    Velocity,
    Weight,
)
from py_ballisticcalc.exceptions import RangeError, OutOfRangeError


def _mk_shot(look_angle: Angular = Angular.Degree(0.0)) -> Shot:
    dm = DragModel(
        bc=0.243,
        drag_table=TableG7,
        weight=Weight.Grain(175),
        diameter=Distance.Millimeter(7.62),
        length=Distance.Millimeter(32.0),
    )
    shot = Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))
    shot.look_angle = look_angle
    return shot


def test_config_restored_after_find_max_range(loaded_engine_instance):
    # Set a very tight maximum drop so normal integrates terminate immediately if restoration works.
    cfg = BaseEngineConfigDict(cMaximumDrop=-1.0)
    calc = Calculator(config=cfg, engine=loaded_engine_instance)
    shot = _mk_shot()

    # Call find_max_range (temporarily zeroes cMaximumDrop and cMinimumVelocity internally)
    _ = calc.find_max_range(shot)

    # Now run an integrate that should hit the configured MaximumDropReached quickly
    res = calc.integrate(shot, Distance.Yard(1000), Distance.Yard(25))
    assert res.error is not None, "Expected integrate to terminate due to MaximumDrop"
    assert res.error.reason == RangeError.MaximumDropReached


def test_config_restored_after_find_zero_angle_failure(loaded_engine_instance):
    # Make min velocity unrealistically high so integrates will immediately terminate when restored
    cfg = BaseEngineConfigDict(cMinimumVelocity=10000.0)
    calc = Calculator(config=cfg, engine=loaded_engine_instance)
    shot = _mk_shot()

    # Force OutOfRangeError in zero solving to exercise the finally-restore path
    with pytest.raises(OutOfRangeError):
        _ = calc.find_zero_angle(shot, Distance.Mile(50))  # absurdly far

    # After failure, integrate should still honor the restored high min velocity
    res = calc.integrate(shot, Distance.Yard(1000), Distance.Yard(25))
    assert res.error is not None, "Expected integrate to terminate due to MinimumVelocity"
    assert res.error.reason == RangeError.MinimumVelocityReached


def test_near_vertical_apex_is_max_range(loaded_engine_instance):
    # Near-vertical look angle within APEX_IS_MAX_RANGE_RADIANS threshold
    look = Angular.Degree(89.99)
    calc = Calculator(engine=loaded_engine_instance)
    shot = _mk_shot(look)

    max_range, angle = calc.find_max_range(shot)
    assert abs((angle >> Angular.Radian) - (look >> Angular.Radian)) < 1e-6

    # Compute apex and compare slant distance to reported max range
    apex = calc.find_apex(shot)
    ca = math.cos(look >> Angular.Radian)
    sa = math.sin(look >> Angular.Radian)
    apex_sdist = (apex.distance >> Distance.Foot) * ca + (apex.height >> Distance.Foot) * sa
    assert abs((max_range >> Distance.Foot) - apex_sdist) < 1e-3


def test_dense_output_random_sampling_get_at(loaded_engine_instance):
    # Stress interpolation on dense output buffers
    calc = Calculator(engine=loaded_engine_instance)
    shot = _mk_shot()

    res = calc.integrate(shot, Distance.Yard(400), Distance.Yard(10), dense_output=True)
    traj = res.base_data  # CBaseTrajSeq when cythonized engine is used
    assert traj is not None and len(traj) >= 3

    # Random time samples across the trajectory duration
    t = 0
    t_end = traj[-1].time
    for _ in range(200):
        t = random.random() * t_end
    _ = traj.get_at('time', t)
    # Random range samples
    x_end = traj[-1].position.x
    for _ in range(200):
        x = random.random() * x_end
        _ = traj.get_at('position.x', x)
    # Clean up
    del res
    gc.collect()


def test_find_apex_restores_min_velocity(loaded_engine_instance):
    # High min velocity would normally terminate integrates; apex must temporarily drop it to 0 and then restore
    cfg = BaseEngineConfigDict(cMinimumVelocity=10000.0)
    calc = Calculator(config=cfg, engine=loaded_engine_instance)
    shot = _mk_shot(Angular.Degree(30))

    # Should succeed despite high min velocity due to temporary override inside find_apex
    _ = calc.find_apex(shot)

    # After returning, integrate should respect restored high min velocity and terminate early
    res = calc.integrate(shot, Distance.Yard(1000), Distance.Yard(25))
    assert res.error is not None
    assert res.error.reason == RangeError.MinimumVelocityReached


def test_alternating_invalid_wind_cycles(loaded_engine_instance):
    class _AD:
        def __init__(self, raw_value: float):
            self.raw_value = raw_value

    class BadWind:
        # Provide only until_distance.raw_value so Shot.winds sorting works
        def __init__(self):
            self.until_distance = _AD(0.0)  # Missing attributes for C conversion

    calc = Calculator(engine=loaded_engine_instance)
    shot = _mk_shot()

    for i in range(10):
        # Inject invalid wind and ensure integrate fails cleanly
        winds = list(shot.winds)
        winds.append(BadWind())  # type: ignore[arg-type]
        shot.winds = winds  # type: ignore[assignment]
        with pytest.raises((RuntimeError, AttributeError)):
            _ = calc.integrate(shot, Distance.Yard(50), Distance.Yard(25))

        # Now clear winds and ensure multiple valid integrates still succeed
        shot.winds = []
        _ = calc.integrate(shot, Distance.Yard(150 + 5 * i), Distance.Yard(25))
