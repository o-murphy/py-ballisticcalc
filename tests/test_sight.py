import unittest

from py_ballisticcalc import Sight, Unit


class TestSight(unittest.TestCase):

    def test_sfp(self):

        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane=Sight.FocalPlane.SFP,
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        cases = [
            {"td": 100, "mag": 1, 'step': 0.25 / (1 / 1) * 1, 'adj': 4},
            {"td": 200, "mag": 1, 'step': 0.25 / (2 / 1) * 1, 'adj': 8},
            {"td": 100, "mag": 10, 'step': 0.25 / (1 / 1) * 10, 'adj': 0.4},
            {"td": 200, "mag": 10, 'step': 0.25 / (2 / 1) * 10, 'adj': 0.8},
            {"td": 50, "mag": 1, 'step': 0.25 / (1 / 2) * 1, 'adj': 2},
            {"td": 50, "mag": 10, 'step': 0.25 / (1 / 2) * 10, 'adj': 0.2},
        ]

        for case in cases:
            with self.subTest(case=case):
                step = s._adjust_sfp_reticle_steps(Unit.Meter(case['td']), case['mag']).vertical.unit_value
                self.assertAlmostEqual(step, case['step'], places=6)

        for case in cases:
            with self.subTest(case=case):
                adj = s.get_adjustment(Unit.Meter(case['td']), Unit.Mil(1), Unit.Mil(1), case['mag']).vertical
                self.assertAlmostEqual(adj, case['adj'], places=6)

    def test_ffp(self):
        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane=Sight.FocalPlane.FFP,
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        cases = [
            {"td": 100, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 200, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 100, "mag": 2, 'step': 0.25, 'adj': 4},
            {"td": 200, "mag": 2, 'step': 0.25, 'adj': 4},
            {"td": 100, "mag": 10, 'step': 0.25, 'adj': 4},
            {"td": 200, "mag": 10, 'step': 0.25, 'adj': 4},
            {"td": 50, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 50, "mag": 10, 'step': 0.25, 'adj': 4},
        ]

        for case in cases:
            with self.subTest(case=case):
                adj = s.get_adjustment(Unit.Meter(case['td']),
                                       Unit.Mil(1),
                                       Unit.Mil(1),
                                       case['mag']).vertical
                self.assertAlmostEqual(adj, case['adj'], places=7)

    def test_lwir(self):
        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane=Sight.FocalPlane.LWIR,
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        cases = [
            {"td": 100, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 200, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 100, "mag": 2, 'step': 0.25, 'adj': 8},
            {"td": 200, "mag": 2, 'step': 0.25, 'adj': 8},
            {"td": 100, "mag": 10, 'step': 0.25, 'adj': 40},
            {"td": 200, "mag": 10, 'step': 0.25, 'adj': 40},
            {"td": 50, "mag": 1, 'step': 0.25, 'adj': 4},
            {"td": 50, "mag": 10, 'step': 0.25, 'adj': 40},
        ]

        for case in cases:
            with self.subTest(case=case):
                adj = s.get_adjustment(Unit.Meter(case['td']),
                                       Unit.Mil(1),
                                       Unit.Mil(1),
                                       case['mag']).vertical
                self.assertAlmostEqual(adj, case['adj'], places=7)