import unittest
from py_ballisticcalc import *


class TestPerformance(unittest.TestCase):
    def setUp(self) -> None:
        self.dm = DragModel(0.223, TableG7, 168, 0.308)
        self.ammo = Ammo(self.dm, 1.282, 2750)
        self.weapon = Weapon(2, 11.24, zero_elevation=Angular.MOA(4.221))
        self.atmo = Atmo.icao()
        self.shot = Shot(weapon=self.weapon, winds=[Wind(Velocity(5, Velocity.MPH), -45)])
        self.calc = TrajectoryCalc(self.ammo)

    def test__init__(self):
        self.assertTrue(self.calc)

    def test_elevation_performance(self):
        self.calc.zero_angle(self.weapon, self.atmo, Distance.Yard(100), Angular.Degree(0))

    def test_path_performance(self):
        d = self.calc.trajectory(self.shot, Distance.Yard(1000), Distance.Yard(100))
        # [print(p.formatted()) for p in d]
