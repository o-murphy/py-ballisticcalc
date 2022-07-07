from py_ballisticcalc.extended import MultipleBallisticCoefficient
from py_ballisticcalc.extended import ProfileExtended
from py_ballisticcalc.drag import *
from py_ballisticcalc.bmath import *
import unittest


class TestMultipleBC(unittest.TestCase):

    def setUp(self) -> None:
        self.mbc = MultipleBallisticCoefficient([[0.275, 800], [0.26, 700], [0.255, 500], ],
                                                unit.VelocityMPS,
                                                DragTableG7,
                                                unit.Distance(0.308, unit.DistanceInch),
                                                unit.Weight(178, unit.WeightGrain))

    def test_calculate_custom_drag_func(self):
        custom_drag_function = self.mbc.calculate_custom_drag_func()

        self.assertEqual(custom_drag_function[0], {'A': 0.0, 'B': 0.1259323091692403})
        self.assertEqual(custom_drag_function[26], {'A': 1.0, 'B': 0.3997667543995166})
        self.assertEqual(custom_drag_function[48], {'A': 2.0, 'B': 0.3077230217436949})
        self.assertEqual(custom_drag_function[68], {'A': 3.0, 'B': 0.24187353100644302})
        self.assertEqual(custom_drag_function[78], {'A': 4.0, 'B': 0.1898670957891984})

    def test_create_multiple_ballistic_coefficient(self):
        bc = self.mbc.create_extended_ballistic_coefficient()
        self.assertLess(math.fabs(bc.value - 0.2683212330707692), 1e-4)
        self.assertLess(math.fabs(bc.standard_cd(1) - 0.3997667543995166), 1e-8)
        self.assertLess(math.fabs(bc.standard_cd(3) - 0.24187353100644302), 1e-8)
        self.assertLess(math.fabs(bc.calculated_cd(3) - 0.24163165747543655), 1e-8)


class TestProfileExtended(unittest.TestCase):

    def test_profile_bc(self):
        p = ProfileExtended(
            maximum_distance=(2500, unit.DistanceMeter),
            distance_step=(1, unit.DistanceMeter),
            # maximum_step_size=(5, unit.DistanceFoot)
        )

        data = p.trajectory_data

        self.assertLess(math.fabs(-0.2952755905 - data[0].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-2.4677575464e-05 - data[1].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-6.1696307895 - data[5].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-48.439433788 - data[10].drop.get_in(unit.DistanceFoot)), 1e-8)

    def test_profile_custom(self):
        mbc = MultipleBallisticCoefficient([[0.275, 800], [0.255, 500], [0.26, 700], ],
                                           unit.VelocityMPS,
                                           DragTableG7,
                                           unit.Distance(0.308, unit.DistanceInch),
                                           unit.Weight(178, unit.WeightGrain))
        custom_df = mbc.calculate_custom_drag_func()
        p = ProfileExtended(drag_table=0, custom_drag_function=custom_df)
        data = p.trajectory_data

        self.assertLess(math.fabs(-0.2952755905 - data[0].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-2.2291008548e-05 - data[1].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-5.9005867893 - data[5].drop.get_in(unit.DistanceFoot)), 1e-8)
        self.assertLess(math.fabs(-44.378399173 - data[10].drop.get_in(unit.DistanceFoot)), 1e-8)
