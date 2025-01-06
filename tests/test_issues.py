"""Unittests for the specific issues library"""

import unittest
from py_ballisticcalc import (DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Calculator, RangeError, HitResult, logger)


class TestIssue96_97(unittest.TestCase):

    def test_must_return_hit_result(self):
        drag_model = DragModel(bc=0.03,
                               drag_table=TableG1,
                               diameter=Distance.Millimeter(23),
                               weight=Weight.Gram(188.5),
                               length=Distance.Millimeter(108.2))
        ammo = Ammo(drag_model, Velocity.MPS(930))
        weapon = Weapon()
        zero = Shot(weapon=weapon, ammo=ammo, relative_angle=Angular.Degree(1.0))
        calc = Calculator(_config={"cMinimumVelocity": 0})

        def must_fire(interface: Calculator, zero_shot,
                      trajectory_range, extra_data,
                      **kwargs) -> (HitResult, RangeError | None):
            """wrapper function to resolve RangeError and get HitResult"""
            try:
                # try to get valid result
                return interface.fire(zero_shot, trajectory_range, **kwargs, extra_data=extra_data), None
            except RangeError as err:
                # directly init hit result with incomplete data before exception occurred
                return HitResult(zero_shot, err.incomplete_trajectory, extra=extra_data), err

        hit_result, err = must_fire(calc, zero, Distance.Meter(1600.2437248702522), extra_data=True)

        # should return error
        self.assertIsInstance(err, RangeError)
        self.assertIsInstance(hit_result, HitResult, "Expected HitResult but got %s" % type(hit_result))
