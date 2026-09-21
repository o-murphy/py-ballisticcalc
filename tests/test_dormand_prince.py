"""Dormand--Prince public API and adaptive-regression tests.

Run explicitly with ``--engine=cython+dopri``.  Keeping these
separate from Cash--Karp tests prevents controller-specific expectations from
silently skipping the new engine.
"""
import math

import pytest

from py_ballisticcalc import Ammo, Atmo, DragModel, Shot, TableG7, TrajFlag, Weapon, Wind
from py_ballisticcalc.unit import Angular, Distance, Velocity


def _shot():
    return Shot(
        ammo=Ammo(DragModel(.22, TableG7), mv=Velocity.MPS(800)),
        weapon=Weapon(zero_elevation=Angular.MOA(3)), atmo=Atmo.icao(),
    )


def _integrate(engine):
    return engine.integrate(_shot(), Distance.Meter(2000), Distance.Meter(100),
                            0., TrajFlag.ALL, dense_output=True)


class TestDormandPrince:
    @pytest.fixture(autouse=True)
    def _require_dopri(self, loaded_engine_instance):
        if (loaded_engine_instance.__module__ != "py_ballisticcalc_exts.dopri_engine"
                or loaded_engine_instance.__name__ != "CythonizedDormandPrinceIntegrationEngine"):
            pytest.skip("DOPRI-specific test; run with --engine=cython+dopri")
        import py_ballisticcalc_exts as exts
        self.exts = exts

    def test_public_api_defaults_and_round_trip(self):
        engine = self.exts.CythonizedDormandPrinceIntegrationEngine({
            "relative_tolerance": 1e-7, "absolute_tolerance": 1e-5,
        })
        assert engine.relative_tolerance == 1e-7
        assert engine.absolute_tolerance == 1e-5
        assert engine.get_step_stats() == (0, 0)
        assert self.exts.CythonizedDormandPrinceIntegrationEngine({}).relative_tolerance == 1e-6

    @pytest.mark.parametrize("key,value", [
        ("relative_tolerance", 0.), ("relative_tolerance", math.nan),
        ("absolute_tolerance", -1.), ("absolute_tolerance", math.inf),
    ])
    def test_invalid_tolerances(self, key, value):
        with pytest.raises(ValueError):
            self.exts.CythonizedDormandPrinceIntegrationEngine({key: value})

    def test_tighter_tolerances_increase_work(self):
        loose = self.exts.CythonizedDormandPrinceIntegrationEngine({"relative_tolerance": 1e-5})
        tight = self.exts.CythonizedDormandPrinceIntegrationEngine({"relative_tolerance": 1e-8})
        _integrate(loose); _integrate(tight)
        assert tight.get_step_stats()[0] > loose.get_step_stats()[0]

        atol_loose = self.exts.CythonizedDormandPrinceIntegrationEngine(
            {"relative_tolerance": 1e-12, "absolute_tolerance": 1e-2})
        atol_tight = self.exts.CythonizedDormandPrinceIntegrationEngine(
            {"relative_tolerance": 1e-12, "absolute_tolerance": 1e-6})
        _integrate(atol_loose); _integrate(atol_tight)
        assert atol_tight.get_step_stats()[0] > atol_loose.get_step_stats()[0]

    def test_trajectory_is_within_conservative_rk4_bound(self):
        reference = _integrate(self.exts.CythonizedRK4IntegrationEngine({"cStepMultiplier": .1}))
        actual = _integrate(self.exts.CythonizedDormandPrinceIntegrationEngine({}))
        assert len(actual.samples) == len(reference.samples)
        assert max(abs(a.height.raw_value - b.height.raw_value)
                   for a, b in zip(actual.samples, reference.samples)) < .5
        assert max(abs(a.velocity.raw_value - b.velocity.raw_value)
                   for a, b in zip(actual.samples, reference.samples)) < .1
        ref_events = {event.flag: event for event in reference.events}
        assert {event.flag for event in actual.events} == set(ref_events)
        assert all(abs(event.distance.raw_value - ref_events[event.flag].distance.raw_value) < 3.
                   for event in actual.events)

    def test_matches_scipy_rk45_when_available(self):
        """Adaptive boundaries differ, but the same tolerance model agrees on trajectory."""
        pytest.importorskip("scipy")
        from py_ballisticcalc.engines.scipy_engine import SciPyIntegrationEngine
        dopri = _integrate(self.exts.CythonizedDormandPrinceIntegrationEngine({}))
        scipy = _integrate(SciPyIntegrationEngine({
            "integration_method": "RK45", "relative_tolerance": 1e-6,
            "absolute_tolerance": 1e-6,
        }))
        assert max(abs(a.height.raw_value - b.height.raw_value)
                   for a, b in zip(dopri.samples, scipy.samples)) < .5
        assert max(abs(a.velocity.raw_value - b.velocity.raw_value)
                   for a, b in zip(dopri.samples, scipy.samples)) < .1

    def test_wind_transition_has_no_stale_fsal_derivative(self):
        shot = _shot()
        shot.winds = [
            Wind(Velocity.MPS(0), Angular.Degree(90), Distance.Meter(40)),
            Wind(Velocity.MPS(12), Angular.Degree(270), Distance.Meter(2000)),
        ]
        dopri = self.exts.CythonizedDormandPrinceIntegrationEngine({})
        result = dopri.integrate(shot, Distance.Meter(1000), Distance.Meter(50),
                                 0., TrajFlag.ALL, dense_output=True)
        reference = self.exts.CythonizedRK4IntegrationEngine({"cStepMultiplier": .1}).integrate(
            shot, Distance.Meter(1000), Distance.Meter(50), 0., TrajFlag.ALL, dense_output=True)
        assert dopri.get_step_stats()[0] > 0
        assert max(abs(a.windage.raw_value - b.windage.raw_value)
                   for a, b in zip(result.samples, reference.samples)) < .5
