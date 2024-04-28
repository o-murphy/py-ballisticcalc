"""
Useful types for prefer_units of measurement conversion for ballistics calculations
"""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, MISSING, Field
from enum import IntEnum
from math import pi, atan, tan
from typing import NamedTuple, Union, TypeVar
import re

from py_ballisticcalc.logger import logger

__all__ = ('Unit', 'UnitType',
           'AbstractUnit', 'AbstractUnitType',
           'UnitProps', 'UnitAliases',
           'UnitPropsDict', 'Distance',
           'Velocity', 'Angular', 'Temperature', 'Pressure',
           'Energy', 'Weight', 'Dimension', 'PreferredUnits',
           'UnitAliasError', 'UnitTypeError', 'UnitConversionError')

UnitType = TypeVar('UnitType', bound='Unit')
AbstractUnitType = TypeVar('AbstractUnitType', bound='AbstractUnit')


class UnitTypeError(TypeError):
    pass


class UnitConversionError(UnitTypeError):
    pass


class UnitAliasError(ValueError):
    pass


# pylint: disable=invalid-name
class Unit(IntEnum):
    """
    Usage of IntEnum simplify data serializing for using it with databases etc.
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

    @property
    def key(self) -> str:
        """
        :return: readable name of the unit of measure
        """
        return UnitPropsDict[self].name

    @property
    def accuracy(self) -> int:
        """
        :return: default accuracy of the unit of measure
        """
        return UnitPropsDict[self].accuracy

    @property
    def symbol(self) -> str:
        """
        :return: short symbol of the unit of measure in CI
        """
        return UnitPropsDict[self].symbol

    def __repr__(self) -> str:
        return UnitPropsDict[self].name

    def __call__(self: UnitType, value: [int, float, AbstractUnitType] = None) -> AbstractUnitType:
        """Creates new unit instance by dot syntax
        :param self: unit as Unit enum
        :param value: numeric value of the unit
        :return: AbstractUnit instance
        """

        # if value is None:
        #     return self

        if isinstance(value, AbstractUnit):
            return value << self
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
        else:
            raise UnitTypeError(f"{self} Unit is not supported")
        return obj

    @staticmethod
    def find_unit_by_alias(string_to_find, aliases):
        # Iterate over the keys of the dictionary
        for aliases_tuple in aliases.keys():
            # Check if the string is present in any of the tuples
            # if any(string_to_find in alias for alias in aliases_tuple):
            if string_to_find in (each.lower() for each in aliases_tuple):
                return aliases[aliases_tuple]
        return None  # If not found, return None or handle it as needed

    @staticmethod
    def parse_unit(input_: str) -> UnitType:
        input_ = input_.strip().lower()
        if not isinstance(input_, str):
            raise TypeError(f"type str expected for 'input_', got {type(input_)}")
        if hasattr(PreferredUnits, input_):
            return getattr(PreferredUnits, input_)
        try:
            return Unit[input_]
        except KeyError:
            return Unit.find_unit_by_alias(input_, UnitAliases)

    @staticmethod
    def parse_value(input_: [str, float, int], preferred: [UnitType, str]) -> AbstractUnitType:

        def create_as_preferred(value):
            if isinstance(preferred, Unit):
                return preferred(float(value))
            if isinstance(preferred, str):
                if units := Unit.parse_unit(preferred):
                    return units(float(value))
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
            if units := Unit.parse_unit(alias):
                return units(float(value))
            else:
                raise UnitAliasError(f"Unsupported unit {alias=}")

        raise UnitAliasError(f"Can't parse unit {input_=}")


class UnitProps(NamedTuple):
    """Properties of unit measure"""
    name: str
    accuracy: int
    symbol: str


UnitPropsDict = {
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
}

UnitAliases = {
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
    ('foot', 'ft'): Unit.Foot,
    ('yard', 'yd'): Unit.Yard,
    ('mile', 'mi', 'mi.'): Unit.Mile,
    ('nauticalmile', 'nm', 'nmi'): Unit.NauticalMile,
    ('millimeter', 'mm'): Unit.Millimeter,
    ('centimeter', 'cm'): Unit.Centimeter,
    ('meter', 'm'): Unit.Meter,
    ('kilometer', 'km'): Unit.Kilometer,
    ('line', 'ln', 'liniа'): Unit.Line,

    ('footpound', 'foot-pound', 'ft⋅lbf', 'ft⋅lbf', 'ft⋅lb',
     'foot*pound', 'ft*lbf', 'ft*lbf', 'ft*lb'): Unit.FootPound,
    ('joule', 'J'): Unit.Joule,

    ('mmHg',): Unit.MmHg,
    ('inHg', '″Hg'): Unit.InHg,
    ('bar',): Unit.Bar,
    ('hectopascal', 'hPa'): Unit.hPa,
    ('psi', 'lbf/in2'): Unit.PSI,

    ('fahrenheit', '°F', 'F', 'degF'): Unit.Fahrenheit,
    ('celsius', '°C', 'C', 'degC'): Unit.Celsius,
    ('kelvin', '°K', 'K', 'degK'): Unit.Kelvin,
    ('rankin', '°R', 'R', 'degR'): Unit.Rankin,

    ('meter/second', 'm/s', 'meter/s', 'm/second', 'mps'): Unit.MPS,
    ('kilometer/hour', 'km/h', 'kilometer/h', 'km/hour', 'kmh'): Unit.KMH,
    ('foot/second', 'ft/s', 'foot/s', 'ft/second', 'fps'): Unit.FPS,
    ('mile/hour', 'mi/h', 'mile/h', 'mi/hour', 'mph'): Unit.MPH,
    ('knot', 'kn', 'kt'): Unit.KT,

    ('grain', 'gr', 'grn'): Unit.Grain,
    ('ounce', 'oz'): Unit.Ounce,
    ('gram', 'g'): Unit.Gram,
    ('pound', 'lb'): Unit.Pound,
    ('kilogram', 'kilogramme', 'kg'): Unit.Kilogram,
    ('newton', 'N'): Unit.Kilogram,
}


class AbstractUnit:
    """Abstract class for unit of measure instance definition
    Stores defined unit and value, applies conversions to other prefer_units
    """
    __slots__ = ('_value', '_defined_units')

    def __init__(self, value: [float, int], units: Unit):
        """
        :param units: unit as Unit enum
        :param value: numeric value of the unit
        """
        self._value: float = self.to_raw(value, units)
        self._defined_units: Unit = units

    def __str__(self) -> str:
        """
        :return: readable unit value
        """
        units = self._defined_units
        props = UnitPropsDict[units]
        v = self.from_raw(self._value, units)
        return f'{round(v, props.accuracy)}{props.symbol}'

    def __repr__(self) -> str:
        """
        :return: instance as readable view
        """
        return f'<{self.__class__.__name__}: {self << self.units} ({round(self._value, 4)})>'

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        return float(self) == other

    def __lt__(self, other):
        return float(self) < other

    def __gt__(self, other):
        return float(self) > other

    def __le__(self, other):
        return float(self) <= other

    def __ge__(self, other):
        return float(self) >= other

    def __lshift__(self, other: Unit):
        return self.convert(other)

    def __rshift__(self, other: Unit):
        return self.get_in(other)

    def __rlshift__(self, other: Unit):
        return self.convert(other)

    def _validate_unit_type(self, value: float, units: Unit):
        """Validates the prefer_units
        :param value: value of the instance
        :param units: Unit enum type
        :return: value in specified prefer_units
        """
        if not isinstance(units, Unit):
            err_msg = f"Type expected: {Unit}, {type(Unit).__name__} " \
                      f"found: {type(units).__name__} ({value})"
            raise TypeError(err_msg)
        if units not in self.__dict__.values():
            raise UnitConversionError(f'{self.__class__.__name__}: unit {units} is not supported')
        return 0

    def to_raw(self, value: float, units: Unit) -> float:
        """Converts value with specified prefer_units to raw value
        :param value: value of the instance
        :param units: Unit enum type
        :return: value in specified prefer_units
        """
        return self._validate_unit_type(value, units)

    def from_raw(self, value: float, units: Unit) -> float:
        """Converts raw value to specified prefer_units
        :param value: raw value of the unit
        :param units: Unit enum type
        :return: value in specified prefer_units
        """
        return self._validate_unit_type(value, units)

    def convert(self, units: Unit) -> AbstractUnitType:
        """Returns new unit instance in specified prefer_units
        :param units: Unit enum type
        :return: new unit instance in specified prefer_units
        """
        value = self.get_in(units)
        return self.__class__(value, units)

    def get_in(self, units: Unit) -> float:
        """
        :param units: Unit enum type
        :return: value in specified prefer_units
        """
        return self.from_raw(self._value, units)

    @property
    def units(self) -> Unit:
        """
        :return: defined prefer_units
        """
        return self._defined_units

    @property
    def unit_value(self) -> float:
        """Returns float value in defined prefer_units"""
        return self.get_in(self.units)

    @property
    def raw_value(self) -> float:
        """Raw unit value getter
        :return: raw unit value
        """
        return self._value


class Distance(AbstractUnit):
    """Distance unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Distance.Inch:
            return value
        if units == Distance.Foot:
            result = value * 12
        elif units == Distance.Yard:
            result = value * 36
        elif units == Distance.Mile:
            result = value * 63360
        elif units == Distance.NauticalMile:
            result = value * 72913.3858
        elif units == Distance.Line:
            result = value / 10
        elif units == Distance.Millimeter:
            result = value / 25.4
        elif units == Distance.Centimeter:
            result = value / 2.54
        elif units == Distance.Meter:
            result = value / 25.4 * 1000
        elif units == Distance.Kilometer:
            result = value / 25.4 * 1000000
        else:
            return super().to_raw(value, units)
        return result

    def from_raw(self, value: float, units: Unit):
        if units == Distance.Inch:
            return value
        if units == Distance.Foot:
            result = value / 12
        elif units == Distance.Yard:
            result = value / 36
        elif units == Distance.Mile:
            result = value / 63360
        elif units == Distance.NauticalMile:
            result = value / 72913.3858
        elif units == Distance.Line:
            result = value * 10
        elif units == Distance.Millimeter:
            result = value * 25.4
        elif units == Distance.Centimeter:
            result = value * 2.54
        elif units == Distance.Meter:
            result = value * 25.4 / 1000
        elif units == Distance.Kilometer:
            result = value * 25.4 / 1000000
        else:
            return super().from_raw(value, units)
        return result

    Inch = Unit.Inch
    Foot = Unit.Foot
    Yard = Unit.Yard
    Mile = Unit.Mile
    NauticalMile = Unit.NauticalMile
    Millimeter = Unit.Millimeter
    Centimeter = Unit.Centimeter
    Meter = Unit.Meter
    Kilometer = Unit.Kilometer
    Line = Unit.Line


