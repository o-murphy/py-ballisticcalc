import pytest

from py_ballisticcalc.conditions import Wind
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.engines.base_engine import _WindSock
from py_ballisticcalc.munition import Ammo
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import Distance, Velocity, Angular, Unit


class TestWindSock:
    def test_winds_sort(self):
        """Test that the winds are sorted by until_distance"""
        winds = [
            Wind(Unit.MPS(0), Unit.Degree(90), Unit.Meter(100)),
            Wind(Unit.MPS(1), Unit.Degree(60), Unit.Meter(300)),
            Wind(Unit.MPS(2), Unit.Degree(30), Unit.Meter(200)),
            Wind(Unit.MPS(2), Unit.Degree(30), Unit.Meter(50)),
        ]
        shot = Shot(ammo=Ammo(DragModel(0.22, TableG7), Velocity.FPS(2600)), winds=winds)
        sorted_winds = shot.winds
        assert sorted_winds[0] is winds[3]
        assert sorted_winds[1] is winds[0]
        assert sorted_winds[2] is winds[2]
        assert sorted_winds[3] is winds[1]

    def test_windsock_switches_vectors_at_thresholds(self):
        w1 = Wind(velocity=Velocity.FPS(10), direction_from=Angular.Degree(0), until_distance=Distance.Foot(50))
        w2 = Wind(velocity=Velocity.FPS(20), direction_from=Angular.Degree(90), until_distance=Distance.Foot(100))
        ws = _WindSock((w1, w2))
        v0 = ws.vector_for_range(0.0)
        assert v0.x > 0 and v0.z == pytest.approx(0.0)
        v49 = ws.vector_for_range(49.0)
        assert v49.x == pytest.approx(v0.x) and v49.z == pytest.approx(v0.z)
        v50 = ws.vector_for_range(50.0)
        # Now from left to right (+z), crosswind only
        assert v50.x == pytest.approx(0.0, abs=1e-12)
        assert v50.z > 0
