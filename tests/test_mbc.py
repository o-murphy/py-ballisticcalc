import unittest
from typing import NamedTuple

from py_ballisticcalc import *
from py_ballisticcalc.trajectory_calc import calculate_curve, calculate_by_curve


class TestMBC(unittest.TestCase):

    def test_multibc2drg(self):

        cIcao1MachFPS = 1116.4499224539381
        curve = calculate_curve(TableG7)
        class TestData(NamedTuple):
            name: str
            w: float
            d: float
            g7: list[float]
            cd: list[float]
            ff: list[float]

        velocities = [1500, 2000, 2500, 3000]

        test_data = (
            TestData(
                "Berger .308 168gr BT",
                168,
                1.220,
                [0.224, 0.227, 0.234, 0.239],
                [0.414, 0.350, 0.307, 0.276],
                [1.128, 1.116, 1.079, 1.060],
            ),
            TestData(
                "SMK .308 168gr",
                168,
                1.215,
                [0.211, 0.214, 0.222, 0.226],
                [0.441, 0.371, 0.325, 0.291],
                [1.201, 1.184, 1.142, 1.119],
            ),
            TestData(
                "SMK .338 300gr",
                300,
                1.7,
                [0.370, 0.374, 0.386, 0.393],
                [0.373, 0.315, 0.276, 0.248],
                [1.015, 1.004, 0.971, 0.954],
            ),
            TestData(
                "HORNADY .338 250gr BTHP",
                250,
                1.567,
                [0.314, 0.317, 0.327, 0.332],
                [0.366, 0.309, 0.272, 0.244],
                [0.996, 0.987, 0.956, 0.940],
            )
        )


        """
        i = CD / CDst
        SD = (w / 7000) / d^2
        BC = SD * (1 / i)
        i = SD / BC
        BC = SD / i
        """


        for bullet in test_data:

            with self.subTest(bullet.name):

                b = tuple(zip(bullet.g7, bullet.ff, bullet.cd, velocities))

                mbc = MultiBC(
                    drag_table=TableG7,
                    weight=Weight.Grain(bullet.w),
                    diameter=Distance.Inch(bullet.d),
                    mbc_table = [{'BC': BC, 'V': V} for BC, I, CD, V in b]
                )

                sd = mbc._get_sectional_density()

                print("i\tI\tCDst\tCD")
                for BC, I, CD, V in b:
                    with self.subTest(f"{bullet.name} {BC}"):

                        cd = calculate_by_curve(TableG7, curve, V / cIcao1MachFPS)

                        i = mbc._get_form_factor(BC)
                        print(f"{i}\t{I}\t{cd}\t{CD}")
                        # self.assertAlmostEqual(cd, CD, places=1)


    # def test_mbc(self):
    #     mbc = MultiBC(
    #         drag_table=TableG7,
    #         weight=Weight(178, Weight.Grain),
    #         diameter=Distance(0.308, Distance.Inch),
    #         mbc_table=[{'BC': p[0], 'V': p[1]} for p in ((0.275, 800), (0.255, 500), (0.26, 700))],
    #     )
    #     cdm = mbc.cdm
    #     self.assertEqual(cdm[0], {'Mach': 0.0, 'CD': 0.1259323091692403})
    #     self.assertEqual(cdm[-1], {'Mach': 5.0, 'CD': 0.1577125859466895})
    #
    # def test_mbc_valid(self):
    #     # Litz's multi-bc table comversion to CDM, 338LM 285GR HORNADY ELD-M
    #     mbc = MultiBC(
    #         drag_table=TableG7,
    #         weight=Weight.Grain(285),
    #         diameter=Distance.Inch(0.338),
    #         mbc_table=[{'BC': p[0], 'V': Velocity.MPS(p[1])} for p in ((0.417, 745), (0.409, 662), (0.4, 580))],
    #     )
    #     cdm = mbc.cdm
    #     cds = [p['CD'] for p in cdm]
    #     machs = [p['Mach'] for p in cdm]
    #
    #     reference = (
    #         (1, 0.3384895315),
    #         (2, 0.2573873416),
    #         (3, 0.2069547831),
    #         (4, 0.1652052415),
    #         (5, 0.1381406102),
    #     )
    #
    #     for mach, cd in reference:
    #         idx = machs.index(mach)
    #         with self.subTest(mach=mach):
    #             self.assertAlmostEqual(cds[idx], cd, 3)