class Pressure(AbstractUnit):
    """Pressure unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        if units == Pressure.InHg:
            result = value * 25.4
        elif units == Pressure.Bar:
            result = value * 750.061683
        elif units == Pressure.hPa:
            result = value * 750.061683 / 1000
        elif units == Pressure.PSI:
            result = value * 51.714924102396
        else:
            return super().to_raw(value, units)
        return result

    def from_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        if units == Pressure.InHg:
            result = value / 25.4
        elif units == Pressure.Bar:
            result = value / 750.061683
        elif units == Pressure.hPa:
            result = value / 750.061683 * 1000
        elif units == Pressure.PSI:
            result = value / 51.714924102396
        else:
            return super().from_raw(value, units)
        return result

    MmHg = Unit.MmHg
    InHg = Unit.InHg
    Bar = Unit.Bar
    hPa = Unit.hPa
    PSI = Unit.PSI


class Weight(AbstractUnit):
    """Weight unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        if units == Weight.Gram:
            result = value * 15.4323584
        elif units == Weight.Kilogram:
            result = value * 15432.3584
        elif units == Weight.Newton:
            result = value * 151339.73750336
        elif units == Weight.Pound:
            result = value / 0.000142857143
        elif units == Weight.Ounce:
            result = value * 437.5
        else:
            return super().to_raw(value, units)
        return result

    def from_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        if units == Weight.Gram:
            result = value / 15.4323584
        elif units == Weight.Kilogram:
            result = value / 15432.3584
        elif units == Weight.Newton:
            result = value / 151339.73750336
        elif units == Weight.Pound:
            result = value * 0.000142857143
        elif units == Weight.Ounce:
            result = value / 437.5
        else:
            return super().from_raw(value, units)
        return result

    Grain = Unit.Grain
    Ounce = Unit.Ounce
    Gram = Unit.Gram
    Pound = Unit.Pound
    Kilogram = Unit.Kilogram
    Newton = Unit.Newton


