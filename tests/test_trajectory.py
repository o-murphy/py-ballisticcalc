from math import fabs

import pytest

from py_ballisticcalc import *

pytestmark = pytest.mark.engine

class TestTrajectory:

    def test_zero1(self, loaded_engine_instance):
        dm = DragModel(0.365, TableG1, 69, 0.223, 0.9)
        ammo = Ammo(dm, 2600)
        weapon = Weapon(Distance(3.2, Distance.Inch))
        atmosphere = Atmo.icao()
        calc = Calculator(engine=loaded_engine_instance)
        zero_angle = calc.barrel_elevation_for_target(Shot(weapon=weapon, ammo=ammo, atmo=atmosphere),
                                                      Distance(100, Distance.Yard))
        assert pytest.approx(zero_angle >> Angular.Radian, abs=1e-4) == 0.0016514

    def test_zero2(self, loaded_engine_instance):
        dm = DragModel(0.223, TableG7, 69, 0.223, 0.9)
        ammo = Ammo(dm, 2750)
        weapon = Weapon(Distance(2, Distance.Inch))
        atmosphere = Atmo.icao()
        calc = Calculator(engine=loaded_engine_instance)
        zero_angle = calc.barrel_elevation_for_target(Shot(weapon=weapon, ammo=ammo, atmo=atmosphere),
                                                      Distance(100, Distance.Yard))
        assert pytest.approx(zero_angle >> Angular.Radian, abs=1e-4) == 0.0012286

    def custom_assert_equal(self, a, b, accuracy, name):
        assert fabs(a - b) < accuracy, f'Equality {name} failed (|{a} - {b}|, {accuracy} digits)'

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float,
                     mach: float, energy: float, path: float, hold: float,
                     windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: Unit):

        self.custom_assert_equal(distance, data.distance >> Distance.Yard, 0.1, "Distance")
        self.custom_assert_equal(velocity, data.velocity >> Velocity.FPS, 5, "Velocity")
        self.custom_assert_equal(mach, data.mach, 0.005, "Mach")
        self.custom_assert_equal(energy, data.energy >> Energy.FootPound, 5, "Energy")
        self.custom_assert_equal(time, data.time, 0.06, "Time")
        self.custom_assert_equal(ogv, data.ogw >> Weight.Pound, 1, "OGV")

        if distance >= 800:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 4, 'Drop')
        elif distance >= 500:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 1, 'Drop')
        else:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 0.5, 'Drop')

        if distance > 1:
            self.custom_assert_equal(hold, data.drop_angle >> adjustment_unit, 0.5, 'Hold')

        if distance >= 800:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1.5, "Windage")
        elif distance >= 500:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1, "Windage")
        else:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 0.5, "Windage")

        if distance > 1:
            self.custom_assert_equal(wind_adjustment,
                                     data.windage_angle >> adjustment_unit, 0.5, "WAdj")

    @pytest.mark.parametrize(
        "data_point, distance, velocity, mach, energy, path, hold, windage, wind_adjustment, time, ogv, adjustment_unit",
        [
            (lambda trajectory: trajectory[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, Angular.MOA),
            (lambda trajectory: trajectory[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, Angular.MOA),
            (lambda trajectory: trajectory[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, Angular.MOA),
            (lambda trajectory: trajectory[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, Angular.MOA),
        ],
        ids=["0_yards", "100_yards", "500_yards", "1000_yards"]
    )
    def test_path_g1(self, loaded_engine_instance, data_point, distance, velocity, mach, energy, path, hold, windage,
                     wind_adjustment, time, ogv, adjustment_unit):
        dm = DragModel(0.223, TableG1, 168, 0.308, 1.282)
        ammo = Ammo(dm, Velocity(2750, Velocity.FPS))
        weapon = Weapon(Distance(2, Distance.Inch), zero_elevation=Angular(0.001228, Angular.Radian))
        atmosphere = Atmo.icao()
        shot_info = Shot(weapon=weapon, ammo=ammo, atmo=atmosphere,
                         winds=[Wind(Velocity(5, Velocity.MPH), Angular(10.5, Angular.OClock))])

        calc = Calculator(engine=loaded_engine_instance)
        data = calc.fire(shot_info, Distance.Yard(1000), Distance.Yard(100)).trajectory
        assert len(data) == 11, "Trajectory Row Count"
        self.validate_one(data_point(data), distance, velocity, mach, energy, path, hold, windage, wind_adjustment,
                          time, ogv, adjustment_unit)

    @pytest.mark.parametrize(
        "data_point, distance, velocity, mach, energy, path, hold, windage, wind_adjustment, time, ogv, adjustment_unit",
        [
            (lambda trajectory: trajectory[0], 0, 2750, 2.46, 2821, -2.0, 0.0, 0.0, 0.00, 0.000, 880, Angular.Mil),
            (lambda trajectory: trajectory[1], 100, 2545, 2.28, 2416, 0.0, 0.0, -0.2, -0.06, 0.113, 698, Angular.Mil),
            (lambda trajectory: trajectory[5], 500, 1814, 1.62, 1227, -56.2, -3.2, -6.3, -0.36, 0.672, 252, Angular.Mil),
            (lambda trajectory: trajectory[10], 1000, 1086, 0.97, 440, -399.9, -11.3, -31.6, -0.90, 1.748, 54, Angular.Mil)
        ],
        ids=["0_yards", "100_yards", "500_yards", "1000_yards"]
    )
    def test_path_g7(self, loaded_engine_instance, data_point, distance, velocity, mach, energy, path, hold, windage,
                     wind_adjustment, time, ogv, adjustment_unit):
        dm = DragModel(0.223, TableG7, 168, 0.308, 1.282)
        ammo = Ammo(dm, Velocity(2750, Velocity.FPS))
        weapon = Weapon(2, 12, zero_elevation=Angular.MOA(4.221))
        shot_info = Shot(weapon=weapon, ammo=ammo, winds=[Wind(Velocity(5, Velocity.MPH), Angular.Degree(-45))])

        calc = Calculator(engine=loaded_engine_instance)
        data = calc.fire(shot_info, Distance.Yard(1000), Distance.Yard(100)).trajectory
        assert len(data) == 11, "Trajectory Row Count"
        self.validate_one(data_point(data), distance, velocity, mach, energy, path, hold, windage, wind_adjustment,
                          time, ogv, adjustment_unit)


class TestTrajFlagName:

    def test_single_and_combined_flags(self):
        assert TrajFlag.name(TrajFlag.NONE) == 'NONE'
        assert TrajFlag.name(TrajFlag.ZERO_UP) == 'ZERO_UP'
        assert TrajFlag.name(TrajFlag.ZERO_DOWN) == 'ZERO_DOWN'
        assert TrajFlag.name(TrajFlag.ZERO) == 'ZERO'
        combo = TrajFlag.ZERO | TrajFlag.APEX | TrajFlag.MACH
        s = TrajFlag.name(combo)
        # Ensure ZERO compresses up/down and includes others
        assert 'ZERO' in s and 'APEX' in s and 'MACH' in s
        assert 'ZERO_UP' not in s and 'ZERO_DOWN' not in s

    def test_unknown_flag_returns_unknown(self):
        assert TrajFlag.name(1 << 10) == 'UNKNOWN'


class TestTrajectoryDataFilter:

    @staticmethod
    def _mk_shot(mv_fps=2600.0):
        dm = DragModel(bc=0.243, drag_table=TableG7)
        return Shot(ammo=Ammo(dm, mv=Velocity.FPS(mv_fps)), weapon=Weapon(), atmo=Atmo.icao())

    def test_range_interpolation_with_sparse_history(self,loaded_engine_instance):
        """Ensure RANGE rows are interpolated when exact hits not on step grid and only minimal history exists.

        This stresses the code path that requires prev_prev_data and prev_data to interpolate when `record_distance`
        falls between integration steps.
        """
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2400.0)
        # Pick a trajectory range and a coarse step that likely doesn't align with integration steps
        res = calc.fire(shot, trajectory_range=Distance.Yard(350), trajectory_step=Distance.Yard(137))
        # We should have RANGE rows at 0 yd (initial), then ~137yd and ~274yd plus the end
        ranges = [td for td in res.trajectory if td.flag & TrajFlag.RANGE]
        assert len(ranges) >= 2
        # Distances after the initial should be near multiples of 137 yd (within tolerance)
        yards = [td.distance >> Distance.Yard for td in ranges[:-1]]
        nonzero = [y for y in yards if y > 1.0]
        assert pytest.approx(nonzero[0], rel=0.03) == 137
        if len(nonzero) > 1:
            assert pytest.approx(nonzero[1], rel=0.03) == 274


    def test_time_step_sampling_generates_rows(self, loaded_engine_instance):
        """With time_step set, confirm rows appear even when distance-step is large (or defaulted)."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2400.0)
        # No trajectory_step specified -> default equals trajectory_range, so RANGE would be at end only.
        res = calc.fire(shot, trajectory_range=Distance.Yard(300), time_step=0.02, raise_range_error=False)
        # Expect >2 rows due to time-based recording
        assert len(res.trajectory) > 2
        # And at least one has RANGE flag set via time-step sampling
        assert any(td.flag & TrajFlag.RANGE for td in res.trajectory)


    def test_zero_up_then_zero_down_ordering(self, loaded_engine_instance):
        """Trajectory should mark ZERO_UP first then ZERO_DOWN when crossing line of sight."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2700.0)
        # Give slight positive elevation relative to look angle to ensure rise then fall across sight-line.
        shot.weapon = Weapon(sight_height=Distance.Inch(2), zero_elevation=Angular.MOA(3.0))
        res = calc.fire(shot, trajectory_range=Distance.Yard(400), trajectory_step=Distance.Yard(10),
                        flags=TrajFlag.ZERO)
        flags = [td.flag for td in res.trajectory if td.flag & TrajFlag.ZERO]
        # If zero crossings exist, the first should include ZERO_UP, and later one ZERO_DOWN
        if flags:
            # ZERO combines UP/DOWN, but during first crossing it should include UP before DOWN appears
            assert flags[0] & TrajFlag.ZERO_UP
            if len(flags) > 1:
                assert flags[-1] & TrajFlag.ZERO_DOWN


    def test_mach_crossing_detected_with_tight_steps(self, loaded_engine_instance):
        """Ensure MACH crossing is detected even when range/time steps are relatively large by enabling flags."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(3000.0)  # clearly supersonic
        res = calc.fire(shot, trajectory_range=Distance.Yard(1200), trajectory_step=Distance.Yard(200),
                        time_step=0.01, flags=TrajFlag.MACH)
        assert res.flag(TrajFlag.MACH) is not None


    def test_zero_down_only_when_start_above(self, loaded_engine_instance):
        """Starting above sight-line should suppress ZERO_UP and allow ZERO_DOWN only."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2650.0)
        # Negative sight height => initial y > 0 relative to sight line
        shot.weapon = Weapon(sight_height=Distance.Inch(-2), zero_elevation=Angular.Degree(0.0))
        res = calc.fire(shot, trajectory_range=Distance.Yard(400), trajectory_step=Distance.Yard(25),
                        flags=TrajFlag.ZERO)
        assert res.flag(TrajFlag.ZERO_UP) is None
        assert res.flag(TrajFlag.ZERO_DOWN) is not None


    def test_range_steps_do_not_exceed_limit(self, loaded_engine_instance):
        """RANGE sampling should not produce samples beyond the specified range limit."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2500.0)
        rng = Distance.Yard(250)
        step = Distance.Yard(60)
        res = calc.fire(shot, trajectory_range=rng, trajectory_step=step)
        limit_yards = rng >> Distance.Yard
        range_rows = [td for td in res.trajectory if td.flag & TrajFlag.RANGE]
        assert len(range_rows) >= 2
        for row in range_rows:
            assert (row.distance >> Distance.Yard) <= limit_yards + 1e-6


    def test_apex_flag_once(self, loaded_engine_instance):
        """APEX should be flagged at most once and then suppressed for the rest of the trajectory."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(800.0)
        shot.weapon.zero_elevation = Angular.Degree(5.0)
        res = calc.fire(shot, trajectory_range=Distance.Yard(800), trajectory_step=Distance.Yard(25),
                        flags=TrajFlag.APEX)
        apex_rows = [td for td in res.trajectory if td.flag & TrajFlag.APEX]
        assert len(apex_rows) == 1


    def test_zero_and_mach_flags_both_present(self, loaded_engine_instance):
        """Requesting ZERO and MACH together should yield both events when physically applicable."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(3000.0)
        shot.weapon.zero_elevation = Angular.MOA(2.0)
        res = calc.fire(shot, trajectory_range=Distance.Yard(1200), trajectory_step=Distance.Yard(100),
                        flags=TrajFlag.ZERO | TrajFlag.MACH)
        assert res.flag(TrajFlag.MACH) is not None
        zero_rows = [td for td in res.trajectory if td.flag & TrajFlag.ZERO]
        assert len(zero_rows) >= 1


    def test_no_rows_closer_than_merge_threshold(self, loaded_engine_instance):
        """Ensure coalescing merges events so no two rows are within the merge time threshold."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2800.0)
        # Request multiple flags and dense-ish sampling to provoke close-by events
        res = calc.fire(shot, trajectory_range=Distance.Yard(500), trajectory_step=Distance.Yard(50),
                        time_step=0.001, flags=TrajFlag.ALL, raise_range_error=False)
        dt_thresh = BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA
        times = [td.time for td in res.trajectory]
        diffs = [t2 - t1 for t1, t2 in zip(times, times[1:])]
        assert all(abs(d) >= dt_thresh for d in diffs)


    def test_zero_event_coalesces_onto_range_row(self, loaded_engine_instance):
        """A ZERO crossing should appear on a RANGE-sampled row when timestamps align closely (coalesced flags)."""
        calc = Calculator(engine=loaded_engine_instance)
        shot = self._mk_shot(2750.0)
        # Set zero at 200 yd, then sample RANGE at 200 yd so ZERO and RANGE align
        calc.set_weapon_zero(shot, Distance.Yard(200))
        res = calc.fire(shot, trajectory_range=Distance.Yard(600), trajectory_step=Distance.Yard(200),
                        flags=TrajFlag.ZERO)
        # Find any ZERO row that also includes RANGE flag (coalesced)
        coalesced = [td for td in res.trajectory if (td.flag & TrajFlag.ZERO) and (td.flag & TrajFlag.RANGE)]
        assert len(coalesced) >= 1


    def test_combined_flags(self, loaded_engine_instance):
        """Test that combined flags are correctly set in the trajectory"""
        dm = DragModel(bc=0.243, drag_table=TableG7)
        shot = Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))
        calc = Calculator(engine=loaded_engine_instance)
        calc.set_weapon_zero(shot, zero_distance=Distance.Meter(200))
        hit_result = calc.fire(shot, trajectory_range=Distance.Meter(300),
                               trajectory_step=Distance.Meter(100), flags=TrajFlag.ALL)
        td = hit_result.flag(TrajFlag.ZERO_DOWN)
        assert td is not None, 'Expected to find a ZERO_DOWN flag in trajectory'
        assert td.flag == TrajFlag.ZERO_DOWN | TrajFlag.RANGE, 'ZERO_DOWN should occur on a RANGE row'
