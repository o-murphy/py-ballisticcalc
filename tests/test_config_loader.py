import os
from unittest import TestCase
from py_ballisticcalc import (basicConfig, PreferredUnits, Unit, loadMixedUnits, loadMetricUnits, loadImperialUnits,
                              get_global_max_calc_step_size, reset_globals)

ASSETS_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ), 'assets')


class TestConfigLoader(TestCase):

    def test_preferred_units_load(self):
        with self.subTest("env"):
            basicConfig()
            self.assertEqual(PreferredUnits.distance, Unit.Yard)

        with self.subTest("manual"):
            basicConfig(max_calc_step_size=Unit.Meter(0.3), preferred_units={
                'distance': Unit.Meter
            })
            self.assertEqual(get_global_max_calc_step_size().units, Unit.Meter)
            self.assertEqual(PreferredUnits.distance, Unit.Meter)

        with self.subTest("imperial"):
            loadImperialUnits()
            self.assertEqual(PreferredUnits.distance, Unit.Foot)

        with self.subTest("metric"):
            loadMetricUnits()
            self.assertEqual(PreferredUnits.distance, Unit.Meter)

        with self.subTest("mixed"):
            loadMixedUnits()
            self.assertEqual(PreferredUnits.velocity, Unit.MPS)

        basicConfig()
        reset_globals()
        PreferredUnits.defaults()