class Temperature(AbstractUnit):
    """Temperature unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        if units == Temperature.Rankin:
            result = value - 459.67
        elif units == Temperature.Celsius:
            result = value * 9 / 5 + 32
        elif units == Temperature.Kelvin:
            result = (value - 273.15) * 9 / 5 + 32
        else:
            return super().to_raw(value, units)
        return result

    def from_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        if units == Temperature.Rankin:
            result = value + 459.67
        elif units == Temperature.Celsius:
            result = (value - 32) * 5 / 9
        elif units == Temperature.Kelvin:
            result = (value - 32) * 5 / 9 + 273.15
        else:
            return super().from_raw(value, units)
        return result

    Fahrenheit = Unit.Fahrenheit
    Celsius = Unit.Celsius
    Kelvin = Unit.Kelvin
    Rankin = Unit.Rankin


class Angular(AbstractUnit):
    """Angular unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        if units == Angular.Degree:
            result = value / 180 * pi
        elif units == Angular.MOA:
            result = value / 180 * pi / 60
        elif units == Angular.Mil:
            result = value / 3200 * pi
        elif units == Angular.MRad:
            result = value / 1000
        elif units == Angular.Thousandth:
            result = value / 3000 * pi
        elif units == Angular.InchesPer100Yd:
            result = atan(value / 3600)
        elif units == Angular.CmPer100m:
            result = atan(value / 10000)
        elif units == Angular.OClock:
            result = value / 6 * pi
        else:
            return super().to_raw(value, units)
        if result > 2 * pi:
            result = result % (2 * pi)
        return result

    def from_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        if units == Angular.Degree:
            result = value * 180 / pi
        elif units == Angular.MOA:
            result = value * 180 / pi * 60
        elif units == Angular.Mil:
            result = value * 3200 / pi
        elif units == Angular.MRad:
            result = value * 1000
        elif units == Angular.Thousandth:
            result = value * 3000 / pi
        elif units == Angular.InchesPer100Yd:
            result = tan(value) * 3600
        elif units == Angular.CmPer100m:
            result = tan(value) * 10000
        elif units == Angular.OClock:
            result = value * 6 / pi
        else:
            return super().from_raw(value, units)
        return result

    Radian = Unit.Radian
    Degree = Unit.Degree
    MOA = Unit.MOA
    Mil = Unit.Mil
    MRad = Unit.MRad
    Thousandth = Unit.Thousandth
    InchesPer100Yd = Unit.InchesPer100Yd
    CmPer100m = Unit.CmPer100m
    OClock = Unit.OClock


