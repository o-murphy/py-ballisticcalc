"""Unit conversion system for ballistic calculations.

This module provides a comprehensive type-safe unit conversion system, supporting physical dimensions
including distance, velocity, angular measurements, temperature, pressure, weight, energy, and time.

The system uses a base class `GenericDimension` with specialized subclasses for each physical dimension.
Each dimension maintains its values internally in a fixed raw unit (e.g., inches for distance, m/s for velocity)
and provides conversion methods to any supported unit within that dimension.

Key Features:
    * Type-safe unit conversions with compile-time checking
    * Flexible conversion syntax with operator overloading
    * Default preferred units configuration
    * String parsing and unit alias resolution
    * Integration with ballistic calculation engines

Typical Usage:
    >>> from py_ballisticcalc.unit import Distance, Velocity, Unit
    >>> # Create distance measurement
    >>> distance = Distance(100, Distance.Meter)
    >>> # Convert to different units
    >>> yards = distance.convert(Distance.Yard)
    >>> # Alternative conversion syntax
    >>> yards = distance << Distance.Yard
    >>> # Get numeric value in specific units
    >>> yard_value = distance.get_in(Distance.Yard)
    >>> print(f"100m = {yard_value:.1f} yards")

Supported Dimensions:
    * Distance: inch, foot, yard, mile, nautical mile, mm, cm, m, km, line
    * Velocity: m/s, km/h, ft/s, mph, knots
    * Angular: radian, degree, MOA, mil, mrad, thousandth, inch/100yd, cm/100m, o'clock
    * Temperature: Fahrenheit, Celsius, Kelvin, Rankine
    * Pressure: mmHg, inHg, bar, hPa, PSI
    * Weight: grain, ounce, gram, pound, kilogram, newton
    * Energy: foot-pound, joule
    * Time: second, minute, millisecond, microsecond, nanosecond, picosecond

The module also provides `PreferredUnits` configuration for setting default units that apply
throughout the ballistic calculation system, and comprehensive string parsing capabilities for input processing.

Examples:
    Basic unit creation and conversion:
        >>> distance = Distance.Meter(300)
        >>> range_yards = distance.convert(Distance.Yard)
        >>> print(f"300m = {range_yards}")

    Working with velocity:
        >>> muzzle_velocity = Velocity.FPS(2800)
        >>> velocity_mps = muzzle_velocity >> Velocity.MPS
        >>> print(f"2800 ft/s = {velocity_mps:.1f} m/s")

    Angular measurements for ballistics:
        >>> elevation = Angular.MOA(2.5)
        >>> elevation_mils = elevation << Angular.Mil
        >>> print(f"2.5 MOA = {elevation_mils:.3f} mils")

    Setting preferred units:
        >>> PreferredUnits.distance = Unit.Meter
        >>> PreferredUnits.velocity = Unit.MPS
        >>> # Now ballistic calculations will use metric units by default
"""

# Standard library imports
import re
from dataclasses import dataclass, fields, MISSING
from enum import IntEnum
from math import pi
from typing import NamedTuple, Union, TypeVar, Optional, Tuple, Final, Protocol, runtime_checkable, \
    SupportsFloat, SupportsInt, Hashable, Generic, Mapping, Any, Iterable, Sequence, Callable, Generator

from typing_extensions import Self, TypeAlias, override

# Local imports
from py_ballisticcalc.exceptions import UnitTypeError, UnitConversionError, UnitAliasError
from py_ballisticcalc.logger import logger

Number: TypeAlias = Union[float, int]
MAX_ITERATIONS = 1e6


def counter(start: Number = 0, step: Number = 1, end: Optional[Number] = None) -> Iterable[Number]:
    """Generate a sequence of numbers with optional bounds.

    Creates an arithmetic sequence starting at 'start' with a constant increment/decrement of 'step'.
    Can generate infinite sequences or bounded sequences up to 'end'.

    Args:
        start: Initial value for the sequence. Defaults to 0.
        step: Increment/decrement step value. Cannot be 0 for infinite iteration.
              Positive values create ascending sequences, negative values create descending sequences. Defaults to 1.
        end: Final value (exclusive) for bounded sequences. If None, creates an infinite sequence. Defaults to None.

    Yields:
        Number: The next value in the arithmetic sequence.

    Raises:
        ValueError: If 'step' is 0 for infinite iteration, or if 'step' has the wrong sign
                    for the given 'start' and 'end' range (e.g., positive step with start > end).

    Examples:
        >>> # Finite ascending sequence
        >>> list(counter(0, 1, 5))
        [0, 1, 2, 3, 4]
        
        >>> # Finite descending sequence
        >>> list(counter(10, -2, 0))
        [10, 8, 6, 4, 2]
        
        >>> # Infinite sequence (first 3 values)
        >>> iter_seq = counter(1, 0.5)
        >>> [next(iter_seq) for _ in range(3)]
        [1, 1.5, 2.0]
    """
    if step == 0:
        if end is None:
            raise ValueError("For infinite iteration, 'step' cannot be zero.")
        else:
            if (end > start and start <= end) or (end < start and start >= end) or (start == end):
                yield start
            return

    current = start
    if end is None:
        while True:
            yield current
            current += step
    else:
        if step > 0:
            if start > end:
                raise ValueError("For an incremental step (step > 0), 'start' cannot be greater than 'end'.")
            while current < end:
                yield current
                current += step
        else:  # step < 0
            if start < end:
                raise ValueError("For a decrementing step (step < 0), 'start' cannot be less than 'end'.")
            while current > end:
                yield current
                current += step


