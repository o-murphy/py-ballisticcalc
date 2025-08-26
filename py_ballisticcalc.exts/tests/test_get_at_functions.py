import math
import pytest

from py_ballisticcalc_exts.base_traj_seq import CBaseTrajSeq


def make_linear_seq(n=5):
    seq = CBaseTrajSeq()
    for i in range(n):
        # time=i, px=10*i (linear), py=0, pz=0, velocities not used in tests, mach grows
        seq.append(float(i), 10.0 * i, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6 + 0.01 * i)
    return seq


def test_get_at_time_and_posx_basic():
    seq = make_linear_seq(3)  # times 0,1,2 and px 0,10,20
    # time key
    r1 = seq.get_at("time", 1.5)
    assert r1.time == pytest.approx(1.5)
    assert r1.position_vector.x == pytest.approx(15.0)
    # position.x key
    r2 = seq.get_at("position.x", 15.0)
    assert r2.time == pytest.approx(1.5)
    assert r2.position_vector.x == pytest.approx(15.0)


def test_get_at_with_start_from_time_behaves_like_hitresult():
    seq = make_linear_seq(5)  # times 0..4, px 0..40 step 10
    # Starting search around time >= 2 should still find x=15 at ~1.5 by scanning backward
    r = seq.get_at("position.x", 15.0, start_from_time=2.0)
    assert r.time == pytest.approx(1.5)
    assert r.position_vector.x == pytest.approx(15.0)


def test_get_at_slant_height_simple():
    seq = make_linear_seq(3)
    # choose look angle 90 deg => slant = -px
    look = math.pi / 2.0
    target_slant = -15.0  # implies px=15
    r = seq.get_at_slant_height(look, target_slant)
    assert r.position_vector.x == pytest.approx(15.0)
    assert r.time == pytest.approx(1.5)
