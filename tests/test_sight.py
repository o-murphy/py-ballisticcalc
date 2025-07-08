import pytest

from py_ballisticcalc import Sight, Unit


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
