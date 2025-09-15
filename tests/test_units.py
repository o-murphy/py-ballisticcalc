import pytest

from py_ballisticcalc import loadImperialUnits, loadMixedUnits, loadMetricUnits
from py_ballisticcalc.unit import *


# Helper function adapted for direct use in parameterized tests
def back_n_forth_pytest(value, units, unit_class):
    u = unit_class(value, units)
    v = u >> units
    assert pytest.approx(v, abs=1e-7) == value


class TestUnitLoaders:
    def test_loaders(self):
        PreferredUnits.restore_defaults()
        assert PreferredUnits.temperature == Unit.Fahrenheit
        loadMixedUnits()
        assert PreferredUnits.temperature == Unit.Celsius
        loadImperialUnits()
        assert PreferredUnits.temperature == Unit.Fahrenheit
        loadMetricUnits()
        assert PreferredUnits.temperature == Unit.Celsius
        PreferredUnits.restore_defaults()
        assert PreferredUnits.temperature == Unit.Fahrenheit


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
        ret = Unit.parse(case, Unit.FootPound)
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'footpound'
        ret = Unit.parse(case, 'footpound')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'ft*lb'
        ret = Unit.parse(case, 'ft*lb')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

        # Test with string 'energy'
        ret = Unit.parse(case, 'energy')
        assert isinstance(ret, Energy)
        assert ret.units == Unit.FootPound

    def test_parse_units(self):
        ret = Unit._parse_unit('ft*lb')
        assert isinstance(ret, Unit)

        ret = Unit._parse_unit("newton")
        assert ret == Unit.Newton

    def test_parse_unit_mixed_case_and_whitespace(self):
        assert Unit._parse_unit(' Ft ') == Unit.Foot
        assert Unit._parse_unit('  m / s ') == Unit.MPS
        assert Unit._parse_unit('\tinHg\t') == Unit.InHg
        # inches per 100 yards variants
        assert Unit._parse_unit('in/100yard') == Unit.InchesPer100Yd
        assert Unit._parse_unit('inper100yd') == Unit.InchesPer100Yd

    def test_parse_unit_pluralization_and_aliases(self):
        assert Unit._parse_unit('yards') == Unit.Yard
        assert Unit._parse_unit('feet') == Unit.Foot

    def test_parse_value_with_embedded_units_and_spaces(self):
        ret = Unit.parse('  12.5  ft / s  ', Unit.MPS)
        assert ret.units == Unit.FPS  # parsing takes embedded alias; preferred only for plain numbers

        ret2 = Unit.parse('1000 psi', None)
        assert ret2.units == Unit.PSI

    def test_parse_value_invalid_alias_raises(self):
        with pytest.raises(UnitAliasError):
            _ = Unit.parse('10 foobars', None)

    def test_parse_unit_unknown_returns_none(self):
        assert Unit._parse_unit('nonesuch') is None


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
        # Angles should be normalized to the interval (-180, 180] degrees.
        assert pytest.approx(Angular(540, Angular.Degree).raw_value) == Angular(180, Angular.Degree).raw_value
        assert pytest.approx(Angular(-270, Angular.Degree).raw_value) == Angular(90, Angular.Degree).raw_value


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

    def test_temperature_addition_clamps_absolute_zero(self):
        t = Temperature.Kelvin(10)
        t2 = t + (-1000)
        assert (t2 >> Temperature.Kelvin) == pytest.approx(0.0)

    def test_temperature_mul_div_raise(self):
        with pytest.raises(TypeError):
            _ = Temperature.Celsius(10) * 2
        with pytest.raises(TypeError):
            _ = Temperature.Celsius(10) / 2


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


class TestArithmetic:

    def test_mul_div_with_numbers(self):
        d = Distance.Yard(3)
        c = 2
        assert isinstance(d * c, Distance)
        assert pytest.approx((d * c).raw_value) == c * d.raw_value
        assert pytest.approx((c * d).raw_value) == c * d.raw_value
        assert isinstance(d / c, Distance)
        assert pytest.approx((d / c).raw_value) == d.raw_value / c

    def test_same_dimension_div(self):
        a = Distance.Meter(2)
        b = Distance.Inch(5)
        assert isinstance(a / b, float)
        assert pytest.approx(a / b) == a.raw_value / b.raw_value
        assert isinstance(b / a, float)
        assert pytest.approx(b / a) == b.raw_value / a.raw_value

    def test_same_dimension_add_sub(self):
        a = Distance.Meter(2)
        b = Distance.Yard(1)
        c = a + b
        assert isinstance(c, Distance)
        # raw values should add, preserving left units
        assert pytest.approx(c.raw_value) == a.raw_value + b.raw_value
        assert c.units == a.units
        c = a - b
        assert pytest.approx(c.raw_value) == a.raw_value - b.raw_value
        assert c.units == a.units

    def test_add_sub_with_numbers(self):
        a = Distance.Meter(2)
        # +5 meters
        c = a + 5
        assert isinstance(c, Distance)
        assert pytest.approx(c >> Distance.Meter) == pytest.approx(7)
        # radd
        c2 = 5 + a
        assert pytest.approx(c2 >> Distance.Meter) == pytest.approx(7)
        # subtraction
        c3 = a - 5
        assert pytest.approx(c3 >> Distance.Meter) == pytest.approx(-3)
        c4 = 5 - a
        # interpret as 5 meters minus a
        assert pytest.approx(c4 >> Distance.Meter) == pytest.approx(3)

    def test_inplace_with_numbers(self):
        a = Distance.Meter(2)
        a += 5
        assert pytest.approx(a >> Distance.Meter) == 7
        a -= 2
        assert pytest.approx(a >> Distance.Meter) == 5
        a *= 2
        assert pytest.approx(a >> Distance.Meter) == 10
        a /= 2
        assert pytest.approx(a >> Distance.Meter) == 5

    def test_inplace_with_same_dimension(self):
        a = Distance.Meter(2)
        a += Distance.Meter(5)
        assert pytest.approx(a >> Distance.Meter) == 7
        a -= Distance.Meter(2)
        assert pytest.approx(a >> Distance.Meter) == 5
        a /= Distance.Meter(2)
        assert pytest.approx(a) == 2.5

    def test_temperature_rules(self):
        tC = Temperature.Celsius(20)
        # addition/subtraction in current unit
        t2 = tC + 5
        assert isinstance(t2, Temperature)
        assert pytest.approx(t2 >> Temperature.Celsius) == 25
        t3 = tC - 10
        assert pytest.approx(t3 >> Temperature.Celsius) == 10
        # absolute zero clamp
        t4 = Temperature.Celsius(-270) - 10
        assert pytest.approx(t4 >> Temperature.Celsius) == -273.15
        # no multiplication or division
        with pytest.raises(TypeError):
            _ = tC * 2
        with pytest.raises(TypeError):
            _ = 2 * tC
        with pytest.raises(TypeError):
            _ = tC / 2
        with pytest.raises(TypeError):
            _ = 2 / tC


