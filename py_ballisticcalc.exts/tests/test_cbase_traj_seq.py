import pytest

from py_ballisticcalc_exts.base_traj_seq import CBaseTrajSeq


def test_reserve_and_append_growth():
    seq = CBaseTrajSeq()
    seq.reserve(1)
    for i in range(8):
        seq.append(float(i), i, i, i, i, i, i, 0.5 + 0.01 * i)
    assert len(seq) == 8
    # Spot check first and last
    assert seq[0].time == pytest.approx(0.0)
    assert seq[-1].time == pytest.approx(7.0)


def test_interpolate_bounds_checks():
    seq = CBaseTrajSeq()
    # Need at least three points and middle index is required
    for i in range(3):
        seq.append(float(i), 10.0 * i, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6)

    # Valid case: idx=1 has neighbors on both sides
    mid = seq.interpolate_at(1, "time", 0.5)
    assert mid.time == pytest.approx(0.5)

    # Error cases: out-of-range or no neighbors
    with pytest.raises(IndexError):
        seq.interpolate_at(3, "time", 1.5)


def test_append_and_len_and_getitem():
    seq = CBaseTrajSeq()
    assert len(seq) == 0
    seq.append(0.0, 1.0, 2.0, 3.0, 10.0, 20.0, 30.0, 0.8)
    seq.append(1.0, 2.0, 3.0, 4.0, 11.0, 21.0, 31.0, 0.81)
    assert len(seq) == 2
    p0 = seq[0]
    p1 = seq[1]
    assert p0.time == pytest.approx(0.0)
    assert p1.time == pytest.approx(1.0)
    # position components (use Python-facing Vector properties)
    assert p0.position_vector.x == pytest.approx(1.0)
    assert p1.position_vector.y == pytest.approx(3.0)


def test_negative_index_and_c_getitem():
    seq = CBaseTrajSeq()
    seq.append(0.0, 0, 0, 0, 0, 0, 0, 0.0)
    seq.append(1.0, 1, 1, 1, 1, 1, 1, 1.0)
    # negative index from Python-level __getitem__
    last = seq[-1]
    assert last.time == pytest.approx(1.0)


def test_interpolate_at_time_and_position():
    seq = CBaseTrajSeq()
    # Create three points with time 0,1,2 and position.x linearly increasing
    seq.append(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5)
    seq.append(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6)
    seq.append(2.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7)

    # Interpolate at time=1.5 should give position.x ~ 15.0
    interpolated = seq.interpolate_at(1, 'time', 1.5)
    assert interpolated.time == pytest.approx(1.5)
    assert interpolated.position_vector.x == pytest.approx(15.0)
    # Interpolate at position.x == 15 -> should give time ~1.5
    interpolated2 = seq.interpolate_at(1, 'position.x', 15.0)
    assert interpolated2.time == pytest.approx(1.5)
    assert interpolated2.position_vector.x == pytest.approx(15.0)


def test_interpolate_at_accepts_negative_index_middle():
    seq = CBaseTrajSeq()
    # three points, so -2 should normalize to 1 (the middle)
    seq.append(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5)
    seq.append(1.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6)
    seq.append(2.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7)

    mid = seq.interpolate_at(-2, 'time', 1.5)
    assert mid.time == pytest.approx(1.5)
    assert mid.position_vector.x == pytest.approx(15.0)
