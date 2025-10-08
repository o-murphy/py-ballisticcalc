"""Interpolation utilities for ballistic calculations.

This module provides both piecewise cubic Hermite interpolation (PCHIP) and linear
interpolation methods. Linear interpolation (interpolate_2_pt) requires 2 points.
PCHIP (interpolate_3_pt) requires 3 points and produces smoother results that
preserve monotonicity and prevent overshoot using the Fritsch–Carlson slope limiting algorithm.
"""

from dataclasses import dataclass
from enum import Enum
from typing_extensions import List, Literal, Sequence

__all__ = [
    "InterpolationMethod",
    "InterpolationMethodEnum",
    "interpolate_3_pt",
    "interpolate_2_pt",
    # Optimized PCHIP (precompute-and-eval API)
    "PchipPrepared",
    "pchip_prepare",
    "pchip_eval",
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


def _pchip_slopes_three_points(x0: float, y0: float, x1: float, y1: float, x2: float, y2: float):
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


# ===== Optimized PCHIP: precompute coefficients for fast interpolation =====


@dataclass
class PchipPrepared:
    """Precomputed PCHIP spline coefficients for fast evaluation.

    Represents a cubic Hermite spline with Fritsch–Carlson slope limiting
    on an increasing knot sequence x[0..n-1]. For each interval i in [0..n-2],
    the segment on [x[i], x[i+1]] is expressed as:

        y(x) = a[i] + dx*(b[i] + dx*(c[i] + dx*d[i]))

    where dx = x - x[i].

    Attributes:
        x: Knot positions, strictly increasing (length n)
        a: Constant coefficients per segment (length n-1)
        b: Linear coefficients per segment (length n-1)
        c: Quadratic coefficients per segment (length n-1)
        d: Cubic coefficients per segment (length n-1)
    """

    x: List[float]
    a: List[float]
    b: List[float]
    c: List[float]
    d: List[float]


def _ensure_strictly_increasing(xs: Sequence[float]) -> None:
    for i in range(1, len(xs)):
        if xs[i] <= xs[i - 1]:
            raise ValueError("x values must be strictly increasing with no duplicates")


def pchip_prepare(xs: Sequence[float], ys: Sequence[float]) -> PchipPrepared:
    """Precompute PCHIP spline coefficients for fast evaluation.

    Uses Fritsch–Carlson slope limiting to ensure a monotone-preserving,
    C1-continuous interpolant. Coefficients are normalized to dx = x - x_i
    for efficient Horner evaluation without runtime divisions.

    Args:
        xs: Strictly increasing x values (length n >= 2)
        ys: Corresponding y values (length n)

    Returns:
        PchipPrepared object containing knots and per-segment coefficients.

    Raises:
        ValueError: If input sizes mismatch or xs not strictly increasing.
    """
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    n = len(xs)
    if n < 2:
        raise ValueError("At least two points are required for interpolation")
    _ensure_strictly_increasing(xs)

    # Compute h and finite differences delta
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    delta = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]

    # Slopes m at knots using Fritsch–Carlson method
    m = [0.0] * n
    if n == 2:
        # Linear segment: both slopes equal to delta
        m[0] = delta[0]
        m[1] = delta[0]
    else:
        # Interior nodes
        for i in range(1, n - 1):
            d0 = delta[i - 1]
            d1 = delta[i]
            if d0 == 0.0 or d1 == 0.0 or _sign(d0) != _sign(d1):
                m[i] = 0.0
            else:
                w1 = 2 * h[i] + h[i - 1]
                w2 = h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d0 + w2 / d1)

        # Endpoints (three-point formula + limiting)
        # Left endpoint
        d0 = delta[0]
        d1 = delta[1]
        m0 = ((2 * h[0] + h[1]) * d0 - h[0] * d1) / (h[0] + h[1])
        if _sign(m0) != _sign(d0):
            m0 = 0.0
        elif abs(m0) > 3 * abs(d0):
            m0 = 3 * d0
        m[0] = m0

        # Right endpoint
        dn_2 = delta[-1]
        dn_3 = delta[-2]
        mn = ((2 * h[-1] + h[-2]) * dn_2 - h[-1] * dn_3) / (h[-1] + h[-2])
        if _sign(mn) != _sign(dn_2):
            mn = 0.0
        elif abs(mn) > 3 * abs(dn_2):
            mn = 3 * dn_2
        m[-1] = mn

    # Convert Hermite form to unnormalized polynomial per segment: a + b*dx + c*dx^2 + d*dx^3
    a = [0.0] * (n - 1)
    b = [0.0] * (n - 1)
    c = [0.0] * (n - 1)
    d = [0.0] * (n - 1)
    for i in range(n - 1):
        y0 = ys[i]
        y1 = ys[i + 1]
        h_i = h[i]
        m0 = m[i]
        m1 = m[i + 1]
        a[i] = y0
        b[i] = m0
        # Derived from normalized Hermite basis expansion
        c[i] = (3 * (y1 - y0) - (2 * m0 + m1) * h_i) / (h_i * h_i)
        d[i] = (2 * (y0 - y1) + (m0 + m1) * h_i) / (h_i * h_i * h_i)

    return PchipPrepared(x=list(xs), a=a, b=b, c=c, d=d)


def pchip_eval(prep: PchipPrepared, x: float) -> float:
    """Evaluate a precomputed PCHIP spline at x.

    Uses binary search to locate the interval and Horner's rule to compute the cubic efficiently:
        `y = a + dx*(b + dx*(c + dx*d))`

    Args:
        prep: PCHIP spline coefficients
        x: Evaluation point

    Returns:
        Interpolated y-value at x.
    """
    xs = prep.x
    n = len(xs)
    if x <= xs[0]:
        i = 0
    elif x >= xs[-1]:
        i = n - 2
    else:
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        i = lo
    dx = x - xs[i]
    return prep.a[i] + dx * (prep.b[i] + dx * (prep.c[i] + dx * prep.d[i]))
