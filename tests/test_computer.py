import copy
import pytest

from py_ballisticcalc import (Ammo, Atmo, BaseEngineConfigDict, Calculator, DragModel, RangeError, Shot,
                              TableG7, Vacuum, Weapon, Wind)
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

class TestComputer:

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance):
        self.range = Distance.Yard(1000)
        self.step = Distance.Yard(100)
        self.dm = DragModel(0.22, TableG7, 168, 0.308, 1.22)
        self.ammo = Ammo(self.dm, Velocity.FPS(2600))
        self.weapon = Weapon(4, 12)
        self.atmosphere = Atmo.icao()
        self.calc = Calculator(engine=loaded_engine_instance)
        self.baseline_shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere)
        self.baseline_trajectory = self.calc.fire(
            shot=self.baseline_shot, trajectory_range=self.range, trajectory_step=self.step
        )

    #region Cant
    def test_cant_zero_elevation(self):
        """Cant_angle = 90 degrees with zero barrel elevation should match baseline with:
            drop+=sight_height, windage-=sight_height
        """
        canted = copy.copy(self.baseline_shot)
        canted.cant_angle = Angular.Degree(90)
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t.trajectory[5].height.raw_value - self.weapon.sight_height.raw_value) == \
               self.baseline_trajectory[5].height.raw_value
        assert pytest.approx(t.trajectory[5].windage.raw_value + self.weapon.sight_height.raw_value) == \
               self.baseline_trajectory[5].windage.raw_value

    def test_cant_positive_elevation(self):
        """Cant_angle = 90 degrees with positive barrel elevation and zero twist should match baseline with:
            drop+=sight_height, windage-=sight_height at muzzle, increasingly positive down-range
        """
        canted = Shot(weapon=Weapon(sight_height=self.weapon.sight_height, twist=0, zero_elevation=Angular.Mil(2)),
                      ammo=self.ammo, atmo=self.atmosphere, cant_angle=Angular.Degree(90))
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t.trajectory[5].height.raw_value - self.weapon.sight_height.raw_value,
                             abs=1e-2) == pytest.approx(self.baseline_trajectory[5].height.raw_value, abs=1e-2)
        assert pytest.approx(t.trajectory[0].windage.raw_value) == -self.weapon.sight_height.raw_value
        assert t.trajectory[5].windage.raw_value > t.trajectory[3].windage.raw_value

    def test_cant_zero_sight_height(self):
        """Cant_angle = 90 degrees with sight_height=0 and barrel_elevation=0 should match baseline with:
            drop+=baseline.sight_height, windage no change
        """
        canted = Shot(weapon=Weapon(sight_height=0, twist=self.weapon.twist),
                      ammo=self.ammo, atmo=self.atmosphere, cant_angle=Angular.Degree(90))
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t.trajectory[5].height.raw_value - self.weapon.sight_height.raw_value) == \
               self.baseline_trajectory[5].height.raw_value
        assert pytest.approx(t.trajectory[5].windage.raw_value) == self.baseline_trajectory[5].windage.raw_value
    # endregion Cant

    # region Wind
    def test_wind_from_left(self):
        """Wind from left should increase windage"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(3, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].windage.raw_value > self.baseline_trajectory[5].windage.raw_value

    def test_wind_from_right(self):
        """Wind from right should decrease windage"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(9, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].windage.raw_value < self.baseline_trajectory[5].windage.raw_value

    def test_wind_from_back(self):
        """Wind from behind should decrease drop"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(0, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value > self.baseline_trajectory[5].height.raw_value

    def test_wind_from_front(self):
        """Wind from in front should increase drop"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(6, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value < self.baseline_trajectory[5].height.raw_value

    def test_wind_lag_rule(self):
        """Lag rule: Windage due to crosswind v_w = t_lag * v_w"""
        v_w = Velocity.FPS(5)  # crosswind velocity
        crosswind = Wind(v_w, Angular(3, Angular.OClock))
        # Use default weapon with no twist to eliminate spin drift:
        base_shot = Shot(ammo=self.ammo, atmo=Atmo.icao(), winds=[crosswind])
        base = self.calc.fire(base_shot, trajectory_range=self.range, trajectory_step=self.step)
        vacuum_shot = Shot(ammo=self.ammo, atmo=Vacuum(), winds=[crosswind])
        vac = self.calc.fire(vacuum_shot, trajectory_range=self.range, trajectory_step=self.step)
        t_lag = base[5].time - vac[5].time
        assert pytest.approx(base[5].windage >> Distance.Feet) == t_lag * (v_w >> Velocity.FPS)

    def test_multiple_wind(self):
        """Multiple winds should be applied in order of distance"""
        no_spin_weapon = Weapon(twist=0)
        shot_right_wind = Shot(weapon=no_spin_weapon, ammo=self.ammo, atmo=self.atmosphere,
                               winds=[Wind(Velocity.MPS(4), Angular.OClock(9))])  # wind from right
        t_right = self.calc.fire(shot_right_wind, trajectory_range=self.range, trajectory_step=self.step)
        # List multiple winds, but out of order:
        shot_multi = Shot(weapon=no_spin_weapon, ammo=self.ammo, atmo=self.atmosphere,
                          winds=[Wind(Velocity.MPS(4), Angular.OClock(3), until_distance=Distance.Yard(700)),
                                 Wind(Velocity.MPS(4), Angular.OClock(9), until_distance=Distance.Yard(550))])
        t_multi = self.calc.fire(shot_multi, trajectory_range=self.range, trajectory_step=self.step)
        # Multiple winds, but last wind has no range limit:
        shot_multi_more = Shot(weapon=no_spin_weapon, ammo=self.ammo, atmo=self.atmosphere,
                               winds=[Wind(Velocity.MPS(4), Angular.OClock(9), until_distance=Distance.Yard(550)),
                                      Wind(Velocity.MPS(4), Angular.OClock(3))])
        t_multi_more = self.calc.fire(shot_multi_more, trajectory_range=self.range, trajectory_step=self.step)
        # Winds are the same to 500 yards:
        assert pytest.approx(t_multi.trajectory[5].windage.raw_value) == t_right.trajectory[5].windage.raw_value
        assert t_multi.trajectory[7].windage.raw_value > t_right.trajectory[7].windage.raw_value
        assert t_multi_more.trajectory[9].windage.raw_value > t_multi.trajectory[9].windage.raw_value

    def test_no_winds(self):
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere, winds=[])
        try:
            self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        except Exception as e:
            pytest.fail(f"self.calc.fire() raised ExceptionType unexpectedly: {e}")

        shot.winds = None
        try:
            self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        except Exception as e:
            pytest.fail(f"self.calc.fire() raised ExceptionType unexpectedly: {e}")
    # endregion Wind

    # region Twist
    def test_no_twist(self):
        """Barrel with no twist should have no spin drift"""
        shot = Shot(weapon=Weapon(twist=0), ammo=self.ammo, atmo=self.atmosphere)
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t.trajectory[5].windage.raw_value) == 0

    def test_twist(self):
        """Barrel with right-hand twist should have positive spin drift.
            Barrel with left-hand twist should have negative spin drift.
            Faster twist rates should produce larger drift.
        """
        shot = Shot(weapon=Weapon(twist=12), ammo=self.ammo, atmo=self.atmosphere)
        twist_right = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert twist_right.trajectory[5].windage.raw_value > 0
        shot = Shot(weapon=Weapon(twist=-8), ammo=self.ammo, atmo=self.atmosphere)
        twist_left = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert twist_left.trajectory[5].windage.raw_value < 0
        # Faster twist should produce larger drift:
        assert -twist_left.trajectory[5].windage.raw_value > twist_right.trajectory[5].windage.raw_value
    # endregion Twist

    # region Atmo
    def test_humidity(self):
        """Increasing relative humidity should decrease drop (due to decreasing density)"""
        humid = Atmo(humidity=.9)  # 90% humidity
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=humid)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value > self.baseline_trajectory[5].height.raw_value

    def test_temp_atmo(self):
        """Dropping temperature should increase drop (due to increasing density)"""
        cold = Atmo(temperature=Temperature.Celsius(0))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value < self.baseline_trajectory[5].height.raw_value

    def test_altitude(self):
        """Increasing altitude should decrease drop (due to decreasing density)"""
        high = Atmo.icao(Distance.Foot(5000))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=high)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value > self.baseline_trajectory[5].height.raw_value

    def test_pressure(self):
        """Decreasing pressure should decrease drop (due to decreasing density)"""
        thin = Atmo(pressure=Pressure.InHg(20.0))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=thin)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value > self.baseline_trajectory[5].height.raw_value
    # endregion Atmo

    # region Ammo
    def test_ammo_drag(self):
        """Increasing ballistic coefficient (bc) should decrease drop"""
        tdm = DragModel(self.dm.BC + 0.5, self.dm.drag_table, self.dm.weight, self.dm.diameter, self.dm.length)
        slick = Ammo(tdm, self.ammo.mv)
        shot = Shot(weapon=self.weapon, ammo=slick, atmo=self.atmosphere)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert t.trajectory[5].height.raw_value > self.baseline_trajectory[5].height.raw_value

    def test_ammo_optional(self):
        """DragModel.weight and .diameter, and Ammo.length, are only relevant when computing
            spin-drift.  Drop should match baseline with those parameters omitted.
        """
        tdm = DragModel(self.dm.BC, self.dm.drag_table)
        tammo = Ammo(tdm, mv=self.ammo.mv)
        shot = Shot(weapon=self.weapon, ammo=tammo, atmo=self.atmosphere)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t.trajectory[5].height.raw_value) == self.baseline_trajectory[5].height.raw_value

    def test_powder_sensitivity(self):
        """With _globalUsePowderSensitivity: Reducing temperature should reduce muzzle velocity"""
        self.ammo.calc_powder_sens(Velocity.FPS(2550), Temperature.Celsius(0))

        # Test case 1: Don't use powder sensitivity
        self.ammo.use_powder_sensitivity = False
        cold_no_sens = Atmo(temperature=Temperature.Celsius(-5))
        shot_no_sens = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold_no_sens)
        t_no_sens = self.calc.fire(shot=shot_no_sens, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(t_no_sens.trajectory[0].velocity.raw_value) == self.baseline_trajectory[
            0].velocity.raw_value

        # Test case 2: Powder temperature the same as atmosphere temperature
        self.ammo.use_powder_sensitivity = True
        cold_same_temp = Atmo(temperature=Temperature.Celsius(-5))
        shot_same_temp = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold_same_temp)
        t_same_temp = self.calc.fire(shot=shot_same_temp, trajectory_range=self.range, trajectory_step=self.step)
        assert t_same_temp.trajectory[0].velocity.raw_value < self.baseline_trajectory[0].velocity.raw_value

        # Test case 3: Different powder temperature
        cold_diff_temp = Atmo(powder_t=Temperature.Celsius(-5))
        shot_diff_temp = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold_diff_temp)
        t_diff_temp = self.calc.fire(shot=shot_diff_temp, trajectory_range=self.range, trajectory_step=self.step)
        assert t_diff_temp.trajectory[0].velocity.raw_value < self.baseline_trajectory[0].velocity.raw_value

        self.ammo.use_powder_sensitivity = False
    # endregion Ammo

    #region Coriolis
    def test_coriolis_flat_approximation(self):
        """Flat-fire Coriolis approximation based on latitude only (no azimuth)."""
        # Ensure that shot.weapon has no twist so we don't add gyroscopic drift
        shot = Shot(ammo=self.ammo, atmo=self.atmosphere)
        base = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)

        # Specify only latitude to get flat-fire approximation
        shot.latitude = 0.0
        equator = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(equator[-1].windage.raw_value) == base[-1].windage.raw_value
        assert pytest.approx(equator[-1].height.raw_value) == base[-1].height.raw_value
        shot.latitude = -40.0
        south = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert south[-1].windage.raw_value < base[-1].windage.raw_value
        shot.latitude = 80.0
        north = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert north[-1].windage.raw_value > -south[-1].windage.raw_value
        assert pytest.approx(north[-1].height.raw_value) == base[-1].height.raw_value
        with pytest.raises(ValueError):
            shot.latitude = 91.0  # Invalid latitude
            self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)

    def test_full_coriolis_by_latitude(self):
        """Shoot towards east at different latitudes."""
        # Ensure that shot.weapon has no twist so we don't add gyroscopic drift
        shot = Shot(ammo=self.ammo, atmo=self.atmosphere)
        base = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)

        shot.azimuth = 90.0  # East
        shot.latitude = 0.0
        equator = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(equator[-1].windage.raw_value) == base[-1].windage.raw_value
        assert equator[-1].height > base[-1].height, "Max vertical effect is shooting east at equator"
        shot.latitude = -40.0
        south = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert south[-1].windage < equator[-1].windage, "Windage goes left as latitude goes south"
        assert south[-1].height < equator[-1].height, "Vertical effect decreases away from equator"
        shot.latitude = 80.0
        north = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert north[-1].windage > -1*south[-1].windage, "Windage goes right as latitude goes north"
        assert north[-1].height < south[-1].height, "Vertical effect decreases away from equator"

    def test_full_coriolis_by_azimuth(self):
        """Shoot in different directions at equator (where vertical Coriolis effect is greatest)."""
        # Ensure that shot.weapon has no twist so we don't add gyroscopic drift
        shot = Shot(ammo=self.ammo, atmo=self.atmosphere)
        base = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)

        shot.latitude = 0.0
        shot.azimuth = 0.0  # North
        north = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert pytest.approx(north[-1].height.raw_value) == base[-1].height.raw_value
        shot.azimuth = 45.0
        northeast = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert northeast[-1].height > north[-1].height, "Vertical increasingly positive as we turn east"
        shot.azimuth = 270.0
        west = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        assert west[-1].height < north[-1].height, "Vertical increasingly negative as we turn west"

    def test_full_coriolis_vertical(self, loaded_engine_instance):
        """Shooting straight up, a projectile should drift west of launch.  Effect greatest at equator."""
        # Ensure that shot.weapon has no twist so we don't add gyroscopic drift
        shot = Shot(ammo=self.ammo, atmo=self.atmosphere)
        shot.relative_angle = Angular.Degree(90)  # Straight up
        calc = Calculator(config={'cMinimumVelocity': 1000}, engine=loaded_engine_instance)
        base = calc.fire(shot, trajectory_range=self.range, raise_range_error=False)
        assert base[-1].windage.raw_value == 0.0

        shot.latitude = 0.0
        shot.azimuth = 0.0  # Face North, so negative windage is west
        equator = calc.fire(shot, trajectory_range=self.range, raise_range_error=False)
        assert equator[-1].windage.raw_value < 0
        shot.latitude = 40.0
        north = calc.fire(shot, trajectory_range=self.range, raise_range_error=False)
        assert equator[-1].windage.raw_value < north[-1].windage.raw_value < 0
    # endregion Coriolis

    # region Errors and Limits
    def test_zero_velocity(self):
        """Test that firing with zero muzzle velocity raises a RangeError"""
        tdm = DragModel(self.dm.BC + 0.5, self.dm.drag_table, self.dm.weight, self.dm.diameter, self.dm.length)
        slick = Ammo(tdm, 0)
        shot = Shot(weapon=self.weapon, ammo=slick, atmo=self.atmosphere)
        with pytest.raises(RangeError):
            self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)

    def test_very_short_shot(self):
        """Ensure we always get at least two points in the trajectory"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere, winds=[])
        hit_result = self.calc.fire(shot=shot, trajectory_range=Distance.Centimeter(5))
        assert len(hit_result.trajectory) > 1

    def test_limit_start(self, loaded_engine_instance):
        """Ensure that a shot that violates config limits instantly still returns at least initial state"""
        conf = BaseEngineConfigDict(
            cMinimumAltitude=0,
        )
        calc = Calculator(config=conf, engine=loaded_engine_instance)
        shot = Shot(ammo=self.ammo)
        shot.relative_angle = Angular.Radian(-0.1)
        t = calc.fire(shot, trajectory_range=Distance.Meter(100), raise_range_error=False)
        assert len(t.trajectory) >= 1
        assert isinstance(t.error, RangeError)

    def test_find_apex_uses_no_min_velocity_and_restores(self, loaded_engine_instance):
        """Ensure decorators work correctly for find_apex, and that config is restored after."""
        # Start with a very high minimum velocity so normal integrate would stop early
        shot = copy.copy(self.baseline_shot)
        mv_fps = shot.ammo.mv >> Velocity.FPS
        calc = Calculator(config={'cMinimumVelocity': mv_fps * 0.99}, engine=loaded_engine_instance)

        # Give some elevation to allow apex finding; should succeed due to decorator
        shot.relative_angle = Angular.Degree(5)
        apex = calc.find_apex(shot)
        assert apex is not None

        # After returning, the high minimum velocity should still apply in normal fire
        res = calc.fire(shot, Distance.Yard(200), Distance.Yard(50), raise_range_error=False)
        assert res.error is not None, "Expected integrate to terminate due to MinimumVelocity"
        assert res.error.reason == RangeError.MinimumVelocityReached

    def test_maximum_drop(self, loaded_engine_instance):
        """Ensure cMaximumDrop is applied correctly, including adjustment for sight height."""
        # cMaximumDrop should be adjusted downward it start-height is negative
        dm = DragModel(bc=0.243, drag_table=TableG7)
        # Projectile starts at y=-sight_height
        sight_height = Distance.Inch(4)  # This needs to be a positive value
        shot = Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)), weapon=Weapon(sight_height=sight_height))
        shot.relative_angle = Angular.Degree(0.05)
        calc = Calculator(config={'cMaximumDrop': 0}, engine=loaded_engine_instance)
        res = calc.fire(shot, trajectory_range=Distance.Meter(500), raise_range_error=False)
        assert res.error is not None and res.error.reason == RangeError.MaximumDropReached
        assert pytest.approx(res.trajectory[0].height.raw_value) == -sight_height.raw_value
        assert res.trajectory[-1].height.raw_value <= -sight_height.raw_value
        assert res.trajectory[-1].time > 0.0

        # cMaximumDrop should not be adjusted for positive start-height
        shot.weapon.sight_height = Distance.Inch(-3)
        res = calc.fire(shot, trajectory_range=Distance.Meter(500), raise_range_error=False)
        assert res.error is not None and res.error.reason == RangeError.MaximumDropReached
        assert pytest.approx(res.trajectory[0].height.raw_value) == -shot.weapon.sight_height.raw_value
        assert res.trajectory[-1].height.raw_value <= 0.0 + 1e-9
        assert res.trajectory[-1].time > 0.0

    def test_min_altitude_downward_only(self, loaded_engine_instance):
        """cMinimumAltitude should only apply once velocity is not positive."""
        dm = DragModel(bc=0.243, drag_table=TableG7)
        shot = Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))
        shot.relative_angle = Angular.Degree(0.02)
        calc = Calculator(config={'cMinimumAltitude': 1_000}, engine=loaded_engine_instance)
        res = calc.fire(shot, trajectory_range=Distance.Meter(500), raise_range_error=False)
        assert res.error is not None and res.error.reason == RangeError.MinimumAltitudeReached
        assert res.trajectory[-1].angle.raw_value <= 0.0 + 1e-9
        assert res.trajectory[-1].time > 0.0
    # endregion Errors and Limits
