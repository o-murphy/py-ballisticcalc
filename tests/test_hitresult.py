import pytest

from py_ballisticcalc import *

pytestmark = pytest.mark.engine

class TestHitResult:

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance) -> None:
        weight, diameter = 168, 0.308
        length = Distance.Inch(1.282)
        dm = DragModel(0.223, TableG7, weight, diameter, length)
        ammo = Ammo(dm, Velocity.FPS(2750), Temperature.Celsius(15))
        ammo.calc_powder_sens(2723, 0)
        current_winds = [Wind(2, 90)]
        self.shot = Shot(weapon=Weapon(Distance.Inch(1)), ammo=ammo, winds=current_winds)
        self.calc = Calculator(engine=loaded_engine_instance)
        self.calc.set_weapon_zero(self.shot, Distance.Foot(300))
        self.shot_result = self.calc.fire(self.shot, trajectory_range=Distance.Yard(1000),
                                          trajectory_step=Distance.Yard(10), flags=TrajFlag.ALL)

    def test_flags(self):
        zero_up = self.shot_result.flag(TrajFlag.ZERO_UP)
        assert zero_up is not None, "ZERO_UP flag not found in HitResult"
        assert pytest.approx(zero_up.distance >> Distance.Yard, abs=0.5) == 40.5, "ZERO_UP distance"

        zero_dn = self.shot_result.flag(TrajFlag.ZERO_DOWN)
        assert zero_dn is not None, "ZERO_DOWN flag not found in HitResult"
        assert pytest.approx(zero_dn.distance >> Distance.Yard, abs=0.5) == 100.0, "ZERO_DOWN distance"

        apex = self.shot_result.flag(TrajFlag.APEX)
        assert apex is not None, "APEX flag not found in HitResult"
        assert pytest.approx(apex.distance >> Distance.Yard, abs=0.5) == 70.5, "APEX distance"

        mach = self.shot_result.flag(TrajFlag.MACH)
        assert mach is not None, "MACH flag not found in HitResult"
        assert pytest.approx(mach.distance >> Distance.Yard, abs=0.5) == 963.0, "MACH distance"

    def test_get_at_unrequested_flag(self):
        hr = self.calc.fire(self.shot, trajectory_range=Distance.Meter(100), flags=TrajFlag.RANGE)
        with pytest.raises(AttributeError):
            _ = hr.flag(TrajFlag.ZERO)

    def test_danger_space(self):
        # Danger space on downward trajectory
        danger_space = self.shot_result.danger_space(Distance.Yard(500), Distance.Meter(1.5))
        assert pytest.approx(danger_space.begin.distance >> Distance.Yard, abs=0.5) == 388.7
        assert pytest.approx(danger_space.end.distance >> Distance.Yard, abs=0.5) == 580.8

        # Danger space beginning at muzzle
        danger_space = self.shot_result.danger_space(Distance.Yard(200), Distance.Inch(10))
        assert pytest.approx(danger_space.begin.distance >> Distance.Yard, abs=0.5) == 0.0
        assert pytest.approx(danger_space.end.distance >> Distance.Yard, abs=0.5) == 254.7

        # Danger space extending past end of computed trajectory
        danger_space = self.shot_result.danger_space(Distance.Yard(990), Distance.Yard(1))
        assert pytest.approx(danger_space.begin.distance >> Distance.Yard, abs=0.5) == 974.9
        assert pytest.approx(danger_space.end.distance >> Distance.Yard, abs=0.5) == 1000.0

        # Danger space on upward trajectory with slant
        self.shot.look_angle = Angular.Degree(10)
        self.shot.relative_angle = Angular.Degree(2)
        high_shot_result = self.calc.fire(self.shot, trajectory_range=Distance.Yard(300),
                                          trajectory_step=Distance.Yard(10), flags=TrajFlag.ALL)
        danger_space = high_shot_result.danger_space(Distance.Yard(100), Distance.Yard(1))
        assert pytest.approx(danger_space.begin.slant_distance >> Distance.Yard, abs=0.5) == 85.6
        assert pytest.approx(danger_space.end.slant_distance >> Distance.Yard, abs=0.5) == 114.5

    def test_tiny_step(self):
        """Test that tiny range-steps are backfilled correctly"""
        dm = DragModel(bc=0.2, drag_table=TableG7)
        atmo = Atmo.icao()
        _, mach = atmo.get_density_and_mach_for_altitude(0)
        shot = Shot(ammo=Ammo(dm, mv=Velocity.FPS(mach)))
        result = self.calc.fire(shot, trajectory_range=Distance.Meter(1),
                            trajectory_step=Distance.Meter(0.2), flags=TrajFlag.ALL)
        assert len(result) == 6, "Result should have 6 TrajectoryData rows"
        expected_flags = TrajFlag.RANGE | TrajFlag.ZERO_DOWN | TrajFlag.MACH
        assert (result[0].flag & expected_flags) == expected_flags, \
            "First row should have RANGE, ZERO_DOWN, and MACH flags"
