import pytest

from py_ballisticcalc import *


@pytest.mark.usefixtures("loaded_engine_instance")
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
        shot = Shot(weapon=Weapon(), ammo=ammo, winds=current_winds)
        calc = Calculator(_engine=loaded_engine_instance)
        calc.set_weapon_zero(shot, Distance.Foot(300))
        self.shot_result = calc.fire(shot, trajectory_range=Distance.Yard(1000), trajectory_step=Distance.Yard(1),
                                     extra_data=True)

    def test_danger_space(self):
        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Meter(1.5), self.look_angle
        )

        assert pytest.approx(round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 393.0
        assert pytest.approx(round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 579.0

        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Inch(10), self.look_angle
        )

        assert pytest.approx(round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 484.5
        assert pytest.approx(round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy),
                             abs=0.5) == 514.8
