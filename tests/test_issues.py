import math
from typing import Any

import pytest

from py_ballisticcalc import (DragModel, TableG1, TableG7, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Atmo, Calculator, RangeError, HitResult, BaseEngineConfigDict,
                              loadImperialUnits, loadMetricUnits, PreferredUnits,
)

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


class TestIssue204:
    """Regression: zero_angle() and find_zero_angle() must not raise on high-elevation targets.

    Root cause: Ridder's method checked the angle-step tolerance before computing f_next,
    allowing a premature return when the bracket was narrow but height error was still large.
    """

    # (x_m, y_m) in metres — from issue #204 reproduction script.
    _PROBLEM_POINTS = [
        # Failed on both _zero_angle() (iterative) and Newton's method
        (1266.55316094695, 2804.89754166274),
        (1576.72944526049, 2767.49890777391),
        (1654.27351633887, 2786.19822471832),
        (2300.47410865875, 2430.91120277438),
        (3256.85098529216, 1608.14125721997),
        # Failed only on _zero_angle() (iterative)
        (1525.033398,      1458.546722),
        (25.84802369,      2075.624181),
        (1111.465019,      2617.904372),
        (491.1124502,      3047.988662),
    ]

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance):
        self.calc = Calculator(engine=loaded_engine_instance, config=BaseEngineConfigDict(cStepMultiplier=5.0))

    def _make_shot(self, x_m: float, y_m: float):
        dm = DragModel(0.22, TableG7, Weight.Gram(10),
                       Distance.Centimeter(7.62), Distance.Centimeter(3.0))
        shot = Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)), atmo=Atmo.icao())
        shot.slant_angle = Angular.Radian(math.atan2(y_m, x_m))
        target_dist = Distance.Meter(math.hypot(x_m, y_m))
        return shot, target_dist

    @pytest.mark.parametrize("x_m,y_m", _PROBLEM_POINTS)
    def test_zero_angle(self, x_m, y_m):
        """zero_angle() (iterative + Ridder's fallback) must succeed on all points."""
        shot, target_dist = self._make_shot(x_m, y_m)
        angle = self.calc.set_weapon_zero(shot, target_dist)
        assert angle is not None

    @pytest.mark.parametrize("x_m,y_m", _PROBLEM_POINTS)
    def test_find_zero_angle(self, x_m, y_m):
        """find_zero_angle() (Ridder's method) must converge on all problem points."""
        shot, target_dist = self._make_shot(x_m, y_m)
        angle = self.calc._engine_instance.find_zero_angle(shot, target_dist)
        assert angle is not None


class TestIssue305:
    """get_at() must return the closest existing point when the requested value is within
    floating-point precision of it, rather than raising ArithmeticError.

    Root cause: the forward-search loop condition `curr_val < key_value <= next_val` excludes
    any key_value past the last bracketing pair it can find, so target_idx stayed -1 and the
    epsilon check was never reached before the error was raised. This affects not just the
    trajectory's first/last points but also local extrema (e.g. the trajectory apex) for
    non-monotonic attributes like height, since a value epsilon beyond an extremum falls
    outside every bracket the same way a value epsilon beyond an endpoint does.
    """

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance):
        drag_model = DragModel(bc=0.759, drag_table=TableG1, weight=Weight.Gram(108),
                               diameter=Distance.Millimeter(23), length=Distance.Millimeter(108.2))
        self.ammo = Ammo(drag_model, Velocity.MPS(930))
        self.calc = Calculator(engine=loaded_engine_instance)
        self.hit_result = self.calc.fire(Shot(ammo=self.ammo), Distance.Meter(1000), Distance.Meter(100))
        assert len(self.hit_result.trajectory) >= 3

    def test_get_at_epsilon_past_last_point_returns_last_point(self):
        last_point = self.hit_result.trajectory[-1]
        just_past_last = math.nextafter(last_point.distance.raw_value, math.inf)
        result = self.hit_result.get_at("distance", just_past_last)
        assert result == last_point

    def test_get_at_epsilon_before_first_point_returns_first_point(self):
        first_point = self.hit_result.trajectory[0]
        just_before_first = math.nextafter(first_point.distance.raw_value, -math.inf)
        result = self.hit_result.get_at("distance", just_before_first)
        assert result == first_point

    def test_get_at_far_past_last_point_still_raises(self):
        last_point = self.hit_result.trajectory[-1]
        with pytest.raises(ArithmeticError, match="does not reach"):
            self.hit_result.get_at("distance", last_point.distance.raw_value + 1e6)

    def test_get_at_epsilon_past_local_extremum_returns_that_point(self):
        """Height is non-monotonic (rises then falls); the apex is an interior local extremum,
        not an endpoint, and must be found the same way as an endpoint epsilon-overshoot is."""
        shot = Shot(ammo=self.ammo, relative_angle=Angular.Degree(0.5))
        apex_hit_result = self.calc.fire(shot, Distance.Meter(1500), Distance.Meter(50), raise_range_error=False)
        apex = max(apex_hit_result.trajectory, key=lambda pt: pt.height.raw_value)
        assert apex not in (apex_hit_result.trajectory[0], apex_hit_result.trajectory[-1])
        just_past_apex = math.nextafter(apex.height.raw_value, math.inf)
        result = apex_hit_result.get_at("height", just_past_apex)
        assert result == apex
