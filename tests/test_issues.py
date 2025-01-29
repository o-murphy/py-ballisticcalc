"""Unittests for the specific issues library"""
import copy
# mypy: ignore - mypy overhead is not worth it for test code
import unittest
from typing import Any

from typing_extensions import Union
from py_ballisticcalc import (DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Calculator, RangeError, HitResult, InterfaceConfigDict, loadImperialUnits,
                              loadMetricUnits, PreferredUnits)


class TestIssue96_97(unittest.TestCase):

    def setUp(self):
        drag_model = DragModel(bc=0.03,
                               drag_table=TableG1,
                               diameter=Distance.Millimeter(23),
                               weight=Weight.Gram(188.5),
                               length=Distance.Millimeter(108.2))
        ammo = Ammo(drag_model, Velocity.MPS(930))
        weapon = Weapon()
        self.zero = Shot(weapon=weapon, ammo=ammo, relative_angle=Angular.Degree(1.0))
        self.calc = Calculator(_config=InterfaceConfigDict(cMinimumVelocity=0))
        self.trange = Distance.Meter(1600.2437248702522)

    def test_must_return_hit_result(self):

        with self.assertRaisesRegex(RangeError, "Max range not reached"):
            self.calc.fire(self.zero, self.trange, extra_data=True)

        def must_fire(interface: Calculator, zero_shot,
                      trajectory_range, extra_data,
                      **kwargs) -> (HitResult, Union[RangeError, None]):
            """wrapper function to resolve RangeError and get HitResult"""
            try:
                # try to get valid result
                return interface.fire(zero_shot, trajectory_range, **kwargs, extra_data=extra_data), None
            except RangeError as err:
                # directly init hit result with incomplete data before exception occurred
                return HitResult(zero_shot, err.incomplete_trajectory, extra=extra_data), err


        hit_result, err = must_fire(self.calc, self.zero, self.trange, extra_data=True)

        # should return error
        self.assertIsInstance(err, RangeError)
        self.assertIsInstance(hit_result, HitResult, f"Expected HitResult but got {type(hit_result)}")
        
def get_object_attribute_values_as_dict(obj: Any)->dict[str, Any]:
    """"""
    return {attr: getattr(obj, attr) for attr in dir(obj) if not attr.startswith("__")}


class TestIssue144(unittest.TestCase):

    def setUp(self):
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
        weapon = Weapon()
        ammo = Ammo(drag_model, Velocity.MPS(930))
        self.shot = Shot(weapon=weapon, ammo=ammo, relative_angle=Angular.Degree(13.122126582196692))
        self.range = Distance.Meter(740.8068308628336)
        self.calc = Calculator()

    
    def tearDown(self):
        PreferredUnits.set(**self.previous_preferred_units)

    def testResultsWithImperialUnits(self):
        loadImperialUnits()
        hit_result = self.calc.fire(self.shot, self.range, extra_data=False)
        self.check_expected_last_point(hit_result)

    def testResultsWithImperialUnits_FloatInput(self):
        loadImperialUnits()
        hit_result = self.calc.fire(self.shot, self.range>>PreferredUnits.distance, extra_data=False)
        self.check_expected_last_point(hit_result)


    def testResultsWithMetricUnits(self):
        loadMetricUnits()
        hit_result = self.calc.fire(self.shot, self.range, extra_data=False)
        self.check_expected_last_point(hit_result)

    def testResultsWithMetricUnits_FloatInput(self):
        loadMetricUnits()
        hit_result = self.calc.fire(self.shot, self.range>>PreferredUnits.distance, extra_data=False)
        self.check_expected_last_point(hit_result)


    def testResultsWithMetricUnits_FloatTrajectoryStep(self):
        loadMetricUnits()
        hit_result = self.calc.fire(self.shot, self.range, trajectory_step=Distance.Inch(2916.5623262316285)>>PreferredUnits.distance,
                                    extra_data=False)
        self.check_expected_last_point(hit_result)


    def testResultsWithImperialUnitsAndYards(self):
        loadImperialUnits()
        PreferredUnits.distance = Distance.Yard
        hit_result = self.calc.fire(self.shot, self.range, extra_data=False)
        self.check_expected_last_point(hit_result)

    def testResultsWithImperialUnitAndYards_UnitTrajectoryStep(self):
        loadImperialUnits()
        PreferredUnits.distance = Distance.Yard
        hit_result = self.calc.fire(self.shot, self.range, trajectory_step=Distance.Inch(2916.5623262316285),
                                    extra_data=False)
        self.check_expected_last_point(hit_result)


    def testResultWithImperialUnits_FloatRange(self):
        loadImperialUnits()
        self.assertEqual(PreferredUnits.distance, Distance.Foot)
        hit_result = self.calc.fire(self.shot, self.range>>Distance.Foot, extra_data=False)
        self.check_expected_last_point(hit_result)

    def check_expected_last_point(self, hit_result):
        self.assertEqual(11, len(hit_result.trajectory))
        last_hit_point = hit_result[-1]
        self.assertEqual(0.9920863205706615, last_hit_point.time)
        self.assertEqual(740.8498567639497, (last_hit_point.distance >> Distance.Meter))
        self.assertEqual(168.4355597904274, (last_hit_point.height >> Distance.Meter))
