import pytest

from py_ballisticcalc_exts.traj_data import CythonizedBaseTrajData
from py_ballisticcalc_exts._test_helpers import make_base_traj_data


def test_base_traj_interpolate_time_linear_position():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(2.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.70)

    res = CythonizedBaseTrajData.interpolate("time", 1.5, p0, p1, p2)
    assert res.time == pytest.approx(1.5)
    assert res.position.x == pytest.approx(15.0)
    assert res.position.y == 0.0 and res.position.z == 0.0
    # bclibc 58c3172 (C8b): the point is on the cubic Hermite of the step (p1, p2) and its velocity is the derivative of the
    # position polynomial (here zero end slopes: 1.5 * 10 / 1 = 15), not an interpolation of the given velocities.
    assert res.velocity.x == pytest.approx(15.0) and res.velocity.y == 0.0 and res.velocity.z == 0.0
    assert res.mach > 0.60 and res.mach < 0.70


def test_base_traj_interpolate_on_position_sets_position():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 6.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(2.0, 20.0, 0.0, 0.0, 7.0, 0.0, 0.0, 0.70)

    res = CythonizedBaseTrajData.interpolate("position.x", 12.5, p0, p1, p2)
    assert res.position.x == pytest.approx(12.5)
    # time should be between 0.5 and 1.5 for monotone linear-like series
    assert 0.5 < res.time < 1.5


def test_base_traj_interpolate_duplicate_x_raises():
    p0 = make_base_traj_data(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.50)
    p1 = make_base_traj_data(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.60)
    p2 = make_base_traj_data(1.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.70)

    with pytest.raises(ZeroDivisionError):
        CythonizedBaseTrajData.interpolate("time", 0.75, p0, p1, p2)
