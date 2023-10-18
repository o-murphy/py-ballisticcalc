import unittest
from py_ballisticcalc import *


class TestMBC(unittest.TestCase):

    def test_mbc(self):
        mbc = MultiBC(
            drag_table=TableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            mbc_table=[{'BC': p[0], 'V': p[1]} for p in ((0.275, 800), (0.255, 500), (0.26, 700))],
        )
        dm = DragModel.from_mbc(mbc)
        ammo = Ammo(dm, 1, 800)
        cdm = TrajectoryCalc(ammo=ammo).cdm
        self.assertIsNot(cdm, None)
        ret = list(cdm)
        self.assertEqual(ret[0], {'Mach': 0.0, 'CD': 0.1259323091692403})
        self.assertEqual(ret[-1], {'Mach': 5.0, 'CD': 0.15771258594668947})

    def test_mbc_valid(self):
        # Litz's multi-bc table comversion to CDM, 338LM 285GR HORNADY ELD-M
        mbc = MultiBC(
            drag_table=TableG7,
            weight=Weight.Grain(285),
            diameter=Distance.Inch(0.338),
            mbc_table=[{'BC': p[0], 'V': Velocity.MPS(p[1])} for p in ((0.417, 745), (0.409, 662), (0.4, 580))],
        )
        cdm = mbc.cdm
        cds = [p['CD'] for p in cdm]
        machs = [p['Mach'] for p in cdm]

        reference = (
            (1, 0.3384895315),
            (2, 0.2573873416),
            (3, 0.2069547831),
            (4, 0.1652052415),
            (5, 0.1381406102),
        )

        for mach, cd in reference:
            idx = machs.index(mach)
            with self.subTest(mach=mach):
                self.assertAlmostEqual(cds[idx], cd, 3)
