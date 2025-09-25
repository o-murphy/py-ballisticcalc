import types

import pytest

from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Velocity, Energy, Weight

pytestmark = pytest.mark.extended

def _td(distance_ft: float = 0.0) -> TrajectoryData:
    """Create a minimal TrajectoryData row for exception tests."""
    return TrajectoryData(
        time=0.0,
        distance=Distance.Foot(distance_ft),
        velocity=Velocity.FPS(1000),
        mach=1.0,
        height=Distance.Foot(0.0),
        slant_height=Distance.Foot(0.0),
        drop_angle=Angular.Degree(0.0),
        windage=Distance.Foot(0.0),
        windage_angle=Angular.Degree(0.0),
        slant_distance=Distance.Foot(distance_ft),
        angle=Angular.Degree(0.0),
        density_ratio=1.0,
        drag=0.0,
        energy=Energy.FootPound(0.0),
        ogw=Weight.Pound(1.0),
        flag=TrajFlag.NONE,
    )


def test_zero_finding_error_message_and_attrs():
    zfe = ZeroFindingError(0.5, 7, Angular.Degree(1.2))
    assert "after 7 iterations" in str(zfe)
    assert zfe.iterations_count == 7
    assert zfe.zero_finding_error == 0.5

    zfe2 = ZeroFindingError(0.1, 2, Angular.Degree(0.1), reason=ZeroFindingError.ERROR_NON_CONVERGENT)
    assert ZeroFindingError.ERROR_NON_CONVERGENT in str(zfe2)


def test_range_error_last_distance_set_and_none():
    err_empty = RangeError(RangeError.MinimumVelocityReached, [])
    assert err_empty.last_distance is None
    assert RangeError.MinimumVelocityReached in str(err_empty)

    row = _td(distance_ft=123.0)
    err_with = RangeError(RangeError.MaximumDropReached, [row])
    assert err_with.last_distance is not None
    assert float(err_with.last_distance._feet) == pytest.approx(123.0)
    assert RangeError.MaximumDropReached in str(err_with)


def test_out_of_range_error_message_variants():
    d_req = Distance.Foot(500)
    e1 = OutOfRangeError(d_req)
    assert str(d_req._feet) in str(e1)

    maxr = Distance.Foot(1200)
    look = Angular.Degree(5)
    e2 = OutOfRangeError(d_req, max_range=maxr, look_angle=look, note="try smaller distance")
    s = str(e2)
    assert str(maxr._feet) in s and "rad" in s and "try smaller distance" in s