class Velocity(AbstractUnit):
    """Velocity unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Velocity.MPS:
            return value
        if units == Velocity.KMH:
            return value / 3.6
        if units == Velocity.FPS:
            return value / 3.2808399
        if units == Velocity.MPH:
            return value / 2.23693629
        if units == Velocity.KT:
            return value / 1.94384449
        return super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Velocity.MPS:
            return value
        if units == Velocity.KMH:
            return value * 3.6
        if units == Velocity.FPS:
            return value * 3.2808399
        if units == Velocity.MPH:
            return value * 2.23693629
        if units == Velocity.KT:
            return value * 1.94384449
        return super().from_raw(value, units)

    MPS = Unit.MPS
    KMH = Unit.KMH
    FPS = Unit.FPS
    MPH = Unit.MPH
    KT = Unit.KT


class Energy(AbstractUnit):
    """Energy unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        if units == Energy.Joule:
            return value * 0.737562149277
        return super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        if units == Energy.Joule:
            return value / 0.737562149277
        return super().from_raw(value, units)

    FootPound = Unit.FootPound
    Joule = Unit.Joule


class PreferredUnitsMeta(type):
    """Provide representation method for static dataclasses."""

    def __repr__(cls):
        return '\n'.join(f'{field} = {getattr(cls, field)!r}'
                         for field in getattr(cls, '__dataclass_fields__'))