def iterator(items: Sequence[Number], /, *,
             sort: bool = False,
             key: Optional[Callable[[Number], Any]] = None,
             reverse: bool = False) -> Generator[Number, None, None]:
    """Create a generator from a sequence of numbers with optional sorting.

    Provides a flexible iterator interface for numeric sequences.
    Supports optional sorting with custom key functions and reverse ordering.

    Args:
        items: Sequence of numeric values (integers or floats) to iterate over.
        sort: If True, sort the items before iteration. Defaults to False.
        key: Optional function to extract comparison key from each item.
             Used only when sort=True. Defaults to None.
        reverse: If True, reverse the iteration order (used with sorting).
                 Defaults to False.

    Yields:
        Number: Each numeric value from the sequence in the specified order.

    Examples:
        >>> # Basic iteration
        >>> list(iterator([3, 1, 4, 2]))
        [3, 1, 4, 2]
        
        >>> # Sorted iteration
        >>> list(iterator([3, 1, 4, 2], sort=True))
        [1, 2, 3, 4]
        
        >>> # Reverse sorted iteration
        >>> list(iterator([3, 1, 4, 2], sort=True, reverse=True))
        [4, 3, 2, 1]
        
        >>> # Custom key function
        >>> list(iterator([-3, 1, -4, 2], sort=True, key=abs))
        [1, 2, -3, -4]
    """
    if sort:
        items = sorted(items, key=key, reverse=reverse)
    for v in items:
        yield v


@runtime_checkable
class Comparable(Protocol):
    def __eq__(self, other: object) -> bool: ...

    def __lt__(self, other: Self) -> bool: ...

    def __gt__(self, other: Self) -> bool: ...

    def __le__(self, other: Self) -> bool: ...

    def __ge__(self, other: Self) -> bool: ...


_GenericDimensionType = TypeVar('_GenericDimensionType', bound='GenericDimension')


class Unit(IntEnum):
    """Enumeration of all supported unit types.

    Angular Units:
    - Radian, Degree, MOA (Minute of Arc), Mil, MRad (Milliradian), Thousandth, InchesPer100Yd, CmPer100m, OClock
    
    Distance Units:
    - Inch, Foot, Yard, Mile, NauticalMile, Millimeter, Centimeter, Meter, Kilometer, Line
    
    Velocity Units:
    - MPS (meters/second), KMH (km/hour), FPS (feet/second), MPH (miles/hour), KT (knots)
    
    Weight Units:
    - Grain, Ounce, Gram, Pound, Kilogram, Newton
    
    Pressure Units:
    - MmHg, InHg, Bar, hPa (hectopascal), PSI
    
    Temperature Units:
    - Fahrenheit, Celsius, Kelvin, Rankin
    
    Energy Units:
    - FootPound, Joule
    
    Time Units:
    - Second, Minute, Millisecond, Microsecond, Nanosecond, Picosecond

    Each unit can be used as a callable constructor for creating unit instances:

    Examples:
        >>> # Create distance measurements
        >>> distance = Unit.Meter(100)
        >>> range_yards = Unit.Yard(109.4)
        
        >>> # Create velocity measurements
        >>> muzzle_velocity = Unit.FPS(2800)
        >>> velocity_mps = Unit.MPS(853.4)
        
        >>> # Angular measurements for ballistics
        >>> elevation = Unit.MOA(2.5)
        >>> windage = Unit.Mil(1.2)
    """
    Radian = 0
    Degree = 1
    MOA = 2
    Mil = 3
    MRad = 4
    Thousandth = 5
    InchesPer100Yd = 6
    CmPer100m = 7
    OClock = 8

    Inch = 10
    Foot = 11
    Yard = 12
    Mile = 13
    NauticalMile = 14
    Millimeter = 15
    Centimeter = 16
    Meter = 17
    Kilometer = 18
    Line = 19

    FootPound = 30
    Joule = 31

    MmHg = 40
    InHg = 41
    Bar = 42
    hPa = 43
    PSI = 44

    Fahrenheit = 50
    Celsius = 51
    Kelvin = 52
    Rankin = 53

    MPS = 60
    KMH = 61
    FPS = 62
    MPH = 63
    KT = 64

    Grain = 70
    Ounce = 71
    Gram = 72
    Pound = 73
    Kilogram = 74
    Newton = 75

    Minute = 80
    Second = 81
    Millisecond = 82
    Microsecond = 83
    Nanosecond = 84
    Picosecond = 85

    @property
    def key(self) -> str:
        """Readable name of the unit of measure"""
        return UnitPropsDict[self].name

    @property
    def accuracy(self) -> int:
        """Default accuracy of the unit of measure"""
        return UnitPropsDict[self].accuracy

    @property
    def symbol(self) -> str:
        """Short symbol of the unit of measure"""
        return UnitPropsDict[self].symbol

    def __repr__(self) -> str:
        return UnitPropsDict[self].name

    def __call__(self: Self, value: Union[Number, _GenericDimensionType]) -> _GenericDimensionType:
        """Creates a new unit instance using dot syntax.

        Args:
            value (Union[Number, _GenericDimensionType]): Numeric value of the unit
                                                          or an existing GenericDimension instance.

        Returns:
            _GenericDimensionType: An instance of the corresponding unit dimension.

        Raises:
            UnitTypeError: If the unit type is not supported.
        """
        obj: GenericDimension
        if isinstance(value, GenericDimension):
            return value << self  # type: ignore
        if 0 <= self < 10:
            obj = Angular(value, self)
        elif 10 <= self < 20:
            obj = Distance(value, self)
        elif 30 <= self < 40:
            obj = Energy(value, self)
        elif 40 <= self < 50:
            obj = Pressure(value, self)
        elif 50 <= self < 60:
            obj = Temperature(value, self)
        elif 60 <= self < 70:
            obj = Velocity(value, self)
        elif 70 <= self < 80:
            obj = Weight(value, self)
        elif 80 <= self < 90:
            obj = Time(value, self)
        else:
            raise UnitTypeError(f"{self} Unit is not supported")
        return obj  # type: ignore

    def counter(self, start: Number, step: Number,
            end: Optional[Number] = None, include_end: bool = True) -> Generator[_GenericDimensionType, None, None]:
        """Generates a finite or infinite sequence of `GenericDimension` objects.

        This function acts as a counter for measurements, yielding `GenericDimension`
        instances at specified intervals, defined by `start`, `step`, and `end`.
        The underlying numeric values are handled as raw values of the given unit.

        Args:
            self: The unit to apply to each generated numeric value (e.g., `Unit.Meter`, `Unit.Second`).
            start: The starting raw value for the sequence. Defaults to 0.
            step: The increment/decrement step for the sequence.
                                Must not be 0 for an infinite sequence. Defaults to 0.
            end: The raw value at which the sequence should stop (exclusive by default).
                                         If `None`, the sequence is infinite. Defaults to `None`.
            include_end: If `True` and `end` is provided, the `end` value will be
                                included in the sequence. Defaults to `True`.

        Yields:
            _GenericDimensionType: A `GenericDimension` object of the specific type implied by `u`,
                                   representing the current measurement in the sequence.

        Raises:
            ValueError:
                If `step` is 0 for an infinite sequence, or if `step` has the wrong
                direction for the given `start` and `end` range.
            StopIteration:
                If the iteration limit (`MAX_ITERATIONS`) is reached during an infinite sequence.

        Examples:
            >>> from py_ballisticcalc import Distance, Unit
            >>> list(Unit.Meter.counter(start=0, step=100, end=300)) # Inferred as Generator[Distance]
            [Distance(0), Distance(100), Distance(200)]
        """
        _start: _GenericDimensionType = self(start)
        _step: _GenericDimensionType = self(step)
        _end: Optional[_GenericDimensionType] = self(end) if end is not None else None

        _start_raw: Number = _start.raw_value
        _step_raw: Number = _step.raw_value
        _end_raw: Optional[Number] = _end.raw_value if _end is not None else None

        if _end_raw is not None and include_end:
            _end_raw += _step_raw
        for i, raw_value in enumerate(counter(_start_raw, _step_raw, _end_raw)):
            value: _GenericDimensionType = self(0)
            value._value = raw_value
            yield value
            if i == MAX_ITERATIONS:
                raise StopIteration("Max counter iterations limit is %d" % MAX_ITERATIONS)

    def iterator(self, items: Sequence[Number], /, *,
                 sort: bool = False,
                 reverse: bool = False) -> Generator[_GenericDimensionType, None, None]:
        """Creates a sorted sequence of `GenericDimension` objects from raw numeric values.

        Args:
            self: The unit to apply to each numeric value (e.g., `Unit.Meter`, `Unit.FPS`).
            items: A sequence of raw numeric values (integers or floats).
            sort: If set to `True`, the elements will be sorted before yield.
            reverse: If set to `True`, the elements are sorted in descending order. Defaults to `False`.

        Yields:
            _GenericDimensionType: A `GenericDimension` object of the specific type implied by `u`, in sorted order.

        Examples:
            >>> from py_ballisticcalc import Distance, Unit
            >>> list(Unit.Meter.iterator([300, 100, 200], sort=True))  # Inferred as Iterable[Distance]
            [Distance(100), Distance(200), Distance(300)]
        """
        iter_ = iterator(items, sort=sort, reverse=reverse)
        for v in iter_:
            yield self(v)


