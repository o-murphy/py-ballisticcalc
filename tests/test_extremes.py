import math
import pytest

from py_ballisticcalc import *
from py_ballisticcalc.helpers import vacuum_range, EARTH_GRAVITY_CONSTANT_IN_SI
from py_ballisticcalc.vector import Vector


class TestAtmoBoundaries:
    def test_humidity_accepts_fraction_and_percent(self):
        a = Atmo.icao()
        # Set as percent -> stored as fraction
        a.humidity = 50
        assert pytest.approx(a.humidity, abs=1e-12) == 0.5
        # Set as fraction -> stored unchanged
        a.humidity = 0.25
        assert pytest.approx(a.humidity, abs=1e-12) == 0.25

    @pytest.mark.parametrize("bad", [-0.01, -10, 100.01, 1e6])
    def test_humidity_out_of_range_raises(self, bad):
        a = Atmo.icao()
        with pytest.raises(ValueError):
            a.humidity = bad

    def test_altitude_reuse_window_edges(self):
        a = Atmo.icao(Distance.Foot(1000))
        dr0, m0 = a.get_density_and_mach_for_altitude(1000.0)
        # Exactly within 30 ft should reuse cached values
        dr1, m1 = a.get_density_and_mach_for_altitude(1000.0 + 29.999)
        assert dr1 == pytest.approx(dr0)
        assert m1 == pytest.approx(m0)
        # Outside window recomputes; values should still be sane
        dr2, m2 = a.get_density_and_mach_for_altitude(1000.0 + 31.0)
        assert 0 < dr2 < 2 and m2 > 0

    def test_temperature_at_altitude_floor(self):
        a = Atmo.icao()
        with pytest.warns(RuntimeWarning):
            t = a.temperature_at_altitude(1e9)
        # Not below absolute-zero in Celsius
        assert t >= Atmo.cLowestTempC - 1e-9


class TestWindVectors:
    @pytest.mark.parametrize(
        "deg, expect_x, expect_z",
        [
            (0.0, 1.0, 0.0),    # tailwind
            (90.0, 0.0, 1.0),   # from left to right -> +z
            (180.0, -1.0, 0.0), # headwind
            (270.0, 0.0, -1.0), # from right to left -> -z
        ],
    )
    def test_cardinal_directions(self, deg, expect_x, expect_z):
        w = Wind(velocity=Velocity.FPS(10), direction_from=Angular.Degree(deg))
        v = w.vector
        # Components scaled by 10 fps
        assert v.x == pytest.approx(10 * expect_x, abs=1e-9)
        assert v.z == pytest.approx(10 * expect_z, abs=1e-9)
        assert v.y == 0.0


class TestVectorEdge:
    def test_normalize_near_zero_returns_unchanged(self):
        eps = 1e-12
        v = Vector(eps, -eps, eps)
        n = v.normalize()
        # Threshold in implementation is 1e-10
        assert n == v


class TestInterpolationTightSpacing:
    def test_three_point_pchip_tiny_interval(self):
        from py_ballisticcalc.interpolation import interpolate_3_pt
        # Very tight spacing between first two points
        x0, x1, x2 = 0.0, 1e-12, 1.0
        y0, y1, y2 = 0.0, 1e-12, 1.0
        # Should not raise and should be within envelope
        y = interpolate_3_pt(5e-13, x0, y0, x1, y1, x2, y2)
        assert 0.0 - 1e-12 <= y <= 1.0 + 1e-12


class TestHelpersVacuum:
    def test_vacuum_range_zero_or_ninety_angle(self):
        assert vacuum_range(100.0, 0.0) == pytest.approx(0.0)
        assert vacuum_range(100.0, 90.0) == pytest.approx(0.0)

    def test_vacuum_range_negative_gravity_handled(self):
        # Function flips sign of gravity if negative
        g = -EARTH_GRAVITY_CONSTANT_IN_SI
        r1 = vacuum_range(50.0, 45.0, gravity=g)
        r2 = vacuum_range(50.0, 45.0, gravity=abs(g))
        assert r1 == pytest.approx(r2)

    def test_vacuum_angle_to_zero_domain_error(self):
        # distance too large -> argument to asin > 1 => ValueError
        from py_ballisticcalc.helpers import vacuum_angle_to_zero
        v = 10.0
        g = EARTH_GRAVITY_CONSTANT_IN_SI
        # Make distance slightly larger than max range achievable at 45 deg
        d = (v**2 / g) * 1.01
        with pytest.raises(ValueError):
            _ = vacuum_angle_to_zero(v, d, gravity=g)

    def test_vacuum_velocity_to_zero_zero_angle_division_by_zero(self):
        from py_ballisticcalc.helpers import vacuum_velocity_to_zero
        with pytest.raises(ZeroDivisionError):
            _ = vacuum_velocity_to_zero(1.0, 0.0)


class TestUnitsDivisionErrors:
    def test_division_by_zero_number_raises(self):
        d = Distance.Meter(1.0)
        with pytest.raises(ZeroDivisionError):
            _ = d / 0

    def test_division_by_zero_dimension_raises(self):
        d = Distance.Meter(1.0)
        z = Distance.Meter(0.0)
        with pytest.raises(ZeroDivisionError):
            _ = d / z


class TestWindMaxDistance:
    def test_custom_max_distance_used_for_default_until(self):
        w = Wind(velocity=Velocity.FPS(1), direction_from=Angular.Degree(0), max_distance_feet=12345)
        assert w.until_distance == Distance.Foot(12345)


class TestVectorLargeMagnitude:
    def test_magnitude_large_values(self):
        # Should not raise; hypot returns inf for extremely large values
        v = Vector(1e308, 1e308, 1e308)
        m = v.magnitude()
        assert math.isfinite(m) or math.isinf(m)
