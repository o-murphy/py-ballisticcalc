import pytest

from py_ballisticcalc import *


class TestDangerSpace:

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance) -> None:
        self.look_angle = Angular.Degree(0)
        weight, diameter = 168, 0.308
        length = Distance.Inch(1.282)
        dm = DragModel(0.223, TableG7, weight, diameter, length)
        ammo = Ammo(dm, Velocity.FPS(2750), Temperature.Celsius(15))
        ammo.calc_powder_sens(2723, 0)
        current_winds = [Wind(2, 90)]
        shot = Shot(weapon=Weapon(Distance.Inch(1)), ammo=ammo, winds=current_winds)
        calc = Calculator(engine=loaded_engine_instance)
        calc.set_weapon_zero(shot, Distance.Foot(300))
        self.shot_result = calc.fire(shot, trajectory_range=Distance.Yard(1000), trajectory_step=Distance.Yard(1),
                                     extra_data=True)

    def test_danger_space(self):
        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Meter(1.5), self.look_angle
        )

        assert pytest.approx(round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 388.0
        assert pytest.approx(round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 581.0

        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Inch(10), self.look_angle
        )

        assert pytest.approx(round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 483.0
        assert pytest.approx(round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 516.0

    def test_extra_data(self):
        """With extra_data=True, the trajectory should include points for ZERO and MACH crossings."""
        seen_zero_up = False
        seen_zero_down = False
        seen_mach = False
        for p in self.shot_result.trajectory:
            if TrajFlag(p.flag) & TrajFlag.ZERO_UP:
                seen_zero_up = True
            if TrajFlag(p.flag) & TrajFlag.ZERO_DOWN:
                seen_zero_down = True
            if TrajFlag(p.flag) & TrajFlag.MACH:
                seen_mach = True
        assert seen_zero_up, "ZERO_UP flag not found in trajectory"
        assert seen_zero_down, "ZERO_DOWN flag not found in trajectory"
        assert seen_mach, "MACH flag not found in trajectory"
