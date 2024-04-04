import os
from unittest import TestCase
from py_ballisticcalc import basicConfig, PreferredUnits, Unit


class TestConfigLoader(TestCase):

    def test_preferred_units_load(self):
        basicConfig()
        self.assertEqual(PreferredUnits.distance, Unit.Yard)

    def test_custom_config_path(self):

        assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')

        basicConfig(os.path.join(assets_dir, ".pybc-imperial.toml"))
        self.assertEqual(PreferredUnits.distance, Unit.Foot)

        basicConfig(os.path.join(assets_dir, ".pybc-metrics.toml"))
        self.assertEqual(PreferredUnits.distance, Unit.Meter)

        basicConfig(os.path.join(assets_dir, ".pybc-mixed.toml"))
        self.assertEqual(PreferredUnits.velocity, Unit.MPS)


