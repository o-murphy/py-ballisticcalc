"""
Use-full types for units of measurement conversion for ballistics calculations
"""

import typing
from enum import IntEnum
from math import pi, atan, tan
from typing import NamedTuple
from dataclasses import dataclass

__all__ = ('Unit', 'AbstractUnit', 'UnitPropsDict', 'Distance',
           'Velocity', 'Angular', 'Temperature', 'Pressure',
           'Energy', 'Weight', 'TypedUnits')


class Unit(IntEnum):
    """
    Usage of IntEnum simplify data serializing for using it with databases etc.
    """
    RAD = 0
    DEGREE = 1
    MOA = 2
    MIL = 3
    MRAD = 4
    THOUSAND = 5
    INCHES_PER_100YD = 6
    CM_PER_100M = 7
    H_O_CLOCK = 8

    INCH = 10
    FOOT = 11
    YARD = 12
    MILE = 13
    NAUTICAL_MILE = 14
    MILLIMETER = 15
    CENTIMETER = 16
    METER = 17
    KILOMETER = 18
    LINE = 19

    FOOT_POUND = 30
    JOULE = 31

    MM_HG = 40
    IN_HG = 41
    BAR = 42
    HP = 43
    PSI = 44

    FAHRENHEIT = 50
    CELSIUS = 51
    KELVIN = 52
    RANKIN = 53

    MPS = 60
    KMH = 61
    FPS = 62
    MPH = 63
    KT = 64

    GRAIN = 70
    OUNCE = 71
    GRAM = 72
    POUND = 73
    KILOGRAM = 74
    NEWTON = 75

    @property
    def key(self) -> str:
        """
        :rtype: str
        :return: readable name of the unit of measure
        """
        return UnitPropsDict[self].name

    @property
    def accuracy(self) -> int:
        """
        :rtype: int
        :return: default accuracy of the unit of measure
        """
        return UnitPropsDict[self].accuracy

    @property
    def symbol(self):
        """
        :rtype: str
        :return: short symbol of the unit of measure in CI
        """
        return UnitPropsDict[self].symbol

    def __call__(self: 'Unit', value: [int, float, 'AbstractUnit']) -> 'AbstractUnit':
        """Creates new unit instance by dot syntax
        :param self: unit as Unit enum
        :param value: numeric value of the unit
        :return: AbstractUnit instance
        """
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
            raise TypeError(f"{self} Unit is not supports")
        return obj


class UnitProps(NamedTuple):
    """Properties of unit measure"""
    name: str
    accuracy: int
    symbol: str


UnitPropsDict = {
    Unit.RAD: UnitProps('radian', 6, 'rad'),
    Unit.DEGREE: UnitProps('degree', 4, '°'),
    Unit.MOA: UnitProps('MOA', 2, 'MOA'),
    Unit.MIL: UnitProps('MIL', 2, 'MIL'),
    Unit.MRAD: UnitProps('MRAD', 2, 'MRAD'),
    Unit.THOUSAND: UnitProps('thousand', 2, 'ths'),
    Unit.INCHES_PER_100YD: UnitProps('inches/100yd', 2, 'in/100yd'),
    Unit.CM_PER_100M: UnitProps('cm/100m', 2, 'cm/100m'),
    Unit.H_O_CLOCK: UnitProps('hour', 2, 'h'),

    Unit.INCH: UnitProps("inch", 3, "inch"),
    Unit.FOOT: UnitProps("foot", 2, "ft"),
    Unit.YARD: UnitProps("yard", 3, "yd"),
    Unit.MILE: UnitProps("mile", 3, "mi"),
    Unit.NAUTICAL_MILE: UnitProps("nautical mile", 3, "nm"),
    Unit.MILLIMETER: UnitProps("millimeter", 3, "mm"),
    Unit.CENTIMETER: UnitProps("centimeter", 3, "cm"),
    Unit.METER: UnitProps("meter", 3, "m"),
    Unit.KILOMETER: UnitProps("kilometer", 3, "km"),
    Unit.LINE: UnitProps("line", 3, "ln"),

    Unit.FOOT_POUND: UnitProps('foot * pound', 0, 'ft·lb'),
    Unit.JOULE: UnitProps('joule', 0, 'J'),

    Unit.MM_HG: UnitProps('mmHg', 0, 'mmHg'),
    Unit.IN_HG: UnitProps('inHg', 6, 'inHg'),
    Unit.BAR: UnitProps('bar', 2, 'bar'),
    Unit.HP: UnitProps('hPa', 4, 'hPa'),
    Unit.PSI: UnitProps('psi', 4, 'psi'),

    Unit.FAHRENHEIT: UnitProps('fahrenheit', 1, '°F'),
    Unit.CELSIUS: UnitProps('celsius', 1, '°C'),
    Unit.KELVIN: UnitProps('kelvin', 1, '°K'),
    Unit.RANKIN: UnitProps('rankin', 1, '°R'),

    Unit.MPS: UnitProps('mps', 0, 'm/s'),
    Unit.KMH: UnitProps('kmh', 1, 'km/h'),
    Unit.FPS: UnitProps('fps', 1, 'ft/s'),
    Unit.MPH: UnitProps('mph', 1, 'mph'),
    Unit.KT: UnitProps('knots', 1, 'kt'),

    Unit.GRAIN: UnitProps('grain', 1, 'gr'),
    Unit.OUNCE: UnitProps('ounce', 1, 'oz'),
    Unit.GRAM: UnitProps('gram', 1, 'g'),
    Unit.POUND: UnitProps('pound', 3, 'lb'),
    Unit.KILOGRAM: UnitProps('kilogram', 3, 'kg'),
    Unit.NEWTON: UnitProps('newton', 3, 'N'),
}