class TestIterator:

    @pytest.mark.parametrize(
        "start, step, end, include_end, expected_count, expected_values",
        [
            (0, 100, 1000, True, 11, [i * 100 for i in range(11)]),
            (0, 100, 1000, False, 10, [i * 100 for i in range(10)]),
        ]
    )
    def test_finite_counter(self, start, step, end, include_end, expected_count, expected_values):
        counter = Unit.Meter.counter(start, step, end, include_end=include_end)
        items = list(counter) # Convert to list to check all at once and count

        assert len(items) == expected_count
        for i, item in enumerate(items):
            assert isinstance(item, Distance)
            # Use pytest.approx for robust float comparison
            assert (item >> Distance.Meter) == pytest.approx(expected_values[i])

    def test_infinite_counter(self):
        counter = Unit.Meter.counter(0, 100)
        for i in range(10):
            item = next(counter)
            assert isinstance(item, Distance)
            assert (item >> Distance.Meter) == pytest.approx(i * 100)

    @pytest.mark.parametrize(
        "start, step, end, include_end, expected_count, expected_values",
        [
            (-100, -50, -500, True, 9, [-100 - i * 50 for i in range(9)]),
            (-100, -50, -500, False, 8, [-100 - i * 50 for i in range(8)]),
        ]
    )
    def test_backward_finite_counter(self, start, step, end, include_end, expected_count, expected_values):
        counter = Unit.Meter.counter(start, step, end, include_end=include_end)
        items = list(counter)

        assert len(items) == expected_count
        for i, item in enumerate(items):
            assert isinstance(item, Distance)
            assert (item >> Distance.Meter) == pytest.approx(expected_values[i])

    def test_backward_infinite_counter(self):
        counter = Unit.Meter.counter(-100, -50)
        for i in range(10):
            item = next(counter)
            assert isinstance(item, Distance)
            assert (item >> Distance.Meter) == pytest.approx(-100 - i * 50)

    @pytest.mark.parametrize(
        "input_items, sort, reverse, expected_values",
        [
            ([0, 200, 100], False, False, [0, 200, 100]),
            ([0, 200, 100], True, False, [0, 100, 200]),
            ([0, 200, 100], True, True, [200, 100, 0]),
            ([], False, False, []), # Test empty list
            ([50], False, False, [50]), # Test single item list
        ]
    )
    def test_iterable_generic(self, input_items, sort, reverse, expected_values):
        iterable = Unit.Meter.iterator(input_items, sort=sort, reverse=reverse)
        items = list(iterable) # Convert to list to check all at once

        assert len(items) == len(expected_values)
        for i, item in enumerate(items):
            assert isinstance(item, Distance)
            assert (item >> Unit.Meter) == pytest.approx(expected_values[i])

    def test_counter_infinite_invalid_step(self):
        with pytest.raises(ValueError, match="For infinite iteration, 'step' cannot be zero."):
            list(Unit.Meter.counter(0, 0, ))

    # Test for finite counter with step = 0
    def test_counter_finite_zero_step(self):
        # As per your counter logic, for step=0 and finite end, it yields 'start' once.
        counter = Unit.Meter.counter(10, 0, 20)
        items = list(counter)
        assert len(items) == 1
        assert (items[0] >> Distance.Meter) == pytest.approx(10)

        counter_equal_start_end = Unit.Meter.counter(10, 0, 10)
        items_equal_start_end = list(counter_equal_start_end)
        assert len(items_equal_start_end) == 1
        assert (items_equal_start_end[0] >> Distance.Meter) == pytest.approx(10)


    def test_counter_inconsistent_step_direction(self):
        # Matches your exact error message for incremental step
        with pytest.raises(ValueError, match=r"For an incremental step \(step > 0\), 'start' cannot be greater than 'end'."):
            list(Unit.Meter.counter(0, 10, -100)) # start > end with positive step
        # Matches your exact error message for decrementing step
        with pytest.raises(ValueError, match=r"For a decrementing step \(step < 0\), 'start' cannot be less than 'end'."):
            list(Unit.Meter.counter(-100, -10, 0)) # start < end with negative step


    def test_counter_non_numeric_input(self):
        with pytest.raises(TypeError): # Or ValueError, depending on implementation
            list(Unit.Meter.counter("a", 1, 10))  # type: ignore

    def test_iterator_non_numeric_input(self):
        with pytest.raises(TypeError): # Or ValueError
            list(Unit.Meter.iterator([1, "b", 3]))  # type: ignore
