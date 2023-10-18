import unittest
from py_ballisticcalc import *


class TestInterface(unittest.TestCase):

    def setUp(self) -> None:
        dm = DragModel(0.22, TableG7, 168, 0.308)
        self.ammo = Ammo(dm, 1.22, Velocity(2600, Velocity.FPS))
        self.atmosphere = Atmo.icao()