class UnitProps(NamedTuple):
    """Properties and display characteristics for unit measurements.

    Attributes:
        name: Human-readable name of the unit (e.g., 'meter', 'foot-pound').
        accuracy: Number of decimal places for formatting values for display.
        symbol: Standard symbol or abbreviation for the unit (e.g., 'm', 'ft·lb').

    Examples:
        >>> from py_ballisticcalc import Distance, Unit, UnitProps, UnitPropsDict
        >>> d = Distance.Yard(600)
        >>> print(d << Distance.Kilometer)
        0.549km
        >>> UnitPropsDict[Unit.Kilometer] = UnitProps("kilometer", 5, " kilometers")
        >>> print(d << Distance.Kilometer)
        0.54864 kilometers
    """
    name: str
    accuracy: int
    symbol: str


UnitPropsDict: Mapping[Unit, UnitProps] = {
    Unit.Radian: UnitProps('radian', 6, 'rad'),
    Unit.Degree: UnitProps('degree', 4, '°'),
    Unit.MOA: UnitProps('MOA', 2, 'MOA'),
    Unit.Mil: UnitProps('mil', 3, 'mil'),
    Unit.MRad: UnitProps('mrad', 2, 'mrad'),
    Unit.Thousandth: UnitProps('thousandth', 2, 'ths'),
    Unit.InchesPer100Yd: UnitProps('inch/100yd', 2, 'in/100yd'),
    Unit.CmPer100m: UnitProps('cm/100m', 2, 'cm/100m'),
    Unit.OClock: UnitProps('hour', 2, 'h'),

    Unit.Inch: UnitProps("inch", 1, "inch"),
    Unit.Foot: UnitProps("foot", 2, "ft"),
    Unit.Yard: UnitProps("yard", 1, "yd"),
    Unit.Mile: UnitProps("mile", 3, "mi"),
    Unit.NauticalMile: UnitProps("nautical mile", 3, "nm"),
    Unit.Millimeter: UnitProps("millimeter", 3, "mm"),
    Unit.Centimeter: UnitProps("centimeter", 3, "cm"),
    Unit.Meter: UnitProps("meter", 1, "m"),
    Unit.Kilometer: UnitProps("kilometer", 3, "km"),
    Unit.Line: UnitProps("line", 3, "ln"),

    Unit.FootPound: UnitProps('foot-pound', 0, 'ft·lb'),
    Unit.Joule: UnitProps('joule', 0, 'J'),

    Unit.MmHg: UnitProps('mmHg', 0, 'mmHg'),
    Unit.InHg: UnitProps('inHg', 6, 'inHg'),
    Unit.Bar: UnitProps('bar', 2, 'bar'),
    Unit.hPa: UnitProps('hPa', 4, 'hPa'),
    Unit.PSI: UnitProps('psi', 4, 'psi'),

    Unit.Fahrenheit: UnitProps('fahrenheit', 1, '°F'),
    Unit.Celsius: UnitProps('celsius', 1, '°C'),
    Unit.Kelvin: UnitProps('kelvin', 1, '°K'),
    Unit.Rankin: UnitProps('rankin', 1, '°R'),

    Unit.MPS: UnitProps('mps', 0, 'm/s'),
    Unit.KMH: UnitProps('kmh', 1, 'km/h'),
    Unit.FPS: UnitProps('fps', 1, 'ft/s'),
    Unit.MPH: UnitProps('mph', 1, 'mph'),
    Unit.KT: UnitProps('knot', 1, 'kt'),

    Unit.Grain: UnitProps('grain', 1, 'gr'),
    Unit.Ounce: UnitProps('ounce', 1, 'oz'),
    Unit.Gram: UnitProps('gram', 1, 'g'),
    Unit.Pound: UnitProps('pound', 0, 'lb'),
    Unit.Kilogram: UnitProps('kilogram', 3, 'kg'),
    Unit.Newton: UnitProps('newton', 3, 'N'),

    Unit.Minute: UnitProps('minute', 0, 'min', ),
    Unit.Second: UnitProps('second', 1, 's'),
    Unit.Millisecond: UnitProps('millisecond', 3, 'ms', ),
    Unit.Microsecond: UnitProps('microsecond', 6, 'µs'),
    Unit.Nanosecond: UnitProps('nanosecond', 9, 'ns'),
    Unit.Picosecond: UnitProps('picosecond', 12, 'ps')
}