class AbstractUnit:
    """Abstract class for unit of measure instance definition
    Stores defined unit and value, applies conversions to other units
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
        """Returns readable unit value
        :return: readable unit value
        """
        units = self._defined_units
        props = UnitPropsDict[units]
        v = self.from_raw(self._value, units)
        return f'{round(v, props.accuracy)}{props.symbol}'

    def __repr__(self):
        """Returns instance as readable view
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

    def _unit_support_error(self, value: float, units: Unit):
        """Validates the units
        :param value: value of the unit
        :param units: Unit enum type
        :return: value in specified units
        """
        if not isinstance(units, Unit):
            err_msg = f"Type expected: {Unit}, {type(Unit).__name__} " \
                      f"found: {type(units).__name__} ({value})"
            raise TypeError(err_msg)
        if units not in self.__dict__.values():
            raise ValueError(f'{self.__class__.__name__}: unit {units} is not supported')
        return 0

    def to_raw(self, value: float, units: Unit) -> float:
        """Converts value with specified units to raw value
        :param value: value of the unit
        :param units: Unit enum type
        :return: value in specified units
        """
        return self._unit_support_error(value, units)

    def from_raw(self, value: float, units: Unit) -> float:
        """Converts raw value to specified units
        :param value: raw value of the unit
        :param units: Unit enum type
        :return: value in specified units
        """
        return self._unit_support_error(value, units)

    def convert(self, units: Unit) -> 'AbstractUnit':
        """Returns new unit instance in specified units
        :param units: Unit enum type
        :return: new unit instance in specified units
        """
        value = self.get_in(units)
        return self.__class__(value, units)

    def get_in(self, units: Unit) -> float:
        """Returns value in specified units
        :param units: Unit enum type
        :return: value in specified units
        """
        return self.from_raw(self._value, units)

    @property
    def units(self) -> Unit:
        """Returns defined units
        :return: defined units
        """
        return self._defined_units

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

    Inch = Unit.INCH
    Foot = Unit.FOOT
    Yard = Unit.YARD
    Mile = Unit.MILE
    NauticalMile = Unit.NAUTICAL_MILE
    Millimeter = Unit.MILLIMETER
    Centimeter = Unit.CENTIMETER
    Meter = Unit.METER
    Kilometer = Unit.KILOMETER
    Line = Unit.LINE


class Pressure(AbstractUnit):
    """Pressure unit"""

    def to_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        if units == Pressure.InHg:
            result = value * 25.4
        elif units == Pressure.Bar:
            result = value * 750.061683
        elif units == Pressure.HP:
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
        elif units == Pressure.HP:
            result = value / 750.061683 * 1000
        elif units == Pressure.PSI:
            result = value / 51.714924102396
        else:
            return super().from_raw(value, units)
        return result

    MmHg = Unit.MM_HG
    InHg = Unit.IN_HG
    Bar = Unit.BAR
    HP = Unit.HP
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

    Grain = Unit.GRAIN
    Ounce = Unit.OUNCE
    Gram = Unit.GRAM
    Pound = Unit.POUND
    Kilogram = Unit.KILOGRAM
    Newton = Unit.NEWTON


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

    Fahrenheit = Unit.FAHRENHEIT
    Celsius = Unit.CELSIUS
    Kelvin = Unit.KELVIN
    Rankin = Unit.RANKIN


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
        elif units == Angular.Thousand:
            result = value / 3000 * pi
        elif units == Angular.InchesPer100Yd:
            result = atan(value / 3600)
        elif units == Angular.CmPer100M:
            result = atan(value / 10000)
        elif units == Angular.OClock:
            result = value / 6 * pi
        else:
            return super().to_raw(value, units)
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
        elif units == Angular.Thousand:
            result = value * 3000 / pi
        elif units == Angular.InchesPer100Yd:
            result = tan(value) * 3600
        elif units == Angular.CmPer100M:
            result = tan(value) * 10000
        elif units == Angular.OClock:
            result = value * 6 / pi
        else:
            return super().from_raw(value, units)
        return result

    Radian = Unit.RAD
    Degree = Unit.DEGREE
    MOA = Unit.MOA
    Mil = Unit.MIL
    MRad = Unit.MRAD
    Thousand = Unit.THOUSAND
    InchesPer100Yd = Unit.INCHES_PER_100YD
    CmPer100M = Unit.CM_PER_100M
    OClock = Unit.H_O_CLOCK


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

    FootPound = Unit.FOOT_POUND
    Joule = Unit.JOULE


@dataclass
class TypedUnits:  # pylint: disable=too-few-public-methods
    """
    Abstract class to apply auto-conversion values to
    specified units by type-hints in inherited dataclasses
    """

    def __setattr__(self, key, value):
        """
        converts value to specified units by type-hints in inherited dataclass
        """

        _fields = self.__getattribute__('__dataclass_fields__')
        # fields(self.__class__)[0].name
        if key in _fields and not isinstance(value, AbstractUnit):
            default_factory = _fields[key].default_factory
            if isinstance(default_factory, typing.Callable):
                if isinstance(value, Unit):
                    value = None
                else:
                    value = default_factory()(value)

        super().__setattr__(key, value)


# def is_unit(obj: [AbstractUnit, float, int]):
#     """
#     Check if obj is inherited by AbstractUnit
#     :return: False - if float or int
#     """
#     if isinstance(obj, AbstractUnit):
#         return True
#     if isinstance(obj, (float, int)):
#         return False
#     if obj is None:
#         return None
#     raise TypeError(f"Expected Unit, int, or float, found {obj.__class__.__name__}")


# Default units
# Angular.Radian
# Distance.Inch
# Energy.FootPound
# Weight.Grain
# Velocity.MPS
# Temperature.Fahrenheit
# Pressure.MmHg
