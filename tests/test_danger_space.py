import unittest
from py_ballisticcalc import *


class TestDangerSpace(unittest.TestCase):

    def setUp(self) -> None:
        self.look_angle = Angular.Degree(0)
        weight, diameter = 168, 0.308
        length = Distance.Inch(1.282)
        weapon = Weapon(0)
        dm = DragModel(0.223, TableG7, weight, diameter)
        ammo = Ammo(dm, length, Velocity.FPS(2750), Temperature.Celsius(15))
        ammo.calc_powder_sens(2723, 0)
        calc = Calculator()
        current_atmo = Atmo(110, 1000, 15, 72)
        current_winds = [Wind(2, 90)]
        shot = Shot(weapon=weapon, ammo=ammo, atmo=current_atmo, winds=current_winds)
        calc.set_weapon_zero(shot, Distance.Foot(300))
        self.shot_result = calc.fire(shot, trajectory_range=Distance.Yard(1000), trajectory_step=Distance.Yard(100), extra_data=True)

    def test_danger_space(self):
        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Meter(1.5), self.look_angle
        )

        self.assertAlmostEqual(
            round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy), 392.833, 2)
        self.assertAlmostEqual(
            round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy), 579.499, 2)

        danger_space = self.shot_result.danger_space(
            Distance.Yard(500), Distance.Inch(10), self.look_angle
        )

        self.assertAlmostEqual(
            round(danger_space.begin.distance >> Distance.Yard, Distance.Yard.accuracy), 484.367, 2)
        self.assertAlmostEqual(
            round(danger_space.end.distance >> Distance.Yard, Distance.Yard.accuracy), 514.967, 2)
