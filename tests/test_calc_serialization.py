from dataclasses import dataclass
from functools import partial
from typing import Optional

import pytest

try:
    from joblib import Parallel, delayed, parallel_config

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from py_ballisticcalc import (
    Calculator,
    BaseEngineConfigDict,
    Velocity,
    Shot,
    Ammo,
    DragModel,
    TableG1,
    Weight,
    Distance,
    Angular,
)


pytestmark = pytest.mark.skipif(not JOBLIB_AVAILABLE, reason="joblib is not installed")


def create_zero_velocity_calc(engine_type):
    config = BaseEngineConfigDict(cMinimumVelocity=Velocity.MPS(0) >> Velocity.FPS)
    return Calculator(config=config, engine=engine_type)


class BaseCalcWrapper:
    def __init__(self, engine):
        self.engine = engine

    def get_calc(self):
        return create_zero_velocity_calc(self.engine)

    def compute_trajectory(self, distance_meters, angle_in_degrees):
        shot = self.create_shot()
        shot.relative_angle = Angular.Degree(angle_in_degrees)
        return self.get_calc().fire(shot, Distance.Meter(distance_meters), raise_range_error=False)

    def create_shot(self):
        diameter = Distance.Millimeter(23)
        projectile_weight = Weight.Gram(188.5)
        projectile_length = Distance.Millimeter(108.2)
        drag_model = DragModel(0.759, TableG1, projectile_weight, diameter, projectile_length)
        muzzle_velocity = Velocity.MPS(930)

        shot = Shot(ammo=Ammo(dm=drag_model, mv=muzzle_velocity))
        return shot


@dataclass
class CachingWrapper(BaseCalcWrapper):
    engine: object
    _calc: Optional[Calculator] = None

    def __post_init__(self):
        self._calc = create_zero_velocity_calc(self.engine)

    def get_calc(self):
        return self._calc


def calc_shot(distance, angle, wrapper):
    print(f"{distance=} {angle=}")
    result = wrapper.compute_trajectory(distance, angle)
    print(f"{distance=} {angle=} {len(result)=}")
    return result[-1].distance >> Distance.Meter


@pytest.mark.usefixtures("loaded_engine_instance")
class TestParallelCalculations:
    def test_no_calc_serialization(self, loaded_engine_instance):
        shot_processor = partial(calc_shot, wrapper=BaseCalcWrapper(loaded_engine_instance), angle=30)
        with parallel_config(n_jobs=2):
            Parallel()(delayed(shot_processor)(distance**2) for distance in range(1, 10))

    def test_calc_serialization(self, loaded_engine_instance):
        caching_wrapper = CachingWrapper(engine=loaded_engine_instance)
        shot_processor_cached = partial(calc_shot, wrapper=caching_wrapper, angle=30)
        with parallel_config(n_jobs=2):
            Parallel()(delayed(shot_processor_cached)(distance**2) for distance in range(1, 10))
