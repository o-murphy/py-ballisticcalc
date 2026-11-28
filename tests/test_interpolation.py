import itertools
import math

import pytest

from py_ballisticcalc.interpolation import interpolate_2_pt, interpolate_3_pt
from py_ballisticcalc.trajectory_data import BaseTrajData, TrajectoryData
from py_ballisticcalc.unit import Angular, Distance, Energy, Velocity, Weight
from py_ballisticcalc.vector import Vector


class TestInterpolationBasic:

    @staticmethod
    def make_base(t: float, pos: float, vel: float, mach: float) -> BaseTrajData:
        return BaseTrajData(time=t, position=Vector(pos, 0.0, 0.0), velocity=Vector(vel, 0.0, 0.0), mach=mach)

    def test_pchip_monotone_preserves_shape_scalar(self):
        x0, x1, x2 = 0.0, 1.0, 2.0
        y0, y1, y2 = 0.0, 1.0, 1.5
        xs = [0.25, 0.75, 1.25, 1.75]
        last = None
        for x in xs:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            if last is not None:
                assert y >= last - 1e-12
            last = y

    def test_linear_scalar_agrees_with_exact_line(self):
        x0, x1 = 10.0, 20.0
        y0, y1 = 30.0, 50.0
        for x in [10.0, 12.5, 15.0, 17.5, 20.0]:
            y = interpolate_2_pt(x, x0, y0, x1, y1)
            assert math.isclose(y, y0 + (y1 - y0) * (x - x0) / (x1 - x0), rel_tol=0, abs_tol=1e-12)

    def test_basetrajdata_interpolate_method_switch(self):
        # Consistent steps (position change = mean velocity * dt), query inside the first step.
        p0 = self.make_base(0.0, 0.0, 3000.0, 2.5)
        p1 = self.make_base(1.0, 2900.0, 2800.0, 2.3)
        p2 = self.make_base(2.0, 5700.0, 2600.0, 2.1)
        res_pchip = BaseTrajData.interpolate('time', 0.5, p0, p1, p2, method='pchip')
        res_linear = BaseTrajData.interpolate('time', 0.5, p0, p1, p2, method='linear')
        # A step brackets the query, so it is answered on the cubic Hermite of the step: `method` only selects the
        # 3-point fallback and has no effect here (the old 3-point result differed between the methods).
        assert res_pchip == res_linear
        # closed-form Hermite at u = 0.5: x = (y0 + y1) / 2 + dt * (m0 - m1) / 8
        assert res_pchip.position.x == pytest.approx((0.0 + 2900.0) / 2 + (3000.0 - 2800.0) / 8, abs=1e-9)
        assert p0.position.x <= res_pchip.position.x <= p1.position.x

    def test_basetrajdata_interpolate_dimension_switch_on_position(self):
        # Use position.x as key
        p0 = self.make_base(0.0, 0.0, 3000.0, 2.5)
        p1 = self.make_base(1.0, 100.0, 2800.0, 2.3)
        p2 = self.make_base(2.0, 200.0, 2600.0, 2.1)
        res_lin = BaseTrajData.interpolate('position.x', 50.0, p0, p1, p2, method='linear')
        res_pc = BaseTrajData.interpolate('position.x', 50.0, p0, p1, p2, method='pchip')
        # Ensure times are between neighbor times when keying on position.x
        assert p0.time <= res_lin.time <= p1.time
        assert p0.time <= res_pc.time <= p1.time

    def test_basetraj_linear_fallback_chooses_correct_segment(self):
        # Non-uniform key spacing. No step brackets a query outside [0, 2], so the 3-point fallback is used, and
        # method='linear' extrapolates the nearest segment of the sorted points.
        p0 = self.make_base(0.0, 0.0, 0.0, 0.2)
        p1 = self.make_base(0.1, 1.0, 0.0, 0.3)
        p2 = self.make_base(2.0, 2.0, 0.0, 0.4)
        right = BaseTrajData.interpolate('time', 2.5, p0, p1, p2, method="linear")
        assert abs(right.position.x - interpolate_2_pt(2.5, 0.1, p1.position.x, 2.0, p2.position.x)) < 1e-12
        left = BaseTrajData.interpolate('time', -0.5, p0, p1, p2, method="linear")
        assert abs(left.position.x - interpolate_2_pt(-0.5, 0.0, p0.position.x, 0.1, p1.position.x)) < 1e-12
        assert right.time == 2.5 and left.time == -0.5  # the key field is the query

    def test_basetraj_pchip_fallback_when_no_step_brackets(self):
        p0 = self.make_base(0.0, 0.0, 3000.0, 2.5)
        p1 = self.make_base(1.0, 2900.0, 2800.0, 2.3)
        p2 = self.make_base(2.0, 5700.0, 2600.0, 2.1)
        r = BaseTrajData.interpolate('time', 2.5, p0, p1, p2)
        assert r.time == 2.5
        assert r.position.x == interpolate_3_pt(2.5, 0.0, 0.0, 1.0, 2900.0, 2.0, 5700.0)
        assert r.velocity.x == interpolate_3_pt(2.5, 0.0, 3000.0, 1.0, 2800.0, 2.0, 2600.0)
        assert r.mach == interpolate_3_pt(2.5, 0.0, 2.5, 1.0, 2.3, 2.0, 2.1)

    def test_basetraj_backward_step_falls_back_to_pchip(self):
        # Time decreasing: no step runs forward, so there is no Hermite step; the 3-point PCHIP answers.
        p0 = self.make_base(2.0, 20.0, 7.0, 0.7)
        p1 = self.make_base(1.0, 10.0, 6.0, 0.6)
        p2 = self.make_base(0.0, 0.0, 5.0, 0.5)
        r = BaseTrajData.interpolate('time', 1.5, p0, p1, p2)
        assert r.position.x == interpolate_3_pt(1.5, 2.0, 20.0, 1.0, 10.0, 0.0, 0.0)
        assert r.velocity.x == interpolate_3_pt(1.5, 2.0, 7.0, 1.0, 6.0, 0.0, 5.0)

    def test_basetraj_invalid_method_and_duplicate_keys(self):
        p0 = self.make_base(0.0, 0.0, 0.0, 0.5)
        p1 = self.make_base(1.0, 10.0, 0.0, 0.6)
        p2 = self.make_base(2.0, 20.0, 0.0, 0.7)
        with pytest.raises(ValueError):
            BaseTrajData.interpolate('time', 0.5, p0, p1, p2, method="spline")  # type: ignore[arg-type]
        with pytest.raises(ZeroDivisionError):
            BaseTrajData.interpolate('time', 0.5, p0, p1, self.make_base(1.0, 20.0, 0.0, 0.7))