UnitAliasesType: TypeAlias = Mapping[Tuple[str, ...], Unit]

UnitAliases: UnitAliasesType = {
    ('radian', 'rad'): Unit.Radian,
    ('degree', 'deg'): Unit.Degree,
    ('moa',): Unit.MOA,
    ('mil',): Unit.Mil,
    ('mrad',): Unit.MRad,
    ('thousandth', 'ths'): Unit.Thousandth,
    ('inch/100yd', 'in/100yd', 'inch/100yd', 'in/100yard, inper100yd'): Unit.InchesPer100Yd,
    ('centimeter/100m', 'cm/100m', 'cm/100meter', 'centimeter/100meter', 'cmper100m'): Unit.CmPer100m,
    ('hour', 'h'): Unit.OClock,

    ('inch', 'in'): Unit.Inch,
    ('foot', 'feet', 'ft'): Unit.Foot,
    ('yard', 'yd'): Unit.Yard,
    ('mile', 'mi', 'mi.'): Unit.Mile,
    ('nauticalmile', 'nm', 'nmi'): Unit.NauticalMile,
    ('millimeter', 'mm'): Unit.Millimeter,
    ('centimeter', 'cm'): Unit.Centimeter,
    ('meter', 'm'): Unit.Meter,
    ('kilometer', 'km'): Unit.Kilometer,
    ('line', 'ln', 'liniа'): Unit.Line,

    ('footpound', 'foot-pound', 'ft⋅lbf', 'ft⋅lb', 'foot*pound', 'ft*lbf', 'ft*lb'): Unit.FootPound,
    ('joule', 'J'): Unit.Joule,

    ('mmHg',): Unit.MmHg,
    ('inHg', '"Hg'): Unit.InHg,
    ('bar',): Unit.Bar,
    ('hectopascal', 'hPa'): Unit.hPa,
    ('psi', 'lbf/in2'): Unit.PSI,

    ('fahrenheit', '°F', 'F', 'degF'): Unit.Fahrenheit,
    ('celsius', '°C', 'C', 'degC'): Unit.Celsius,
    ('kelvin', '°K', 'K', 'degK'): Unit.Kelvin,
    ('rankin', '°R', 'R', 'degR'): Unit.Rankin,

    ('meter/second', 'm/s', 'meter/s', 'm/second', 'mps'): Unit.MPS,
    ('kilometer/hour', 'km/h', 'kilometer/h', 'km/hour', 'kmh'): Unit.KMH,
    ('foot/second', 'feet/second', 'ft/s', 'foot/s', 'feet/s', 'ft/second', 'fps'): Unit.FPS,
    ('mile/hour', 'mi/h', 'mile/h', 'mi/hour', 'mph'): Unit.MPH,
    ('knot', 'kn', 'kt'): Unit.KT,

    ('grain', 'gr', 'grn'): Unit.Grain,
    ('ounce', 'oz'): Unit.Ounce,
    ('gram', 'g'): Unit.Gram,
    ('pound', 'lb'): Unit.Pound,
    ('kilogram', 'kilogramme', 'kg'): Unit.Kilogram,
    ('newton', 'N'): Unit.Newton,

    ('minute', 'min'): Unit.Minute,
    ('second', 's', 'sec'): Unit.Second,
    ('millisecond', 'ms'): Unit.Millisecond,
    ('microsecond', 'us', 'µs'): Unit.Microsecond,
    ('nanosecond', 'ns'): Unit.Nanosecond,
    ('picosecond', 'ps'): Unit.Picosecond,
}


@runtime_checkable
class Measurable(SupportsFloat, SupportsInt, Hashable, Comparable, Protocol):
    _value: Number
    _defined_units: Unit
    __slots__ = ('_value', '_defined_units')

    def __init__(self, value: Number, units: Unit): ...

    def __str__(self) -> str: ...

    def __repr__(self) -> str: ...

    def __rshift__(self, units: Unit) -> Number: ...

    def __lshift__(self, units: Unit) -> Self: ...

    def __rlshift__(self, units: Unit) -> Self: ...

    def _validate_unit_type(self, value: Number, units: Unit): ...

    def to_raw(self, value: Number, units: Unit) -> Number: ...

    def from_raw(self, value: Number, units: Unit) -> Number: ...

    def convert(self, units: Unit) -> Self: ...

    def get_in(self, units: Unit) -> Number: ...

    @property
    def units(self) -> Unit: ...

    @property
    def unit_value(self) -> Number: ...

    @property
    def raw_value(self) -> Number: ...


