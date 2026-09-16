"""Cash-Karp tolerance and reference-trajectory regressions.

Cash-Karp-specific (relative_tolerance, get_step_stats()) -- skipped
entirely unless --engine actually selects CythonizedCashKarpIntegrationEngine.
The skip check is done purely against `loaded_engine_instance`'s identity
(name/module), with no `py_ballisticcalc_exts` import attempted until *after*
that check passes -- so this file behaves correctly (skips, doesn't error)
even in an environment where `py_ballisticcalc_exts` isn't installed at all
and some other --engine (e.g. the pure-Python rk4_engine) is selected.
"""

import pytest

from py_ballisticcalc import Ammo, Atmo, DragModel, Shot, TableG7, TrajFlag, Weapon
from py_ballisticcalc.unit import Angular, Distance, Velocity


def _shot() -> Shot:
    return Shot(
        ammo=Ammo(DragModel(0.22, TableG7), mv=Velocity.MPS(800)),
        weapon=Weapon(zero_elevation=Angular.MOA(3)),
        atmo=Atmo.icao(),
    )


def _integrate(engine, shot: Shot):
    return engine.integrate(
        shot,
        Distance.Meter(2000),
        Distance.Meter(100),
        0.0,
        TrajFlag.ALL,
        dense_output=True,
    )


class TestCashKarp:
    @pytest.fixture(autouse=True)
    def _require_cashkarp_engine(self, loaded_engine_instance):
        if (
            loaded_engine_instance.__module__ != "py_ballisticcalc_exts.cashkarp_engine"
            or loaded_engine_instance.__name__ != "CythonizedCashKarpIntegrationEngine"
        ):
            pytest.skip(
                "Cash-Karp-specific test; run with "
                "--engine=py_ballisticcalc_exts.cashkarp_engine:CythonizedCashKarpIntegrationEngine"
            )
        # Only import once --engine has already proven this module loadable
        # (loaded_engine_instance succeeded), never as this file's own
        # collection-time skip condition.
        import py_ballisticcalc_exts as exts

        self.exts = exts

    def test_cashkarp_tolerance_controls_adaptive_step_count(self):
        """Tighter Cash-Karp rtol must require more accepted adaptive intervals."""
        loose = self.exts.CythonizedCashKarpIntegrationEngine({"relative_tolerance": 1e-5})
        tight = self.exts.CythonizedCashKarpIntegrationEngine({"relative_tolerance": 1e-8})

        loose_result = _integrate(loose, _shot())
        tight_result = _integrate(tight, _shot())
        loose_accepted, _ = loose.get_step_stats()
        tight_accepted, _ = tight.get_step_stats()

        assert loose.relative_tolerance == 1e-5
        assert tight.relative_tolerance == 1e-8
        assert tight_accepted > loose_accepted
        # Adaptive internal spacing must not alter scheduled table cardinality.
        assert len(tight_result.trajectory) == len(loose_result.trajectory) == 21

    def test_cashkarp_default_tolerance_matches_conservative_rk4_reference(self):
        """The default rtol remains close to a 5x finer fixed-step RK4 reference."""
        shot = _shot()
        reference_engine = self.exts.CythonizedRK4IntegrationEngine({"cStepMultiplier": 0.1})
        reference = _integrate(reference_engine, shot)

        cash_karp = self.exts.CythonizedCashKarpIntegrationEngine({})
        result = _integrate(cash_karp, shot)

        assert cash_karp.relative_tolerance == 1e-6
        assert len(result.trajectory) == len(reference.trajectory)
        assert max(
            abs(actual.height.raw_value - expected.height.raw_value)
            for actual, expected in zip(result.trajectory, reference.trajectory)
        ) < 0.06
        assert max(
            abs(actual.velocity.raw_value - expected.velocity.raw_value)
            for actual, expected in zip(result.trajectory, reference.trajectory)
        ) < 0.03

        reference_events = {event.flag: event for event in reference.events}
        assert {event.flag for event in result.events} == set(reference_events)
        assert all(
            abs(event.distance.raw_value - reference_events[event.flag].distance.raw_value) < 0.5
            for event in result.events
        )