def _hermite(t0, t1, y0, y1, m0, m1, t):
    """Independent closed form of the cubic Hermite of a step: (value, derivative) at time t."""
    h = t1 - t0
    u = (t - t0) / h
    value = (
        y0 * (1 + 2 * u) * (1 - u) ** 2 + h * m0 * u * (1 - u) ** 2 + y1 * u * u * (3 - 2 * u) - h * m1 * u * u * (1 - u)
    )
    # d/dt of the above, written from the derivative basis (6u(u-1), 1-4u+3u^2, 6u(1-u), 3u^2-2u) / h and h
    deriv = (y0 * 6 * u * (u - 1) + y1 * 6 * u * (1 - u)) / h + m0 * (1 - 4 * u + 3 * u * u) + m1 * (3 * u * u - 2 * u)
    return value, deriv


class TestBaseTrajDataHermiteConvention:
    """BaseTrajData.interpolate locates the point on the cubic Hermite of the integration step (the convention of
    the engines and of the cythonized core): velocity = derivative of the position polynomial, Mach linear."""

    @staticmethod
    def pt(t, x, vx, mach, y=0.0, vy=0.0):
        return BaseTrajData(time=t, position=Vector(x, y, 0.0), velocity=Vector(vx, vy, 0.0), mach=mach)

    def test_zero_given_velocities_velocity_is_derivative_of_position(self):
        p0, p1, p2 = self.pt(0.0, 0.0, 0.0, 0.50), self.pt(1.0, 10.0, 0.0, 0.60), self.pt(2.0, 20.0, 0.0, 0.70)
        r = BaseTrajData.interpolate('time', 1.5, p0, p1, p2)
        assert r.time == 1.5
        assert r.position.x == pytest.approx(15.0, abs=1e-12)  # smoothstep at u = 0.5
        assert r.velocity.x == pytest.approx(15.0, abs=1e-12)  # 10 * 6 u (1 - u); the old 3-point result was 0.0
        assert r.mach == pytest.approx(0.65, abs=1e-15)

    @pytest.mark.parametrize("t, step", [(0.25, 0), (0.37, 0), (1.5, 1), (1.61, 1), (1.0, 0)])
    def test_time_key_equals_closed_form_hermite(self, t, step):
        p0, p1, p2 = self.pt(0.0, 0.0, 5.0, 0.50), self.pt(1.0, 10.0, 6.0, 0.60), self.pt(2.0, 20.0, 7.0, 0.70)
        a, b = ((p0, p1), (p1, p2))[step]
        r = BaseTrajData.interpolate('time', t, p0, p1, p2)
        x, vx = _hermite(a.time, b.time, a.position.x, b.position.x, a.velocity.x, b.velocity.x, t)
        assert r.time == t
        assert r.position.x == pytest.approx(x, abs=1e-12)
        assert r.velocity.x == pytest.approx(vx, abs=1e-12)
        assert r.mach == pytest.approx(a.mach + (t - a.time) / (b.time - a.time) * (b.mach - a.mach), abs=1e-15)

    @pytest.mark.parametrize("key, target, step", [("position.x", 7.3, 0), ("position.x", 16.1, 1), ("velocity.x", 5.37, 0), ("velocity.x", 6.5, 1)])
    def test_other_keys_are_located_on_the_step_polynomial(self, key, target, step):
        p0, p1, p2 = self.pt(0.0, 0.0, 5.0, 0.50), self.pt(1.0, 10.0, 6.0, 0.60), self.pt(2.0, 20.0, 7.0, 0.70)
        a, b = ((p0, p1), (p1, p2))[step]
        r = BaseTrajData.interpolate(key, target, p0, p1, p2)
        assert a.time <= r.time <= b.time
        x, vx = _hermite(a.time, b.time, a.position.x, b.position.x, a.velocity.x, b.velocity.x, r.time)
        assert r.position.x == pytest.approx(x, abs=1e-12)
        assert r.velocity.x == pytest.approx(vx, abs=1e-12)
        assert (r.position.x if key == "position.x" else r.velocity.x) == target
        # and the point is really where the polynomial crosses the target
        assert (x if key == "position.x" else vx) == pytest.approx(target, abs=1e-9)

    def test_mach_key(self):
        p0, p1, p2 = self.pt(0.0, 0.0, 5.0, 0.50), self.pt(1.0, 10.0, 6.0, 0.60), self.pt(2.0, 20.0, 7.0, 0.70)
        r = BaseTrajData.interpolate('mach', 0.65, p0, p1, p2)
        assert r.mach == 0.65 and r.time == pytest.approx(1.5, abs=1e-12)

    def test_value_on_the_shared_point_is_that_point(self):
        p0, p1, p2 = self.pt(0.0, 0.0, 5.0, 0.50), self.pt(1.0, 10.0, 6.0, 0.60), self.pt(2.0, 20.0, 7.0, 0.70)
        r = BaseTrajData.interpolate('time', 1.0, p0, p1, p2)
        assert r.position.x == pytest.approx(10.0, abs=1e-12) and r.velocity.x == pytest.approx(6.0, abs=1e-12)


