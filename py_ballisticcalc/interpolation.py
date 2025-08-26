"""Interpolation utilities for ballistic calculations.

This module provides both piecewise cubic Hermite interpolation (PCHIP) and linear
interpolation methods. Linear interpolation (interpolate_2_pt) requires 2 points.
PCHIP (interpolate_3_pt) requires 3 points and produces smoother results that
preserve monotonicity and prevent overshoot using the Fritsch–Carlson slope limiting algorithm.
"""
from enum import Enum
from typing_extensions import Literal

__all__ = [
    "InterpolationMethod",
    "InterpolationMethodEnum",
    "interpolate_3_pt",
    "interpolate_2_pt",
]

InterpolationMethod = Literal["pchip", "linear"]


class InterpolationMethodEnum(str, Enum):
    """Interpolation method options.

    Values map to accepted string identifiers so callers may pass either the
    enum variant or the string directly.

    - PCHIP: Monotone Piecewise Cubic Hermite interpolation (Fritsch–Carlson).
    - LINEAR: Piecewise linear interpolation between adjacent points.
    """

    PCHIP = "pchip"
    LINEAR = "linear"


def _sign(a: float) -> int:
    """Return the sign of a number.

    Args:
        a: Input value.

    Returns:
        1 if a > 0, -1 if a < 0, 0 if a == 0.
    """

    return 1 if a > 0 else (-1 if a < 0 else 0)


def _pchip_slopes_three_points(
    x0: float, y0: float, x1: float, y1: float, x2: float, y2: float
):
    """Compute PCHIP endpoint and interior slopes for three points.

    Uses Fritsch–Carlson slope limiting to preserve monotonicity and prevent
    overshoot. The three points can be provided in any x-order.

    Args:
        x0: First x value.
        y0: First y value.
        x1: Second x value.
        y1: Second y value.
        x2: Third x value.
        y2: Third y value.

    Returns:
        Tuple of slopes (m0, m1, m2) at x0, x1, and x2 respectively.

    Raises:
        ZeroDivisionError: If any adjacent x-values are identical.
    """

    # Ensure ascending order for stable slope calculations
    pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[0])
    (x0, y0), (x1, y1), (x2, y2) = pts

    h0 = x1 - x0
    h1 = x2 - x1
    if h0 == 0 or h1 == 0:
        raise ZeroDivisionError("Duplicate x-values in interpolation points")
    d0 = (y1 - y0) / h0
    d1 = (y2 - y1) / h1

    if d0 == 0 or d1 == 0 or _sign(d0) != _sign(d1):
        m1 = 0.0
    else:
        w1 = 2 * h1 + h0
        w2 = h1 + 2 * h0
        m1 = (w1 + w2) / (w1 / d0 + w2 / d1)

    m0 = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
    if _sign(m0) != _sign(d0):
        m0 = 0.0
    elif abs(m0) > 3 * abs(d0):
        m0 = 3 * d0

    m2 = ((2 * h1 + h0) * d1 - h1 * d0) / (h0 + h1)
    if _sign(m2) != _sign(d1):
        m2 = 0.0
    elif abs(m2) > 3 * abs(d1):
        m2 = 3 * d1

    return m0, m1, m2


def _hermite_eval(
    x: float,
    xk: float,
    xk1: float,
    yk: float,
    yk1: float,
    mk: float,
    mk1: float,
) -> float:
    """Evaluate the cubic Hermite polynomial on [xk, xk1].

    Args:
        x: Evaluation point.
        xk: Left x-bound of the segment.
        xk1: Right x-bound of the segment.
        yk: Function value at xk.
        yk1: Function value at xk1.
        mk: Derivative at xk.
        mk1: Derivative at xk1.

    Returns:
        Interpolated y-value at x.

    Raises:
        ZeroDivisionError: If xk and xk1 are identical.
    """

    h = xk1 - xk
    if h == 0:
        raise ZeroDivisionError("Zero interval width in Hermite evaluation")
    t = (x - xk) / h
    t2 = t * t
    t3 = t2 * t
    h00 = 2 * t3 - 3 * t2 + 1
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2
    return h00 * yk + h * h10 * mk + h01 * yk1 + h * h11 * mk1


def interpolate_3_pt(
    x: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """Monotone PCHIP interpolation using three points.

    This computes Fritsch–Carlson limited slopes at each point, and evaluates a
    cubic Hermite on the segment bracketing x. Input points may be unsorted.

    Args:
        x: Evaluation point.
        x0, y0: First data point.
        x1, y1: Second data point.
        x2, y2: Third data point.

    Returns:
        Interpolated y-value at x.

    Raises:
        ZeroDivisionError: If any adjacent x-values are identical.
    """

    pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[0])
    (x0, y0), (x1, y1), (x2, y2) = pts
    m0, m1, m2 = _pchip_slopes_three_points(x0, y0, x1, y1, x2, y2)
    if x <= x1:
        return _hermite_eval(x, x0, x1, y0, y1, m0, m1)
    else:
        return _hermite_eval(x, x1, x2, y1, y2, m1, m2)


def interpolate_2_pt(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    """Linear interpolation between two points.

    Args:
        x: Evaluation point.
        x0, y0: First data point.
        x1, y1: Second data point.

    Returns:
        Interpolated y-value at x.

    Raises:
        ZeroDivisionError: If x0 == x1.
    """

    if x1 == x0:
        raise ZeroDivisionError("Duplicate x-values in linear interpolation")
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)
