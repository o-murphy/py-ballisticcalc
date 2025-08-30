from typing import Any

import pytest

from py_ballisticcalc import (DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Calculator, RangeError, HitResult, BaseEngineConfigDict,
                              loadImperialUnits, loadMetricUnits, PreferredUnits)

pytestmark = pytest.mark.engine

def get_object_attribute_values_as_dict(obj: Any) -> dict[str, Any]:
    """Returns the attributes of an object as a dictionary."""
    return {attr: getattr(obj, attr) for attr in dir(obj) if not attr.startswith(("_", "defaults", "set"))}

class TestIssue96_97:
    """Scenario where velocity.x approaches zero."""

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance):
        drag_model = DragModel(bc=0.03,
                               drag_table=TableG1,
                               diameter=Distance.Millimeter(23),
                               weight=Weight.Gram(188.5),
                               length=Distance.Millimeter(108.2))
        ammo = Ammo(drag_model, Velocity.MPS(930))
        self.zero = Shot(ammo=ammo, relative_angle=Angular.Degree(1.0))
        self.calc = Calculator(engine=loaded_engine_instance, config=BaseEngineConfigDict(cMinimumVelocity=0))
        self.trange = Distance.Meter(1600.2437248702522)

    def test_must_return_hit_result(self):
        """Return results even when desired trajectory_range isn't reached."""
        with pytest.raises(RangeError, match="Max range not reached"):
            self.calc.fire(self.zero, self.trange)

        hit_result = self.calc.fire(self.zero, self.trange, raise_range_error=False)

        # should return error
        assert isinstance(hit_result.error, RangeError)
        assert isinstance(hit_result, HitResult), f"Expected HitResult but got {type(hit_result)}"


class TestIssue144:
    """Changing the preferred unit should not affect the results"""

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance):
        # storing preferred unit settings in order to avoid influencing other tests
        # due to preferred unit being singletons
        self.previous_preferred_units = get_object_attribute_values_as_dict(PreferredUnits)
        drag_model = DragModel(
            bc=0.759,
            drag_table=TableG1,
            weight=Weight.Gram(108),
            diameter=Distance.Millimeter(23),
            length=Distance.Millimeter(108.2),
        )
        ammo = Ammo(drag_model, Velocity.MPS(930))
        self.shot = Shot(ammo=ammo, relative_angle=Angular.Degree(13.122126582196692))
        self.range = Distance.Meter(740.8068308628336)
        self.step = Distance.Meter(740.8068308628336 / 10)
        self.calc = Calculator(engine=loaded_engine_instance)

    def teardown_method(self):
        PreferredUnits.set(**self.previous_preferred_units)

    def check_expected_last_point(self, hit_result):
        assert 11 == len(hit_result.trajectory)
        last_hit_point = hit_result[-1]
        assert pytest.approx(0.992020943919257, abs=1e-3) == last_hit_point.time
        assert pytest.approx(740.8068308628334, abs=1e-6) == (last_hit_point.distance >> Distance.Meter)
        assert pytest.approx(168.4260740559500, abs=1e-2) == (last_hit_point.height >> Distance.Meter)

    def testResultsWithImperialUnits(self):
        loadImperialUnits()
        hit_result = self.calc.fire(self.shot, self.range, self.step)
        self.check_expected_last_point(hit_result)

    def testResultsWithImperialUnits_FloatInput(self):
        loadImperialUnits()
        hit_result = self.calc.fire(
            self.shot,
            self.range >> PreferredUnits.distance,
            self.step >> PreferredUnits.distance,
            extra_data=False
        )
        self.check_expected_last_point(hit_result)

    def testResultsWithMetricUnits(self):
        loadMetricUnits()
        hit_result = self.calc.fire(self.shot, self.range, self.step)
        self.check_expected_last_point(hit_result)

    def testResultsWithMetricUnits_FloatInput(self):
        loadMetricUnits()
        hit_result = self.calc.fire(
            self.shot,
            self.range >> PreferredUnits.distance,
            self.step >> PreferredUnits.distance,
            extra_data=False
        )
        self.check_expected_last_point(hit_result)

    def testResultsWithMetricUnits_FloatTrajectoryStep(self):
        loadMetricUnits()
        hit_result = self.calc.fire(
            self.shot,
            self.range,
            trajectory_step=Distance.Inch(2916.5623262316285) >> PreferredUnits.distance,
            extra_data=False)
        self.check_expected_last_point(hit_result)

    def testResultsWithImperialUnitsAndYards(self):
        loadImperialUnits()
        PreferredUnits.distance = Distance.Yard
        hit_result = self.calc.fire(self.shot, self.range, self.step)
        self.check_expected_last_point(hit_result)

    def testResultsWithImperialUnitAndYards_UnitTrajectoryStep(self):
        loadImperialUnits()
        PreferredUnits.distance = Distance.Yard
        hit_result = self.calc.fire(self.shot, self.range, trajectory_step=Distance.Inch(2916.5623262316285))
        self.check_expected_last_point(hit_result)

    def testResultWithImperialUnits_FloatRange(self):
        loadImperialUnits()
        assert PreferredUnits.distance == Distance.Foot
        hit_result = self.calc.fire(self.shot,
            self.range >> Distance.Foot,
            self.step >> Distance.Foot
        )
        self.check_expected_last_point(hit_result)