class TestInterpolationEdge:

    def test_pchip_no_overshoot_near_peak_and_valley(self):
        # Local peak around x=1: increasing then decreasing
        x0, x1, x2 = 0.0, 1.0, 2.0
        y0, y1, y2 = 0.0, 2.0, 1.0
        for x in [0.25, 0.75]:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            assert y >= y0 - 1e-12 and y <= y1 + 1e-12
        for x in [1.25, 1.75]:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            assert y <= y1 + 1e-12 and y >= min(y1, y2) - 1e-12

        # Local valley: decreasing then increasing
        y0, y1, y2 = 2.0, 1.0, 2.0
        for x in [0.25, 0.75, 1.25, 1.75]:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            assert y >= min(y0, y1, y2) - 1e-12 and y <= max(y0, y1, y2) + 1e-12

    def test_pchip_monotone_decreasing_segment(self):
        x0, x1, x2 = 0.0, 1.0, 2.0
        y0, y1, y2 = 3.0, 2.0, 1.0
        last = None
        for x in [0.25, 0.75, 1.25, 1.75]:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            if last is not None:
                assert y <= last + 1e-12
            last = y

    def test_pchip_uneven_spacing_monotonicity(self):
        # Uneven spacing: x0=0, x1=0.1, x2=2.0 with increasing y
        x0, x1, x2 = 0.0, 0.1, 2.0
        y0, y1, y2 = 0.0, 1.0, 1.5
        # Sample across both segments
        xs = [0.0, 0.02, 0.05, 0.08, 0.1, 0.5, 1.0, 1.5, 2.0]
        last = None
        for x in xs:
            y = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            if last is not None and x > 0.0:  # skip first
                assert y >= last - 1e-12
            last = y

    def test_permutation_invariance_three_points(self):
        # Same three data points should yield identical results regardless of input order
        pts = [(0.0, 0.0), (1.0, 1.0), (2.0, 1.5)]
        xs = [0.25, 0.75, 1.25, 1.75]
        # Canonical order result
        x0, y0 = pts[0]
        x1, y1 = pts[1]
        x2, y2 = pts[2]
        ref = {x: interpolate_3_pt(x, x0, y0, x1, y1, x2, y2) for x in xs}

        for perm in itertools.permutations(pts):
            (xa, ya), (xb, yb), (xc, yc) = perm
            for x in xs:
                y = interpolate_3_pt(x, xa, ya, xb, yb, xc, yc)
                assert abs(y - ref[x]) < 1e-12

    def test_duplicate_x_raises(self):
        # Linear duplicate x0==x1
        try:
            interpolate_2_pt(0.5, 1.0, 1.0, 1.0, 2.0)
            assert False, "Expected ZeroDivisionError for duplicate x in linear"
        except ZeroDivisionError:
            pass

        # PCHIP duplicate adjacent x should raise
        try:
            interpolate_3_pt(0.5, 1.0, 1.0, 1.0, 2.0, 2.0, 3.0)
            assert False, "Expected ZeroDivisionError for duplicate adjacent x in PCHIP"
        except ZeroDivisionError:
            pass

    def test_endpoint_behavior_exact_matches(self):
        x0, x1, x2 = 0.0, 1.0, 2.0
        y0, y1, y2 = 0.0, 1.0, 2.0
        for x, y_true in [(0.0, y0), (1.0, y1), (2.0, y2)]:
            y_p = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            # Linear endpoints also exact
            y_l = interpolate_2_pt(x, x0, y0, x1, y1) if x <= x1 else interpolate_2_pt(x, x1, y1, x2, y2)
            assert abs(y_p - y_true) < 1e-12
            assert abs(y_l - y_true) < 1e-12

    def test_pchip_equals_linear_on_colinear_points(self):
        # Three points on y = 3x - 2
        x0, x1, x2 = -1.0, 0.0, 2.0
        y0, y1, y2 = -5.0, -2.0, 4.0
        for x in [-1.0, -0.5, 0.0, 1.0, 2.0]:
            y_p = interpolate_3_pt(x, x0, y0, x1, y1, x2, y2)
            # Linear reference on the correct segment
            y_ref = interpolate_2_pt(x, x0, y0, x1, y1) if x <= x1 else interpolate_2_pt(x, x1, y1, x2, y2)
            assert abs(y_p - y_ref) < 1e-12


