"""A zero search (Newton path) leaves the engine configuration as the caller set it, whether it succeeds or fails.

The Newton solver widens ``cMaximumDrop`` and ``cMinimumAltitude`` while it fires shots at the target, and used to restore
them only when it ran to the end: a search that raised (an unreachable target, no convergence, an error out of an
integration) left the widened limits in the engine, and every later ``integrate`` on it ignored the caller's limits.
"""

import dataclasses

import pytest

from py_ballisticcalc import BaseEngineConfigDict, OutOfRangeError, ZeroFindingError
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

LIMITS = BaseEngineConfigDict(cMaximumDrop=-5.0, cMinimumAltitude=-5.0)


def _make_shot(mv_mps: float = 100.0) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.05)),
        ammo=Ammo(DragModel(0.31, TableG7), Velocity.MPS(mv_mps)),
    )


def _snapshot(engine) -> dict:
    config = engine._config
    names = (
        [f.name for f in dataclasses.fields(config)]
        if dataclasses.is_dataclass(config)
        else ["cMaximumDrop", "cMinimumAltitude"]
    )
    return {name: getattr(config, name) for name in names}


def _assert_limits_stop_shot(engine) -> None:
    """The caller's 5 ft drop limit ends a long shot early (a trajectory that is allowed to fall farther runs on)."""
    shot = _make_shot()
    result = engine.integrate(shot, Distance.Meter(1000), Distance.Meter(100))
    assert result.records[-1].distance >> Distance.Meter < 500.0


def test_unreachable_target_restores_config(loaded_engine_instance):
    """100 m/s cannot reach 2000 m: the zero search fails, the limits are still the caller's."""
    engine = loaded_engine_instance(LIMITS)
    before = _snapshot(engine)
    with pytest.raises((OutOfRangeError, ZeroFindingError)):
        engine.zero_angle(_make_shot(), Distance.Meter(2000))
    assert _snapshot(engine) == before
    _assert_limits_stop_shot(engine)


def test_newton_failure_restores_config(loaded_engine_instance):
    """Newton gives up on an unreachable target (raises ZeroFindingError inside its loop), config unchanged."""
    if not issubclass(loaded_engine_instance, BaseIntegrationEngine):
        pytest.skip("cythonized engines handle the zero-search limits natively (C++)")
    engine = loaded_engine_instance(LIMITS)
    before = _snapshot(engine)
    props = engine._init_trajectory(_make_shot())
    with pytest.raises(ZeroFindingError):
        engine._find_zero_newton(props, Distance.Meter(2000))
    assert _snapshot(engine) == before
    _assert_limits_stop_shot(engine)


def test_error_from_integration_restores_config(loaded_engine_instance, monkeypatch):
    """An exception out of the integrations inside the widened section does not leave the limits widened."""
    if not issubclass(loaded_engine_instance, BaseIntegrationEngine):
        pytest.skip("cythonized engines handle the zero-search limits natively (C++)")
    engine = loaded_engine_instance(LIMITS)
    before = _snapshot(engine)
    seen = {}

    def broken(*args, **kwargs):
        seen["widened"] = engine._config.cMaximumDrop
        raise RuntimeError("integration failed")

    monkeypatch.setattr(engine, "_integrate", broken)
    props = engine._init_trajectory(_make_shot(800.0))
    with pytest.raises(RuntimeError, match="integration failed"):
        engine._find_zero_newton(props, Distance.Meter(300))
    assert seen["widened"] != before["cMaximumDrop"]  # the limits were widened while it ran
    assert _snapshot(engine) == before


def test_successful_zero_leaves_config_unchanged(loaded_engine_instance):
    engine = loaded_engine_instance(LIMITS)
    before = _snapshot(engine)
    engine.zero_angle(_make_shot(800.0), Distance.Meter(100))
    assert _snapshot(engine) == before
    _assert_limits_stop_shot(engine)
