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
        with pytest.raises(ValueError, match="For an incremental step \(step > 0\), 'start' cannot be greater than 'end'."):
            list(Unit.Meter.counter(0, 10, -100)) # start > end with positive step
        # Matches your exact error message for decrementing step
        with pytest.raises(ValueError, match="For a decrementing step \(step < 0\) 'start' cannot be less than 'end'."):
            list(Unit.Meter.counter(-100, -10, 0)) # start < end with negative step


    def test_counter_non_numeric_input(self):
        with pytest.raises(TypeError): # Or ValueError, depending on implementation
            list(Unit.Meter.counter("a", 1, 10))

    def test_iterator_non_numeric_input(self):
        with pytest.raises(TypeError): # Or ValueError
            list(Unit.Meter.iterator([1, "b", 3]))