import pytest

from py_ballisticcalc import Sight, Ammo, DragModel, TableG7, Unit


class TestAmmoPowderSensitivity:
    
    def test_calc_powder_sens_disallows_zero_velocity_points(self):
        dm = DragModel(0.3, TableG7)
        a = Ammo(dm, Unit.MPS(0))
        with pytest.raises(ValueError, match="positive muzzle velocities"):
            _ = a.calc_powder_sens(Unit.MPS(300), Unit.Celsius(10))

        a2 = Ammo(dm, Unit.MPS(800))
        with pytest.raises(ValueError, match="positive muzzle velocities"):
            _ = a2.calc_powder_sens(Unit.MPS(0), Unit.Celsius(10))


class TestSight:

    @pytest.mark.parametrize(
        "case",
        [
            {"td": 100, "mag": 1, 'step': 0.25 / (1 / 1) * 1, 'adj': 4},
            {"td": 200, "mag": 1, 'step': 0.25 / (2 / 1) * 1, 'adj': 8},
            {"td": 100, "mag": 10, 'step': 0.25 / (1 / 1) * 10, 'adj': 0.4},
            {"td": 200, "mag": 10, 'step': 0.25 / (2 / 1) * 10, 'adj': 0.8},
            {"td": 50, "mag": 1, 'step': 0.25 / (1 / 2) * 1, 'adj': 2},
            {"td": 50, "mag": 10, 'step': 0.25 / (1 / 2) * 10, 'adj': 0.2},
        ],
        ids=[f"td={c['td']}, mag={c['mag']}" for c in [
            {"td": 100, "mag": 1},
            {"td": 200, "mag": 1},
            {"td": 100, "mag": 10},
            {"td": 200, "mag": 10},
            {"td": 50, "mag": 1},
            {"td": 50, "mag": 10},
        ]]
    )
    def test_sfp(self, case):
        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane='SFP',
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        step = s._adjust_sfp_reticle_steps(Unit.Meter(case['td']), case['mag']).vertical.unit_value
        assert pytest.approx(step, abs=1e-6) == case['step']

        adj = s.get_adjustment(Unit.Meter(case['td']), Unit.Mil(1), Unit.Mil(1), case['mag']).vertical
        assert pytest.approx(adj, abs=1e-6) == case['adj']

    @pytest.mark.parametrize(
        "case",
        [
            {"td": 100, "mag": 1, 'adj': 4},
            {"td": 200, "mag": 1, 'adj': 4},
            {"td": 100, "mag": 2, 'adj': 4},
            {"td": 200, "mag": 2, 'adj': 4},
            {"td": 100, "mag": 10, 'adj': 4},
            {"td": 200, "mag": 10, 'adj': 4},
            {"td": 50, "mag": 1, 'adj': 4},
            {"td": 50, "mag": 10, 'adj': 4},
        ],
        ids=[f"td={c['td']}, mag={c['mag']}" for c in [
            {"td": 100, "mag": 1},
            {"td": 200, "mag": 1},
            {"td": 100, "mag": 2},
            {"td": 200, "mag": 2},
            {"td": 100, "mag": 10},
            {"td": 200, "mag": 10},
            {"td": 50, "mag": 1},
            {"td": 50, "mag": 10},
        ]]
    )
    def test_ffp(self, case):
        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane='FFP',
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        adj = s.get_adjustment(Unit.Meter(case['td']),
                               Unit.Mil(1),
                               Unit.Mil(1),
                               case['mag']).vertical
        assert pytest.approx(adj, abs=1e-7) == case['adj']

    @pytest.mark.parametrize(
        "case",
        [
            {"td": 100, "mag": 1, 'adj': 4},
            {"td": 200, "mag": 1, 'adj': 4},
            {"td": 100, "mag": 2, 'adj': 8},
            {"td": 200, "mag": 2, 'adj': 8},
            {"td": 100, "mag": 10, 'adj': 40},
            {"td": 200, "mag": 10, 'adj': 40},
            {"td": 50, "mag": 1, 'adj': 4},
            {"td": 50, "mag": 10, 'adj': 40},
        ],
        ids=[f"td={c['td']}, mag={c['mag']}" for c in [
            {"td": 100, "mag": 1},
            {"td": 200, "mag": 1},
            {"td": 100, "mag": 2},
            {"td": 200, "mag": 2},
            {"td": 100, "mag": 10},
            {"td": 200, "mag": 10},
            {"td": 50, "mag": 1},
            {"td": 50, "mag": 10},
        ]]
    )
    def test_lwir(self, case):
        click_size = Unit.Mil(0.25)
        s = Sight(focal_plane='LWIR',
                  scale_factor=Unit.Meter(100),
                  h_click_size=click_size,
                  v_click_size=click_size)

        adj = s.get_adjustment(Unit.Meter(case['td']),
                               Unit.Mil(1),
                               Unit.Mil(1),
                               case['mag']).vertical
        assert pytest.approx(adj, abs=1e-7) == case['adj']


class TestSightInvalidInputs:
    def setup_method(self):
        self.click = Unit.Mil(0.25)

    @pytest.mark.parametrize("mag", [0.0, -1.0])
    @pytest.mark.parametrize("fp", ["SFP", "FFP", "LWIR"]) 
    def test_magnification_must_be_positive(self, fp, mag):
        s = Sight(
            focal_plane=fp,
            scale_factor=Unit.Meter(100),
            h_click_size=self.click,
            v_click_size=self.click,
        )
        with pytest.raises(ValueError, match="magnification must be positive"):
            _ = s.get_adjustment(Unit.Meter(100), Unit.Mil(1), Unit.Mil(1), mag)

    def test_sfp_requires_positive_target_distance(self):
        s = Sight(
            focal_plane="SFP",
            scale_factor=Unit.Meter(100),
            h_click_size=self.click,
            v_click_size=self.click,
        )
        with pytest.raises(ValueError, match="target_distance must be positive"):
            _ = s.get_adjustment(Unit.Meter(0), Unit.Mil(1), Unit.Mil(1), 5.0)
