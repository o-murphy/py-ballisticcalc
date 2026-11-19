"""The error kinds of the C ABI (bclibc 2.2) are the exceptions the C++ layer raises."""

import pytest

from py_ballisticcalc_cabi import CythonizedBaseTrajSeq


def seq(n):
    s = CythonizedBaseTrajSeq()
    for i in range(n):
        s.append(i * 0.1, i * 10.0, i * 0.5, 0.0, 800.0 - i, 0.0, 0.0, 2.0 - i * 0.01)
    return s


def test_index_outside_the_buffer_is_index_error():
    with pytest.raises(IndexError):
        seq(5).interpolate_at(0, "time", 0.2)


def test_get_at_outside_the_trajectory_is_index_error():
    with pytest.raises(IndexError):
        seq(5).get_at("time", 99.0)


def test_degenerate_segment_is_value_error():
    s = CythonizedBaseTrajSeq()
    for _ in range(3):
        s.append(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        s.interpolate_at(1, "time", 0.0)
