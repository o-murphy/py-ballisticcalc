import os

import pytest

from py_ballisticcalc import (basicConfig, PreferredUnits, Unit, loadMixedUnits, loadMetricUnits, loadImperialUnits)

ASSETS_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ), 'assets')


class TestConfigLoader:

    @pytest.mark.parametrize(
        "test_name, config_func, expected_distance, expected_velocity",
        [
            ("env", basicConfig, Unit.Yard, None),
            (
                    "manual", lambda: basicConfig(preferred_units={'distance': Unit.Meter}),
                    Unit.Meter, None),
            ("imperial", loadImperialUnits, Unit.Foot, None),
            ("metric", loadMetricUnits, Unit.Meter, None),
            ("mixed", loadMixedUnits, None, Unit.MPS),
        ],
    )
    def test_preferred_units_load(self, test_name, config_func, expected_distance, expected_velocity):
        with pytest.MonkeyPatch.context() as monkeypatch:
            # Ensure a clean state for each subtest if needed
            PreferredUnits.restore_defaults()

            config_func()

            if expected_distance:
                assert PreferredUnits.distance == expected_distance
            if expected_velocity:
                assert PreferredUnits.velocity == expected_velocity

        basicConfig()
        PreferredUnits.restore_defaults()

    def test_preferred_units_load_manual_checks(self):
        basicConfig(preferred_units={
            'distance': Unit.Meter
        })
        assert PreferredUnits.distance == Unit.Meter

        basicConfig()
        PreferredUnits.restore_defaults()