class GenericDimension(Generic[_GenericDimensionType]):
    """Abstract base class for typed unit dimensions.

    This class provides the foundation for all unit measurements in the ballistic
    calculation system. Each dimension (Distance, Velocity, Angular, etc.) inherits
    from this class and defines its own conversion factors and raw unit representation.

    Attributes:
        _value: Internal value stored in the dimension's raw unit.
        _defined_units: The unit type this instance was created with.
        _conversion_factors: Mapping of units to their conversion factors.

    Examples:
        >>> # Subclasses define their own conversion factors
        >>> class Distance(GenericDimension):
        ...     _conversion_factors = {Unit.Meter: 39.3701, Unit.Yard: 36.0}
        
        >>> # Create and convert measurements
        >>> meters = Distance(100, Unit.Meter)
        >>> yards = meters.convert(Unit.Yard)
        >>> print(f"100m = {yards.unit_value:.1f} yards")
    """
    _value: Number
    _defined_units: Unit
    __slots__ = ('_value', '_defined_units')
    _conversion_factors: Mapping[Unit, float] = {}

    def __init__(self, value: Number, units: Unit):
        """Initialize a unit measurement with value and unit type.

        Args:
            value: Numeric value of the measurement in the specified units.
            units: Unit enum specifying the unit type for the value.
        """
        self._value: Number = self.__class__.to_raw(value, units)
        self._defined_units: Unit = units

    def __str__(self) -> str:
        """Human-readable string representation of the unit measurement.

        Returns:
            Formatted string showing the value rounded to appropriate precision
            followed by the unit symbol (e.g., "100.0m", "2800ft/s").

        Note:
            The precision is determined by the unit's `accuracy` property defined in UnitPropsDict.
        """
        units = self._defined_units
        props = UnitPropsDict[units]
        v = self.from_raw(self._value, units)
        return f'{round(v, props.accuracy)}{props.symbol}'

    def __repr__(self) -> str:
        """Detailed string representation for debugging.

        Returns:
            String showing class name, formatted unit value, and raw internal value
            (e.g., "<Distance: 100.0m (3937.01)>").
        """
        return f'<{self.__class__.__name__}: {self << self.units} ({round(self._value, 4)})>'

    def __float__(self) -> float:
        return float(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __eq__(self, other) -> bool:
        return float(self) == other

    def __hash__(self) -> int:
        return hash((self._value, self._defined_units))

    def __lt__(self, other) -> bool:
        return float(self) < other

    def __gt__(self, other) -> bool:
        return float(self) > other

    def __le__(self, other) -> bool:
        return float(self) <= other

    def __ge__(self, other) -> bool:
        return float(self) >= other

    @classmethod
    def _validate_unit_type(cls, units: Unit):
        """Validate that units are compatible with this dimension.

        Args:
            units: Unit type to validate.

        Raises:
            UnitConversionError: If the unit is not supported by this dimension.

        Note:
            Checks that the unit exists in this dimension's conversion factors.
        """
        if not isinstance(units, Unit):
            err_msg = f"Type expected: {Unit}, {type(Unit).__name__}; got: {type(units).__name__} ({units})"
            raise TypeError(err_msg)
        if units not in cls._conversion_factors.keys():
            raise UnitConversionError(f'{cls.__name__}: unit {units} is not supported')
        return

    @classmethod
    def _get_conversion_factor(cls, unit: Unit) -> float:
        return cls._conversion_factors[unit]

    @classmethod
    def new_from_raw(cls, raw_value: float, to_units: Unit) -> Self:
        """Create a new instance from a raw value in base units.

        Args:
            raw_value: Value in the dimension's raw unit (e.g., inches for Distance).
            to_units: Target unit type for the new instance.

        Returns:
            New instance with the raw value converted to the specified units.
        """
        value_in_units = raw_value / cls._get_conversion_factor(to_units)
        return cls(value_in_units, to_units)

    @classmethod
    def from_raw(cls, raw_value: float, unit: Unit) -> Number:
        """Convert a raw value to the specified units.

        Args:
            raw_value: Value in the dimension's raw unit.
            unit: Target unit type for conversion.

        Returns:
            Numeric value converted to the specified units.

        Note:
            Static conversion method that doesn't create a unit instance.
        """
        cls._validate_unit_type(unit)
        return raw_value / cls._get_conversion_factor(unit)
        
    @classmethod
    def to_raw(cls, value: Number, units: Unit) -> Number:
        """Convert a value in specified units to the raw unit.

        Args:
            value: Numeric value to convert.
            units: Unit type of the input value.

        Returns:
            Value converted to the dimension's raw unit.

        Note:
            Used internally for storing values in consistent raw units.
        """
        cls._validate_unit_type(units)
        return value * cls._get_conversion_factor(units)

    def convert(self, units: Unit) -> Self:
        """Convert this measurement to different units within the same dimension.

        Args:
            units: Target unit type for conversion.

        Returns:
            New instance of the same dimension type with value in target units.

        Raises:
            UnitConversionError: If target units are incompatible with this dimension.

        Examples:
            >>> distance = Distance(100, Distance.Meter)
            >>> yards = distance.convert(Distance.Yard)
            >>> print(f"100m = {yards}")  # 100m = 109.4yd
        """
        self._defined_units = units
        return self

    def get_in(self, units: Unit) -> Number:
        """Get the numeric value of this measurement in specified units.

        Args:
            units: Target unit type for the value.

        Returns:
            Numeric value in the specified units (float or int).

        Raises:
            UnitConversionError: If target units are incompatible with this dimension.

        Examples:
            >>> distance = Distance(100, Distance.Meter)
            >>> yard_value = distance.get_in(Distance.Yard)
            >>> print(f"100m = {yard_value:.1f} yards")  # 100m = 109.4 yards
        """
        return self.__class__.from_raw(self._value, units)

    @property
    def units(self) -> Unit:
        """Get the unit type this dimension instance was defined with.

        Returns:
            Unit enum representing the unit type of this measurement.
        """
        return self._defined_units

    @property
    def unit_value(self) -> Number:
        """Get the numeric value in the defined units.

        Returns:
            Numeric value in the units this measurement was created with.

        Note:
            Equivalent to get_in(self.units) but more efficient as a property.
        """
        return self.get_in(self.units)

    @property
    def raw_value(self) -> Number:
        """Get the internal raw value used for calculations.

        Returns:
            Numeric value in the dimension's raw unit (e.g., inches for Distance).
        """
        return self._value

    # aliases more efficient than wrappers
    __rshift__ = get_in
    __rlshift__ = convert
    __lshift__ = convert


class Distance(GenericDimension):
    """Distance measurements.  Raw value is inches."""

    _conversion_factors = {
        Unit.Inch: 1.,
        Unit.Foot: 12.,
        Unit.Yard: 36.,
        Unit.Mile: 63_360.,
        Unit.NauticalMile: 72_913.3858,
        Unit.Line: 0.1,
        Unit.Millimeter: 1. / 25.4,
        Unit.Centimeter: 10. / 25.4,
        Unit.Meter: 1_000. / 25.4,
        Unit.Kilometer: 1_000_000. / 25.4
    }

    @property
    def _inch(self) -> Number:
        """Shortcut for `>> Distance.Inch`"""
        return self._value

    @property
    def _feet(self) -> Number:
        """Shortcut for `>> Distance.Foot`"""
        return self._value / 12

    # Distance.* unit aliases
    Inch: Final[Unit] = Unit.Inch
    Foot: Final[Unit] = Unit.Foot
    Feet: Final[Unit] = Unit.Foot
    Yard: Final[Unit] = Unit.Yard
    Mile: Final[Unit] = Unit.Mile
    NauticalMile: Final[Unit] = Unit.NauticalMile
    Millimeter: Final[Unit] = Unit.Millimeter
    Centimeter: Final[Unit] = Unit.Centimeter
    Meter: Final[Unit] = Unit.Meter
    Kilometer: Final[Unit] = Unit.Kilometer
    Line: Final[Unit] = Unit.Line


class Pressure(GenericDimension):
    """Pressure unit.  Raw value is mmHg."""

    _conversion_factors = {
        Unit.MmHg: 1.,
        Unit.InHg: 25.4,
        Unit.Bar: 750.061683,
        Unit.hPa: 750.061683 / 1_000,
        Unit.PSI: 51.714924102396
    }

    # Pressure.* unit aliases
    MmHg: Final[Unit] = Unit.MmHg
    InHg: Final[Unit] = Unit.InHg
    Bar: Final[Unit] = Unit.Bar
    hPa: Final[Unit] = Unit.hPa
    PSI: Final[Unit] = Unit.PSI


class Weight(GenericDimension):
    """Weight unit.  Raw value is grains."""

    _conversion_factors = {
        Unit.Grain: 1.,
        Unit.Ounce: 437.5,
        Unit.Gram: 15.4323584,
        Unit.Pound: 7_000.,
        Unit.Kilogram: 15_432.3584,
        Unit.Newton: 1_573.662597
    }

    @property
    def _grain(self) -> Number:
        """Shortcut for `>> Weight.Grain`"""
        return self._value

    # Weight.* unit aliases
    Grain: Final[Unit] = Unit.Grain
    Ounce: Final[Unit] = Unit.Ounce
    Gram: Final[Unit] = Unit.Gram
    Pound: Final[Unit] = Unit.Pound
    Kilogram: Final[Unit] = Unit.Kilogram
    Newton: Final[Unit] = Unit.Newton


class Temperature(GenericDimension):
    """Temperature unit.  Raw value is Fahrenheit."""

    _conversion_factors = {
        Unit.Fahrenheit: 0.,
        Unit.Rankin: 0.,
        Unit.Celsius: 0.,
        Unit.Kelvin: 0.
    }

    @property
    def _F(self) -> Number:
        """Shortcut for `>> Temperature.Fahrenheit`"""
        return self._value

    @override
    @classmethod
    def to_raw(cls, value: Number, units: Unit) -> Number:
        if units == Temperature.Fahrenheit:
            return value
        if units == Temperature.Rankin:
            result = value - 459.67
        elif units == Temperature.Celsius:
            result = value * 9. / 5 + 32
        elif units == Temperature.Kelvin:
            result = (value - 273.15) * 9. / 5 + 32
        else:
            raise UnitConversionError(f"Temperature does not support {units}")
        return result

    @override
    @classmethod
    def from_raw(cls, raw_value: Number, unit: Unit) -> Number:
        if unit == Temperature.Fahrenheit:
            return raw_value
        if unit == Temperature.Rankin:
            result = raw_value + 459.67
        elif unit == Temperature.Celsius:
            result = (raw_value - 32) * 5. / 9
        elif unit == Temperature.Kelvin:
            result = (raw_value - 32) * 5. / 9 + 273.15
        else:
            raise UnitConversionError(f"Temperature does not support {unit}")
        return result

    # Temperature.* unit aliases
    Fahrenheit: Final[Unit] = Unit.Fahrenheit
    Celsius: Final[Unit] = Unit.Celsius
    Kelvin: Final[Unit] = Unit.Kelvin
    Rankin: Final[Unit] = Unit.Rankin


class Angular(GenericDimension):
    """Angular measurements.  Raw value is radians."""

    _conversion_factors = {
        Unit.Radian: 1.,
        Unit.Degree: pi / 180,
        Unit.MOA: pi / (60 * 180),
        Unit.Mil: pi / 3_200,
        Unit.MRad: 1. / 1_000,
        Unit.Thousandth: pi / 3_000,
        Unit.InchesPer100Yd: 1. / 3_600,
        Unit.CmPer100m: 1. / 10_000,
        Unit.OClock: pi / 6,
    }

    @property
    def _rad(self):
        """Shortcut for `>> Angular.Radian`"""
        return self._value

    @override
    @classmethod
    def to_raw(cls, value: Number, units: Unit) -> Number:
        """Avoid going in circles: Truncates to [0, 2π)"""
        radians = super().to_raw(value, units)
        if radians > 2. * pi:
            radians = radians % (2. * pi)
        return radians

    # Angular.* unit aliases
    Radian: Final[Unit] = Unit.Radian
    Degree: Final[Unit] = Unit.Degree
    MOA: Final[Unit] = Unit.MOA
    Mil: Final[Unit] = Unit.Mil
    MRad: Final[Unit] = Unit.MRad
    Thousandth: Final[Unit] = Unit.Thousandth
    InchesPer100Yd: Final[Unit] = Unit.InchesPer100Yd
    CmPer100m: Final[Unit] = Unit.CmPer100m
    OClock: Final[Unit] = Unit.OClock


class Velocity(GenericDimension):
    """Velocity measurements.  Raw unit is meters per second."""

    _conversion_factors = {
        Unit.MPS: 1.,
        Unit.KMH: 1. / 3.6,
        Unit.FPS: 1. / 3.2808399,
        Unit.MPH: 1. / 2.23693629,
        Unit.KT: 1. / 1.94384449,
    }

    @property
    def _fps(self) -> Number:
        """Shortcut for `>> Velocity.FPS`"""
        return self._value * 3.2808399

    # Velocity.* unit aliases
    MPS: Final[Unit] = Unit.MPS
    KMH: Final[Unit] = Unit.KMH
    FPS: Final[Unit] = Unit.FPS
    MPH: Final[Unit] = Unit.MPH
    KT: Final[Unit] = Unit.KT


class Energy(GenericDimension):
    """Energy measurements.  Raw unit is foot-pounds."""

    _conversion_factors = {
        Unit.FootPound: 1.,
        Unit.Joule: 1.3558179483314,
    }

    # Energy.* unit aliases
    FootPound: Final = Unit.FootPound
    Joule: Final = Unit.Joule


class Time(GenericDimension):
    """Time measurements.  Raw unit is seconds."""

    _conversion_factors = {
        Unit.Second: 1.,
        Unit.Minute: 1. / 60,
        Unit.Millisecond: 1. / 1_000,
        Unit.Microsecond: 1. / 1_000_000,
        Unit.Nanosecond: 1. / 1_000_000_000,
        Unit.Picosecond: 1. / 1_000_000_000_000,
    }

    @property
    def _seconds(self) -> Number:
        """Shortcut for `>> Time.Second`"""
        return self._value

    # Time.* unit aliases
    Minute: Final[Unit] = Unit.Minute
    Second: Final[Unit] = Unit.Second
    Millisecond: Final[Unit] = Unit.Millisecond
    Microsecond: Final[Unit] = Unit.Microsecond
    Nanosecond: Final[Unit] = Unit.Nanosecond
    Picosecond: Final[Unit] = Unit.Picosecond


class PreferredUnitsMeta(type):
    """Provide representation method for static dataclasses."""
    def __repr__(cls):
        return '\n'.join(f'{field} = {getattr(cls, field)!r}'
                         for field in getattr(cls, '__dataclass_fields__'))


@dataclass
class PreferredUnits(metaclass=PreferredUnitsMeta):  # pylint: disable=too-many-instance-attributes
    """Configuration class for default units used throughout ballistic calculations.

    This class defines the default units that will be used when creating measurements
    without explicitly specifying units, and for displaying results in user interfaces.
    It provides a centralized way to configure unit preferences for an entire ballistic
    calculation session. This allows users to set their preferred unit system once and
    have it apply to all subsequent calculations.

    Default Configuration:
        * angular: Degree (for look-angle and barrel elevation)
        * distance: Yard (traditional ballistic range unit)
        * velocity: FPS (feet per second)
        * pressure: InHg (inches of mercury, for barometric pressure)
        * temperature: Fahrenheit
        * diameter: Inch (bullet and bore diameter)
        * length: Inch (bullet length, barrel length)
        * weight: Grain (bullet weight, powder charge)
        * adjustment: Mil (scope adjustment increments)
        * drop: Inch (trajectory vertical measurements)
        * energy: FootPound (kinetic energy)
        * ogw: Pound (optimal game weight)
        * sight_height: Inch (scope height above bore)
        * target_height: Inch (target dimensions)
        * twist: Inch (barrel twist rate)
        * time: Second (flight time)

    Examples:
        >>> # Set metric preferences
        >>> PreferredUnits.distance = Unit.Meter
        >>> PreferredUnits.velocity = Unit.MPS
        
        >>> # Reset to defaults
        >>> PreferredUnits.restore_defaults()
        
        >>> # Bulk configuration
        >>> PreferredUnits.set(
        ...     distance='meter',
        ...     velocity='mps',
        ...     temperature='celsius'
        ... )

    Note:
        Changing preferred units affects all subsequent unit creation and display.
    """
    # Defaults
    angular: Unit = Unit.Degree
    distance: Unit = Unit.Yard
    velocity: Unit = Unit.FPS
    pressure: Unit = Unit.InHg
    temperature: Unit = Unit.Fahrenheit
    diameter: Unit = Unit.Inch
    length: Unit = Unit.Inch
    weight: Unit = Unit.Grain
    adjustment: Unit = Unit.Mil
    drop: Unit = Unit.Inch
    energy: Unit = Unit.FootPound
    ogw: Unit = Unit.Pound
    sight_height: Unit = Unit.Inch
    target_height: Unit = Unit.Inch
    twist: Unit = Unit.Inch
    time: Unit = Unit.Second

    @classmethod
    def restore_defaults(cls):
        """Reset all preferred units to their default values.

        Examples:
            >>> # Changing default distance units:
            >>> PreferredUnits.distance = Unit.Meter
            >>> # Reset to defaults
            >>> PreferredUnits.restore_defaults()
            >>> PreferredUnits.distance
            yard
        """
        for f in fields(cls):
            if f.default is not MISSING:
                setattr(cls, f.name, f.default)
            elif getattr(f, "default_factory", MISSING) is not MISSING:
                setattr(cls, f.name, f.default_factory())

    @classmethod
    def set(cls, **kwargs):
        """Set preferred units from keyword arguments.

        Allows bulk configuration of preferred units using either Unit enum values or string aliases.
        Invalid attributes or values are logged as warnings but do not raise exceptions.

        Args:
            **kwargs: Keyword arguments where keys are attribute names and values
                      are either Unit enum values or (string) UnitAliases.

        Examples:
            >>> # Set using Unit enums
            >>> PreferredUnits.set(
            ...     distance=Unit.Meter,
            ...     velocity=Unit.MPS,
            ...     temperature=Unit.Celsius
            ... )
            
            >>> # Set using string aliases
            >>> PreferredUnits.set(
            ...     distance='meter',
            ...     velocity='mps',
            ...     weight='gram'
            ... )
            
            >>> # Mixed types
            >>> PreferredUnits.set(
            ...     distance=Unit.Yard,
            ...     velocity='fps',
            ...     adjustment='mil'
            ... )
        """
        for attribute, value in kwargs.items():
            if hasattr(PreferredUnits, attribute):
                if isinstance(value, Unit):
                    setattr(PreferredUnits, attribute, value)
                elif isinstance(value, str):
                    if _unit := _parse_unit(value):
                        setattr(PreferredUnits, attribute, _unit)
                    else:
                        logger.warning(f"{value=} not a member of Unit")
                elif isinstance(value, bool):
                    setattr(PreferredUnits, attribute, value)
                else:
                    logger.warning(f"type of {value=} have not been converted to a member of Unit")
            else:
                logger.warning(f"{attribute=} not found in preferred_units")


def _find_unit_by_alias(string_to_find: str, aliases: UnitAliasesType) -> Optional[Unit]:
    """Find a unit type by searching through a dictionary that maps strings to Units.

    Args:
        string_to_find: String to search for in the alias mappings.
        aliases: Dictionary mapping alias tuples to Unit enum values.

    Returns:
        Unit enum if a match is found, None otherwise.
    """
    # Iterate over the keys of the dictionary
    for aliases_tuple in aliases.keys():
        # Check if the string is present in any of the tuples
        # if any(string_to_find in alias for alias in aliases_tuple):
        if string_to_find in (each.lower() for each in aliases_tuple):
            return aliases[aliases_tuple]
    return None  # If not found, return None or handle it as needed


def _parse_unit(input_: str) -> Union[Unit, None, Any]:
    """Parse a unit type from a string representation.

    Attempts to parse a string into a Unit enum using multiple methods:
    1. Check if it's a preferred unit attribute name
    2. Try direct Unit enum lookup
    3. Search through UnitAliases

    Args:
        input_: String representation of a unit to parse.

    Returns:
        Unit enum if parsing succeeds, None if no match found.

    Raises:
        TypeError: If input is not a string.

    Examples:
        >>> _parse_unit('meter')  # Unit.Meter
        >>> _parse_unit('m')      # Unit.Meter  
        >>> _parse_unit('fps')    # Unit.FPS
        >>> _parse_unit('MOA')    # Unit.MOA
    """
    input_ = input_.strip().lower()
    if not isinstance(input_, str):
        raise TypeError(f"type str expected for 'input_', got {type(input_)}")
    if hasattr(PreferredUnits, input_):
        return getattr(PreferredUnits, input_)
    try:
        return Unit[input_]
    except KeyError:
        return _find_unit_by_alias(input_, UnitAliases)


def _parse_value(input_: Union[str, Number],
                 preferred: Optional[Union[Unit, str]]) -> Optional[Union[GenericDimension[Any], Any, Unit]]:
    """Parse a value with optional unit specification into a unit measurement.

    Args:
        input_: Value to parse - can be a number or string with optional unit.
        preferred: Preferred unit to use for numeric inputs, either as Unit enum or string alias.

    Returns:
        Parsed unit measurement if successful, raises exception on failure.

    Raises:
        TypeError: If input type is not supported.
        UnitAliasError: If unit alias cannot be parsed.

    Examples:
        >>> # Parse numeric value with preferred unit
        >>> _parse_value(100, Unit.Meter)  # Distance(100, Unit.Meter)
        
        >>> # Parse string with embedded unit
        >>> _parse_value('100m', None)     # Distance(100, Unit.Meter)
        >>> _parse_value('2800fps', None)  # Velocity(2800, Unit.FPS)
        
        >>> # Parse with string preferred unit
        >>> _parse_value(50, 'grain')      # Weight(50, Unit.Grain)
    """

    def create_as_preferred(value_):
        if isinstance(preferred, Unit):
            return preferred(float(value_))
        if isinstance(preferred, str):
            if units_ := _parse_unit(preferred):
                return units_(float(value_))
        raise UnitAliasError(f"Unsupported {preferred=} unit alias")

    if isinstance(input_, (float, int)):
        return create_as_preferred(input_)

    if not isinstance(input_, str):
        raise TypeError(f"type, [str, float, int] expected for 'input_', got {type(input_)}")

    input_string = input_.replace(" ", "")
    if match := re.match(r'^-?(?:\d+\.\d*|\.\d+|\d+\.?)$', input_string):
        value = match.group()
        return create_as_preferred(value)

    if match := re.match(r'(^-?(?:\d+\.\d*|\.\d+|\d+\.?))(.*$)', input_string):
        value, alias = match.groups()
        if units := _parse_unit(alias):
            return units(float(value))
        raise UnitAliasError(f"Unsupported unit {alias=}")

    raise UnitAliasError(f"Can't parse unit {input_=}")


__all__ = (
    'Unit',
    'counter',
    'iterator',
    'Measurable',
    'GenericDimension',
    'UnitProps',
    'UnitAliases',
    'UnitPropsDict',
    'Distance',
    'Velocity',
    'Angular',
    'Temperature',
    'Pressure',
    'Energy',
    'Weight',
    'Time',
    'PreferredUnits',
    'UnitAliasError',
    'UnitTypeError',
    'UnitConversionError',
    '_parse_unit',
    '_parse_value'
)
