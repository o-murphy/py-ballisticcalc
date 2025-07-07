import pytest

from py_ballisticcalc.unit import *


# Helper function adapted for direct use in parameterized tests
# It no longer needs 'test' as an argument, as 'unit_class' is passed directly
def back_n_forth_pytest(value, units, unit_class):
    u = unit_class(value, units)
    v = u >> units
    assert pytest.approx(v, abs=1e-7) == value


class TestUnitsParser:
    @pytest.mark.parametrize(
        "case",
        [
            '10', '10.2', '.2', '0.', '10ft*lb', '10footpound'
        ],
        ids=lambda c: f"parse_value_{c.replace('.', '_').replace('*', '_')}"
    )
    def test_parse_values(self, case):
        # Test with Unit.FootPound directly
        ret = _parse_value(case, Unit.FootPound)
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'footpound'
        ret = _parse_value(case, 'footpound')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'ft*lb'
        ret = _parse_value(case, 'ft*lb')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'energy'
        ret = _parse_value(case, 'energy')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

    def test_parse_units(self):
        ret = _parse_unit('ft*lb')
        assert isinstance(ret, Unit)

        ret = _parse_unit("newton")
        assert ret == Unit.Newton


class TestAngular:
    # Define unit_class and unit_list as class attributes
    unit_class = Angular
    unit_list = [
        Angular.Degree,
        Angular.MOA,
        Angular.MRad,
        Angular.Mil,
        Angular.Radian,
        Angular.Thousandth
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_angular(self, u):
        back_n_forth_pytest(3, u, self.unit_class)

    def test_angle_truncation(self):
        assert pytest.approx(Angular(720, Angular.Degree).raw_value) == Angular(0, Angular.Degree).raw_value


class TestDistance:
    unit_class = Distance
    unit_list = [
        Distance.Centimeter,
        Distance.Foot,
        Distance.Inch,
        Distance.Kilometer,
        Distance.Line,
        Distance.Meter,
        Distance.Millimeter,
        Distance.Mile,
        Distance.NauticalMile,
        Distance.Yard
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_distance(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestEnergy:
    unit_class = Energy
    unit_list = [
        Energy.FootPound,
        Energy.Joule
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_energy(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestPressure:
    unit_class = Pressure
    unit_list = [
        Pressure.Bar,
        Pressure.hPa,
        Pressure.MmHg,
        Pressure.InHg
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_pressure(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestTemperature:
    unit_class = Temperature
    unit_list = [
        Temperature.Fahrenheit,
        Temperature.Kelvin,
        Temperature.Celsius,
        Temperature.Rankin
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_temperature(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestVelocity:
    unit_class = Velocity
    unit_list = [
        Velocity.FPS,
        Velocity.KMH,
        Velocity.KT,
        Velocity.MPH,
        Velocity.MPS
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_velocity(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestWeight:
    unit_class = Weight
    unit_list = [
        Weight.Grain,
        Weight.Gram,
        Weight.Kilogram,
        Weight.Newton,
        Weight.Ounce,
        Weight.Pound
    ]

    @pytest.mark.parametrize("u", unit_list, ids=lambda u: f"unit_{u.name}")
    def test_weight(self, u):
        back_n_forth_pytest(3, u, self.unit_class)


class TestUnitConversionSyntax:

    def setup_method(self) -> None:
        self.low = Distance.Yard(10)
        self.high = Distance.Yard(100)

    def test__eq__(self):
        assert self.low == 360
        assert 360 == self.low
        assert self.low == self.low
        assert self.low == Distance.Foot(30)

    def test__ne__(self):
        assert Distance.Yard(100) != Distance.Yard(90)

    def test__lt__(self):
        assert self.low < self.high
        assert 10 < self.high
        assert self.low < 9999

    def test__gt__(self):
        assert self.high > self.low
        assert self.high > 10
        assert 9000 > self.low

    def test__ge__(self):
        assert self.high >= self.low
        assert self.high >= self.high
        assert self.high >= 90
        assert self.high >= 0

    def test__le__(self):
        assert self.low <= self.high
        assert self.high <= self.high
        assert self.low <= 360
        assert self.low <= 360

    def test__rshift__(self):
        assert isinstance(self.low >> Distance.Meter, (int, float))
        # Note: In pytest, modifying instance state within a test function
        # when using parametrize might lead to unexpected interactions
        # if the test function is not truly isolated.
        # For assignment operations like >>=, it's often better to test
        # the return value or a new instance.
        # However, for direct assignment like this, it's usually fine
        # as each parameterized test run is a fresh call.
        temp_low = Distance.Yard(10)  # Use a temporary variable for clarity
        temp_low >>= Distance.Meter
        assert isinstance(temp_low, (int, float))

    def test__lshift__(self):
        desired_unit_type = Distance
        desired_units = Distance.Foot
        converted = self.low << desired_units
        assert isinstance(converted, desired_unit_type)
        assert converted.units == desired_units
        temp_low = Distance.Yard(10)  # Use a temporary variable for clarity
        temp_low <<= desired_units
        assert temp_low.units == desired_units