@dataclass
class PreferredUnits(metaclass=PreferredUnitsMeta):  # pylint: disable=too-many-instance-attributes
    """Default prefer_units for specified measures"""

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

    @dataclass
    class Mixin(ABC):  # pylint: disable=too-few-public-methods
        """
        TODO: move it to Units, use it instead of TypedUnits
        Abstract class to apply auto-conversion values to
        specified prefer_units by type-hints in inherited dataclasses
        """

        def __setattr__(self, key, value):
            """
            converts value to specified prefer_units by type-hints in inherited dataclass
            """

            _fields = self.__getattribute__('__dataclass_fields__')

            if (_field := _fields.get(key)) and value is not None and not isinstance(value, AbstractUnit):

                if units := _field.metadata.get('prefer_units'):

                    if isinstance(units, Unit):
                        value = units(value)
                    elif isinstance(units, str):
                        if _units := Unit.parse_unit(units):
                            value = _units(value)
                        else:
                            raise UnitTypeError(f"Unsupported unit or dimension, use one of {PreferredUnits}")
                    else:
                        raise UnitTypeError(f"Unsupported unit or dimension, use one of {PreferredUnits}")

            super().__setattr__(key, value)

    @classmethod
    def defaults(self):
        """resets preferred units to defaults"""
        self.angular = Unit.Degree
        self.distance = Unit.Yard
        self.velocity = Unit.FPS
        self.pressure = Unit.InHg
        self.temperature = Unit.Fahrenheit
        self.diameter = Unit.Inch
        self.length = Unit.Inch
        self.weight = Unit.Grain
        self.adjustment = Unit.Mil
        self.drop = Unit.Inch
        self.energy = Unit.FootPound
        self.ogw = Unit.Pound
        self.sight_height = Unit.Inch
        self.target_height = Unit.Inch
        self.twist = Unit.Inch

    @classmethod
    def set(cls, **kwargs):
        """set preferred units from Mapping"""
        for attribute, value in kwargs.items():

            if hasattr(PreferredUnits, attribute):
                if isinstance(value, Unit):
                    setattr(PreferredUnits, attribute, value)
                elif isinstance(value, str):
                    if _unit := Unit.parse_unit(value):
                        setattr(PreferredUnits, attribute, _unit)
                    else:
                        logger.warning(f"{value=} not a member of Unit")
                else:
                    logger.warning(f"type of {value=} have not been converted to a member of Unit")
            else:
                logger.warning(f"{attribute=} not found in preferred_units")


# pylint: disable=redefined-builtin,too-few-public-methods,too-many-arguments
class Dimension(Field):
    """
    Definition of measure units specified field for
    PreferredUnits.Mixin based dataclasses
    """

    def __init__(self, prefer_units: Union[str, Unit], init=True, repr_=True,
                 hash_=None, compare=True, metadata=None):

        if metadata is None:
            metadata = {}
        metadata['prefer_units'] = prefer_units

        major, minor = sys.version_info.major, sys.version_info.minor

        if major >= 3 and minor > 9:
            extra = {'kw_only': MISSING}
        elif major >= 3 and minor == 9:
            extra = {}
        else:
            raise RuntimeError("Unsupported python version")

        super().__init__(default=None, default_factory=MISSING,
                         init=init, repr=repr_,
                         hash=hash_, compare=compare,
                         metadata=metadata, **extra)

    @property
    def raw_value(self):
        raise NotImplementedError

    @abstractmethod
    def __rshift__(self, other):
        ...

    @abstractmethod
    def __lshift__(self, other):
        ...
