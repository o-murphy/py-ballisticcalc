"""Unittests for the specific issues library"""

import unittest

from typing_extensions import Union
from py_ballisticcalc import (DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Calculator, RangeError, HitResult)


class TestIssue96_97(unittest.TestCase):

    def setUp(self) -> None:
        drag_model = DragModel(bc=0.03,
                               drag_table=TableG1,
                               diameter=Distance.Millimeter(23),
                               weight=Weight.Gram(188.5),
                               length=Distance.Millimeter(108.2))
        ammo = Ammo(drag_model, Velocity.MPS(930))
        weapon = Weapon()
        self.zero = Shot(weapon=weapon, ammo=ammo, relative_angle=Angular.Degree(1.0))
        self.calc = Calculator(_config={"cMinimumVelocity": 0})
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

