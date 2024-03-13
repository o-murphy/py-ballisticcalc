import unittest
from py_ballisticcalc import *


class TestDangerSpace(unittest.TestCase):

    def setUp(self) -> None:
        self.look_angle = Angular.Degree(0)
        weight, diameter = 168, 0.308
        length = Distance.Inch(1.282)
        dm = DragModel(0.223, TableG7, weight, diameter, length)
        ammo = Ammo(dm, Velocity.FPS(2750), Temperature.Celsius(15))
        ammo.calc_powder_sens(2723, 0)
        current_winds = [Wind(2, 90)]
        shot = Shot(weapon=Weapon(), ammo=ammo, winds=current_winds)
        calc = Calculator()
        calc.set_weapon_zero(shot, Distance.Foot(300))
        self.shot_result = calc.fire(shot, trajectory_range=Distance.Yard(1000), trajectory_step=Distance.Yard(100), extra_data=True)

    def test_danger_space(self):
        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Meter(1.5), self.look_angle
        )

        self.assertAlmostEqual(
            round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy), 393.6, 0)
        self.assertAlmostEqual(
            round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy), 579.0, 0)

        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Inch(10), self.look_angle
        )

        self.assertAlmostEqual(
            round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy), 484.5, 0)
        self.assertAlmostEqual(
            round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy), 514.8, 0)
