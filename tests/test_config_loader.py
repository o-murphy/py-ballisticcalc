from unittest import TestCase
from py_ballisticcalc import basicConfig, PreferredUnits, Unit


class TestConfigLoader(TestCase):

    def test_preferred_units_load(self):
        self.assertEqual(PreferredUnits.distance, Unit.Yard)

    def test_custom_config_path(self):
        basicConfig("../.pybc-template.toml")
        self.assertEqual(PreferredUnits.distance, Unit.Meter)


