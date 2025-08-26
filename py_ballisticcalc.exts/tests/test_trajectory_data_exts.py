import math
import pytest

from py_ballisticcalc_exts.trajectory_data import BaseTrajDataT, make_base_traj_data


def test_base_traj_interpolate_time_linear_position():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(2.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.70)

    res = BaseTrajDataT.interpolate('time', 1.5, p0, p1, p2)
    assert res.time == pytest.approx(1.5)
    assert res.position.x == pytest.approx(15.0)
    assert res.position.y == 0.0 and res.position.z == 0.0
    assert res.velocity.x == 0.0 and res.velocity.y == 0.0 and res.velocity.z == 0.0
    assert res.mach > 0.60 and res.mach < 0.70


def test_base_traj_interpolate_on_position_sets_position():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 6.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(2.0, 20.0, 0.0, 0.0, 7.0, 0.0, 0.0, 0.70)

    res = BaseTrajDataT.interpolate('position.x', 12.5, p0, p1, p2)
    assert res.position.x == pytest.approx(12.5)
    # time should be between 0.5 and 1.5 for monotone linear-like series
    assert 0.5 < res.time < 1.5


def test_base_traj_interpolate_duplicate_x_raises():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(1.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.70)

    with pytest.raises(ZeroDivisionError):
        BaseTrajDataT.interpolate('time', 0.75, p0, p1, p2)