class TestTrajectoryDataInterpolation:
    
    @staticmethod
    def TD(**overrides) -> TrajectoryData:
        # Default builder for TrajectoryData with sensible baseline values.
        base = dict(
            time=0.0,
            distance=Distance.Foot(0.0),
            velocity=Velocity.FPS(1000.0),
            mach=0.3,
            height=Distance.Foot(0.0),
            slant_height=Distance.Foot(0.0),
            drop_angle=Angular.Radian(0.0),
            windage=Distance.Foot(0.0),
            windage_angle=Angular.Radian(0.0),
            slant_distance=Distance.Foot(0.0),
            angle=Angular.Radian(0.0),
            density_ratio=1.0,
            drag=0.0,
            energy=Energy.FootPound(0.0),
            ogw=Weight.Pound(0.0),
            flag=0,
        )
        base.update(overrides)
        return TrajectoryData(**base)  # type: ignore[arg-type]

    @staticmethod
    def chord(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    @staticmethod
    def assert_between(value: float, a: float, b: float, eps: float = 1e-12) -> None:
        lo, hi = (a, b) if a <= b else (b, a)
        assert lo - eps <= value <= hi + eps

    @staticmethod
    def assert_units_match(result: TrajectoryData, proto: TrajectoryData, fields):
        for f in fields:
            assert getattr(result, f).units == getattr(proto, f).units


    def test_trajdata_interpolate_dimensioned_fields_linear_vs_pchip(self):
        # Create three rows with monotone increasing distance/height and varying velocity
        p0 = TD()
        p1 = TD(
            time=1.0,
            distance=Distance.Foot(100.0),
            velocity=Velocity.FPS(900.0),
            mach=0.4,
            height=Distance.Foot(10.0),
            slant_height=Distance.Foot(10.0),
            drop_angle=Angular.Radian(0.01),
            slant_distance=Distance.Foot(100.0),
            density_ratio=0.99,
            drag=0.1,
        )
        p2 = TD(
            time=2.0,
            distance=Distance.Foot(250.0),
            velocity=Velocity.FPS(800.0),
            mach=0.5,
            height=Distance.Foot(25.0),
            slant_height=Distance.Foot(25.0),
            drop_angle=Angular.Radian(0.02),
            slant_distance=Distance.Foot(250.0),
            density_ratio=0.98,
            drag=0.2,
        )

        # Interpolate by time at t=1.5
        t = 1.5
        r_lin = TrajectoryData.interpolate('time', t, p0, p1, p2, method='linear')
        r_p = TrajectoryData.interpolate('time', t, p0, p1, p2, method='pchip')

        # Distance and height are dimensioned; verify linear raw math and PCHIP stay within envelope
        d1, d2 = p1.distance.raw_value, p2.distance.raw_value
        h1, h2 = p1.height.raw_value, p2.height.raw_value
        # Linear should equal two-point segment calculation (between p1 and p2)
        assert abs(r_lin.distance.raw_value - chord(t, 1.0, d1, 2.0, d2)) < 1e-12
        assert abs(r_lin.height.raw_value - chord(t, 1.0, h1, 2.0, h2)) < 1e-12

        # PCHIP should remain within local bounds
        assert_between(r_p.distance.raw_value, d1, d2)
        assert_between(r_p.height.raw_value, h1, h2)

        # Interpolating key attributes should set them exactly
        assert r_lin.time == t and r_p.time == t


    def test_trajdata_key_on_dimensioned_field(self):
        # Interpolate keyed by slant_height using raw float (Feet), ensure exact match and sensible interpolation
        p0 = TD()
        p1 = TD(
            time=1.0,
            distance=Distance.Foot(100.0),
            velocity=Velocity.FPS(900.0),
            mach=0.4,
            height=Distance.Foot(10.0),
            slant_height=Distance.Foot(10.0),
            drop_angle=Angular.Radian(0.01),
            slant_distance=Distance.Foot(100.0),
            density_ratio=0.99,
            drag=0.1,
        )
        p2 = TD(
            time=2.0,
            distance=Distance.Foot(250.0),
            velocity=Velocity.FPS(800.0),
            mach=0.5,
            height=Distance.Foot(25.0),
            slant_height=Distance.Foot(25.0),
            drop_angle=Angular.Radian(0.02),
            slant_distance=Distance.Foot(250.0),
            density_ratio=0.98,
            drag=0.2,
        )

        s = Distance.Foot(20.0)
        r_lin = TrajectoryData.interpolate('slant_height', s, p0, p1, p2, method='linear')
        r_p = TrajectoryData.interpolate('slant_height', s, p0, p1, p2, method='pchip')

        assert abs(r_lin.slant_height.raw_value - s.raw_value) < 1e-9
        assert abs(r_p.slant_height.raw_value - s.raw_value) < 1e-9

        # Spot-check velocity is between neighbors on PCHIP and matches linear chord on linear
        v1, v2 = p1.velocity.raw_value, p2.velocity.raw_value
        assert_between(r_p.velocity.raw_value, v1, v2)
        t1, t2 = p1.slant_height.raw_value, p2.slant_height.raw_value
        v_lin = chord(s.raw_value, t1, v1, t2, v2)
        assert abs(r_lin.velocity.raw_value - v_lin) < 1e-12


    def test_trajdata_mixed_units_key_and_fields(self):
        # Mix units across points: distances/heights in different units; velocity in different units too
        p0 = TD(
            velocity=Velocity.MPH(681.818),  # ~1000 fps
            height=Distance.Meter(0.0),
            slant_height=Distance.Meter(0.0),
            drop_angle=Angular.Degree(0.0),
            windage=Distance.Centimeter(0.0),
            windage_angle=Angular.MOA(0.0),
            angle=Angular.Mil(0.0),
        )
        p1 = TD(
            time=1.0,
            distance=Distance.Yard(100.0/3),  # 100 ft
            velocity=Velocity.MPS(274.32),     # ~900 fps
            mach=0.4,
            height=Distance.Centimeter(304.8),  # 10 ft
            slant_height=Distance.Centimeter(304.8),
            drop_angle=Angular.MRad(0.01),
            windage=Distance.Inch(0.0),
            windage_angle=Angular.Thousandth(0.0),
            slant_distance=Distance.Meter(30.48),
            angle=Angular.Radian(0.0),
            density_ratio=0.99,
            drag=0.1,
        )
        p2 = TD(
            time=2.0,
            distance=Distance.Meter(76.2),  # 250 ft
            velocity=Velocity.KMH(877.822),  # ~800 fps
            mach=0.5,
            height=Distance.Yard(25.0/3),  # 25 ft
            slant_height=Distance.Yard(25.0/3),
            drop_angle=Angular.Mil(0.02),
            windage=Distance.Foot(0.0),
            windage_angle=Angular.Radian(0.0),
            slant_distance=Distance.Meter(76.2),
            angle=Angular.Degree(0.0),
            density_ratio=0.98,
            drag=0.2,
        )

        key = Distance.Meter(5.0)
        r_lin = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='linear')
        r_p = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='pchip')

        assert abs(r_lin.slant_height.raw_value - key.raw_value) < 1e-9
        assert abs(r_p.slant_height.raw_value - key.raw_value) < 1e-9

        # Distance/height are monotone over p1->p2; PCHIP within bounds and linear on chord
        t1, t2 = p1.slant_height.raw_value, p2.slant_height.raw_value
        d1, d2 = p1.distance.raw_value, p2.distance.raw_value
        h1, h2 = p1.height.raw_value, p2.height.raw_value
        w = (key.raw_value - t1) / (t2 - t1)
        d_lin = d1 + (d2 - d1) * w
        h_lin = h1 + (h2 - h1) * w
        assert abs(r_lin.distance.raw_value - d_lin) < 1e-9
        assert abs(r_lin.height.raw_value - h_lin) < 1e-9
        assert_between(r_p.distance.raw_value, d1, d2)
        assert_between(r_p.height.raw_value, h1, h2)

        # Return units for dimensioned fields should follow p0's units
        assert r_lin.distance.units == p0.distance.units
        assert r_p.distance.units == p0.distance.units
        assert r_lin.height.units == p0.height.units
        assert r_p.height.units == p0.height.units
        assert r_lin.velocity.units == p0.velocity.units
        assert r_p.velocity.units == p0.velocity.units


    def test_trajdata_duplicate_key_raises_in_linear_and_pchip(self):
        # Duplicate slant_height values should cause ZeroDivisionError when selecting segment or slopes
        p0 = TD(slant_height=Distance.Foot(10.0))
        p1 = TD(
            time=1.0,
            distance=Distance.Foot(100.0),
            velocity=Velocity.FPS(900.0),
            mach=0.4,
            height=Distance.Foot(10.0),
            slant_height=Distance.Foot(10.0),
            drop_angle=Angular.Radian(0.01),
            slant_distance=Distance.Foot(100.0),
            density_ratio=0.99,
            drag=0.1,
        )
        p2 = TD(
            time=2.0,
            distance=Distance.Foot(200.0),
            velocity=Velocity.FPS(800.0),
            mach=0.5,
            height=Distance.Foot(20.0),
            slant_height=Distance.Foot(10.0),
            drop_angle=Angular.Radian(0.02),
            slant_distance=Distance.Foot(200.0),
            density_ratio=0.98,
            drag=0.2,
        )

        key = Distance.Foot(10.0)
        with pytest.raises(ZeroDivisionError):
            _ = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='linear')
        with pytest.raises(ZeroDivisionError):
            _ = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='pchip')


    def test_trajdata_endpoint_exact_match_on_dimensioned_key(self):
        p0 = TD()
        p1 = TD(time=1.0, distance=Distance.Foot(100.0), velocity=Velocity.FPS(900.0),
                height=Distance.Foot(10.0), slant_height=Distance.Foot(10.0))
        p2 = TD(time=2.0, distance=Distance.Foot(250.0), velocity=Velocity.FPS(800.0),
                height=Distance.Foot(25.0), slant_height=Distance.Foot(25.0))

        for method in ('linear', 'pchip'):
            r = TrajectoryData.interpolate('slant_height', Distance.Foot(10.0), p0, p1, p2, method=method)
            assert r.slant_height.raw_value == p1.slant_height.raw_value
            assert r.distance.raw_value == p1.distance.raw_value
            assert r.height.raw_value == p1.height.raw_value
            assert r.velocity.raw_value == p1.velocity.raw_value

        for method in ('linear', 'pchip'):
            r = TrajectoryData.interpolate('slant_height', Distance.Foot(25.0), p0, p1, p2, method=method)
            assert r.slant_height.raw_value == p2.slant_height.raw_value
            assert r.distance.raw_value == p2.distance.raw_value
            assert r.height.raw_value == p2.height.raw_value
            assert r.velocity.raw_value == p2.velocity.raw_value


    def test_trajdata_mixed_units_key_per_point(self):
        # slant_height units differ per point; key in yet another unit
        p0 = TD()
        p1 = p0._replace(time=1.0, distance=Distance.Foot(100.0), height=Distance.Foot(10.0),
                         slant_height=Distance.Centimeter(304.8))  # 10 ft
        p2 = p0._replace(time=2.0, distance=Distance.Foot(250.0), height=Distance.Foot(25.0),
                         slant_height=Distance.Meter(7.62))  # 25 ft

        key = Distance.Yard(5.0)  # 15 ft
        r_lin = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='linear')
        r_p = TrajectoryData.interpolate('slant_height', key, p0, p1, p2, method='pchip')

        assert abs(r_lin.slant_height.raw_value - key.raw_value) < 1e-9
        assert abs(r_p.slant_height.raw_value - key.raw_value) < 1e-9

        t1, t2 = p1.slant_height.raw_value, p2.slant_height.raw_value
        d1, d2 = p1.distance.raw_value, p2.distance.raw_value
        h1, h2 = p1.height.raw_value, p2.height.raw_value
        w = (key.raw_value - t1) / (t2 - t1)
        d_lin = d1 + (d2 - d1) * w
        h_lin = h1 + (h2 - h1) * w
        assert abs(r_lin.distance.raw_value - d_lin) < 1e-9
        assert abs(r_lin.height.raw_value - h_lin) < 1e-9
        assert_between(r_p.distance.raw_value, d1, d2)
        assert_between(r_p.height.raw_value, h1, h2)


    def test_trajdata_boundary_at_x1_time_key(self):
        # Continuity at x1 from both sides
        p0 = TD()
        p1 = p0._replace(time=1.0, height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, height=Distance.Foot(20.0))
        eps = 1e-9
        t_left = 1.0 - eps
        t_right = 1.0 + eps
        for method in ('linear', 'pchip'):
            y_left = TrajectoryData.interpolate('time', t_left, p0, p1, p2, method=method).height.raw_value
            y_right = TrajectoryData.interpolate('time', t_right, p0, p1, p2, method=method).height.raw_value
            y_mid = TrajectoryData.interpolate('time', 1.0, p0, p1, p2, method=method).height.raw_value
            assert abs(y_left - y_mid) < 1e-6
            assert abs(y_right - y_mid) < 1e-6


    def test_trajdata_boundary_at_x1_dimensioned_key(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, slant_height=Distance.Foot(10.0), height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, slant_height=Distance.Foot(25.0), height=Distance.Foot(25.0))
        eps_raw = 1e-6
        x1_raw = p1.slant_height.raw_value
        s_left = Distance.new_from_raw(x1_raw - eps_raw, p1.slant_height.units)
        s_right = Distance.new_from_raw(x1_raw + eps_raw, p1.slant_height.units)
        for method in ('linear', 'pchip'):
            y_left = TrajectoryData.interpolate('slant_height', s_left, p0, p1, p2, method=method).height.raw_value
            y_right = TrajectoryData.interpolate('slant_height', s_right, p0, p1, p2, method=method).height.raw_value
            y_mid = TrajectoryData.interpolate('slant_height', p1.slant_height, p0, p1, p2, method=method).height.raw_value
            assert abs(y_left - y_mid) < 1e-6
            assert abs(y_right - y_mid) < 1e-6


    def test_trajdata_non_monotone_dimensioned_field_no_overshoot(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, height=Distance.Foot(0.0))
        for t in [0.25, 0.75]:
            y = TrajectoryData.interpolate('time', t, p0, p1, p2, method='pchip').height.raw_value
            assert_between(y, p0.height.raw_value, p1.height.raw_value, eps=1e-9)
        for t in [1.25, 1.75]:
            y = TrajectoryData.interpolate('time', t, p0, p1, p2, method='pchip').height.raw_value
            assert_between(y, p1.height.raw_value, p2.height.raw_value, eps=1e-9)


    def test_trajdata_exact_match_at_p0_dimensioned_key(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, slant_height=Distance.Foot(10.0), height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, slant_height=Distance.Foot(25.0), height=Distance.Foot(25.0))
        for method in ('linear', 'pchip'):
            r = TrajectoryData.interpolate('slant_height', Distance.Foot(0.0), p0, p1, p2, method=method)
            assert r.slant_height.raw_value == p0.slant_height.raw_value
            assert r.height.raw_value == p0.height.raw_value


    def test_trajdata_pchip_monotone_decreasing_velocity(self):
        p0 = TD(velocity=Velocity.FPS(1200.0), mach=0.9)
        p1 = TD(time=1.0, distance=Distance.Foot(100.0), velocity=Velocity.FPS(900.0), mach=0.7,
                height=Distance.Foot(10.0), slant_height=Distance.Foot(10.0))
        p2 = TD(time=2.0, distance=Distance.Foot(250.0), velocity=Velocity.FPS(700.0), mach=0.6,
                height=Distance.Foot(25.0), slant_height=Distance.Foot(25.0))

        xs = [0.25, 0.5, 0.75, 1.25, 1.5, 1.75]
        last = None
        for x in xs:
            r = TrajectoryData.interpolate('time', x, p0, p1, p2, method='pchip')
            v = r.velocity.raw_value
            if last is not None:
                assert v <= last + 1e-12
            last = v


    def test_trajdata_result_units_follow_p0_all_fields(self):
        p0 = TD()
        p1 = TD(
            time=1.0,
            distance=Distance.Meter(30.48),
            velocity=Velocity.MPS(300.0),
            mach=0.4,
            height=Distance.Centimeter(304.8),
            slant_height=Distance.Centimeter(304.8),
            drop_angle=Angular.Degree(0.5),
            windage=Distance.Inch(1.0),
            windage_angle=Angular.MOA(1.0),
            slant_distance=Distance.Yard(100.0/3),
            angle=Angular.Degree(1.0),
            density_ratio=0.99,
            drag=0.1,
            energy=Energy.FootPound(100.0),
            ogw=Weight.Pound(1.0),
            flag=0,
        )
        p2 = TD(
            time=2.0,
            distance=Distance.Meter(76.2),
            velocity=Velocity.KMH(1000.0),
            mach=0.5,
            height=Distance.Yard(25.0/3),
            slant_height=Distance.Yard(25.0/3),
            drop_angle=Angular.Mil(2.0),
            windage=Distance.Foot(2.0),
            windage_angle=Angular.MRad(0.01),
            slant_distance=Distance.Meter(76.2),
            angle=Angular.Mil(3.0),
            density_ratio=0.98,
            drag=0.2,
            energy=Energy.FootPound(200.0),
            ogw=Weight.Pound(2.0),
            flag=0,
        )

        r_lin = TrajectoryData.interpolate('time', 1.5, p0, p1, p2, method='linear')
        r_p = TrajectoryData.interpolate('time', 1.5, p0, p1, p2, method='pchip')

        for r in (r_lin, r_p):
            assert_units_match(
                r,
                p0,
                [
                    'distance', 'height', 'slant_height', 'velocity', 'windage', 'windage_angle',
                    'slant_distance', 'angle', 'drop_angle', 'energy', 'ogw',
                ],
            )


    def test_trajdata_colinear_equals_linear(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, height=Distance.Foot(20.0))
        for t in [0.5, 1.0, 1.5]:
            r_lin = TrajectoryData.interpolate('time', t, p0, p1, p2, method='linear')
            r_p = TrajectoryData.interpolate('time', t, p0, p1, p2, method='pchip')
            assert abs(r_lin.height.raw_value - r_p.height.raw_value) < 1e-12


    def test_trajdata_small_interval_stability(self):
        p0 = TD(time=1.0, height=Distance.Foot(1.0), slant_height=Distance.Foot(1.0))
        eps = 1e-6
        p1 = p0._replace(time=1.0 + eps, height=Distance.Foot(1.0 + 1e-6))
        p2 = p0._replace(time=1.0 + 2*eps, height=Distance.Foot(1.0 + 2e-6))
        for t in [1.0 + 0.5*eps, 1.0 + 1.5*eps]:
            r_lin = TrajectoryData.interpolate('time', t, p0, p1, p2, method='linear')
            r_p = TrajectoryData.interpolate('time', t, p0, p1, p2, method='pchip')
            assert abs(r_lin.height.raw_value - r_p.height.raw_value) < 1e-6


    def test_trajdata_invalid_method_raises(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, height=Distance.Foot(20.0))
        with pytest.raises(ValueError):
            _ = TrajectoryData.interpolate('time', 0.5, p0, p1, p2, method='spline')  # type: ignore[arg-type]


    def test_trajdata_flag_propagation(self):
        p0 = TD()
        p1 = p0._replace(time=1.0, height=Distance.Foot(10.0))
        p2 = p0._replace(time=2.0, height=Distance.Foot(20.0))
        r = TrajectoryData.interpolate('time', 0.5, p0, p1, p2, flag=123, method='pchip')
        assert r.flag == 123

TD = TestTrajectoryDataInterpolation.TD
chord = TestTrajectoryDataInterpolation.chord
assert_between = TestTrajectoryDataInterpolation.assert_between
assert_units_match = TestTrajectoryDataInterpolation.assert_units_match
