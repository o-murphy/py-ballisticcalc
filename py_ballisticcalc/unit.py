from abc import ABC
from enum import IntEnum
from math import pi, atan, tan
from typing import NamedTuple


class Unit(IntEnum):
    """
    Usage of IntEnum simplify data serializing for using it with databases etc.
    """
    Radian = 0
    Degree = 1
    MOA = 2
    Mil = 3
    MRad = 4
    Thousand = 5
    InchesPer100Yd = 6
    CmPer100M = 7

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
    HP = 43
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
    def name(self):
        return UnitPropsDict[self].name

    @property
    def accuracy(self):
        return UnitPropsDict[self].accuracy

    @property
    def symbol(self):
        return UnitPropsDict[self].symbol


class UnitProps(NamedTuple):
    """
    Properties of unit measure
    """
    name: str
    accuracy: int
    symbol: str


UnitPropsDict = {
    Unit.Radian: UnitProps('radian', 6, 'rad'),
    Unit.Degree: UnitProps('degree', 4, '°'),
    Unit.MOA: UnitProps('moa', 2, 'moa'),
    Unit.Mil: UnitProps('mil', 2, 'mil'),
    Unit.MRad: UnitProps('mrad', 2, 'mrad'),
    Unit.Thousand: UnitProps('thousand', 2, 'ths'),
    Unit.InchesPer100Yd: UnitProps('inches/100yd', 2, 'in/100yd'),
    Unit.CmPer100M: UnitProps('cm/100m', 2, 'cm/100m'),

    Unit.Inch: UnitProps("inch", 1, "inch"),
    Unit.Foot: UnitProps("foot", 2, "ft"),
    Unit.Yard: UnitProps("yard", 3, "yd"),
    Unit.Mile: UnitProps("mile", 3, "mi"),
    Unit.NauticalMile: UnitProps("nautical mile", 3, "nm"),
    Unit.Millimeter: UnitProps("millimeter", 3, "mm"),
    Unit.Centimeter: UnitProps("centimeter", 3, "cm"),
    Unit.Meter: UnitProps("meter", 3, "m"),
    Unit.Kilometer: UnitProps("kilometer", 3, "km"),
    Unit.Line: UnitProps("line", 3, "ln"),

    Unit.FootPound: UnitProps('foot * pound', 0, 'ft·lb'),
    Unit.Joule: UnitProps('joule', 0, 'J'),

    Unit.MmHg: UnitProps('mmhg', 0, 'mmHg'),
    Unit.InHg: UnitProps('inhg', 6, '?'),
    Unit.Bar: UnitProps('bar', 2, 'bar'),
    Unit.HP: UnitProps('hp', 4, 'hPa'),
    Unit.PSI: UnitProps('psi', 4, 'psi'),

    Unit.Fahrenheit: UnitProps('fahrenheit', 1, '°F'),
    Unit.Celsius: UnitProps('celsius', 1, '°C'),
    Unit.Kelvin: UnitProps('kelvin', 1, '°K'),
    Unit.Rankin: UnitProps('rankin', 1, '°R'),

    Unit.MPS: UnitProps('mps', 0, 'm/s'),
    Unit.KMH: UnitProps('kmh', 1, 'km/h'),
    Unit.FPS: UnitProps('fps', 1, 'ft/s'),
    Unit.MPH: UnitProps('mph', 1, 'mph'),
    Unit.KT: UnitProps('kt', 1, 'kt'),

    Unit.Grain: UnitProps('grain', 0, 'gr'),
    Unit.Ounce: UnitProps('ounce', 1, 'oz'),
    Unit.Gram: UnitProps('gram', 1, 'g'),
    Unit.Pound: UnitProps('pound', 3, 'lb'),
    Unit.Kilogram: UnitProps('kilogram', 3, 'kg'),
    Unit.Newton: UnitProps('newton', 3, 'N'),
}


class MetaUnit:
    def __call__(self, *args, **kwargs):
        print(args, kwargs)


class AbstractUnit(ABC):

    def __init__(self, value: float, units: Unit):
        self._value: float = self.to_raw(value, units)
        self._defined_units: Unit = units

    def __str__(self):
        units = self._defined_units
        props = UnitPropsDict[units]
        v = self.from_raw(self._value, units)
        return f'{round(v, props.accuracy)} {props.symbol}'

    def __repr__(self):
        return f'<{self.__class__.__name__}>: {self >> self.units} {self.units.symbol} ({self._value})'

    def __format__(self, format_spec: str = "{v:.{a}f} {s}"):
        """
        :param format_spec: (str) - TODO: currently not implemented
        """
        raise NotImplemented

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

    def to_raw(self, value: float, units: Unit):
        if not isinstance(units, Unit):
            error_message = f"Type expected: {Unit}, {type(Unit).__name__} found: {type(units).__name__}"
            raise TypeError(error_message)
        raise KeyError(f'{self.__class__.__name__}: unit {units} is not supported')

    def from_raw(self, value: float, units: Unit):
        if not isinstance(units, Unit):
            error_message = f"Type expected: {Unit}, {type(Unit).__name__} found: {type(units).__name__}"
            raise TypeError(error_message)
        raise KeyError(f'{self.__class__.__name__}: unit {units} is not supported')

    def convert(self, units: Unit):
        value = self.get_in(units)
        return self.__class__(value, units)

    def get_in(self, units: Unit):
        return self.from_raw(self._value, units)

    @property
    def units(self):
        return self._defined_units

    @property
    def raw_value(self):
        return self._value


class Distance(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Distance.Inch:
            return value
        elif units == Distance.Foot:
            return value * 12
        elif units == Distance.Yard:
            return value * 36
        elif units == Distance.Mile:
            return value * 63360
        elif units == Distance.NauticalMile:
            return value * 72913.3858
        elif units == Distance.Line:
            return value / 10
        elif units == Distance.Millimeter:
            return value / 25.4
        elif units == Distance.Centimeter:
            return value / 2.54
        elif units == Distance.Meter:
            return value / 25.4 * 1000
        elif units == Distance.Kilometer:
            return value / 25.4 * 1000000
        super(Distance, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Distance.Inch:
            return value
        elif units == Distance.Foot:
            return value / 12
        elif units == Distance.Yard:
            return value / 36
        elif units == Distance.Mile:
            return value / 63360
        elif units == Distance.NauticalMile:
            return value / 72913.3858
        elif units == Distance.Line:
            return value * 10
        elif units == Distance.Millimeter:
            return value * 25.4
        elif units == Distance.Centimeter:
            return value * 2.54
        elif units == Distance.Meter:
            return value * 25.4 / 1000
        elif units == Distance.Kilometer:
            return value * 25.4 / 1000000
        super(Distance, self).from_raw(value, units)

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

    def to_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        elif units == Pressure.InHg:
            return value * 25.4
        elif units == Pressure.Bar:
            return value * 750.061683
        elif units == Pressure.HP:
            return value * 750.061683 / 1000
        elif units == Pressure.PSI:
            return value * 51.714924102396
        super(Pressure, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        elif units == Pressure.InHg:
            return value / 25.4
        elif units == Pressure.Bar:
            return value / 750.061683
        elif units == Pressure.HP:
            return value / 750.061683 * 1000
        elif units == Pressure.PSI:
            return value / 51.714924102396
        super(Pressure, self).from_raw(value, units)

    MmHg = Unit.MmHg
    InHg = Unit.InHg
    Bar = Unit.Bar
    HP = Unit.HP
    PSI = Unit.PSI


class Weight(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        elif units == Weight.Gram:
            return value * 15.4323584
        elif units == Weight.Kilogram:
            return value * 15432.3584
        elif units == Weight.Newton:
            return value * 151339.73750336
        elif units == Weight.Pound:
            return value / 0.000142857143
        elif units == Weight.Ounce:
            return value * 437.5
        super(Weight, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        elif units == Weight.Gram:
            return value / 15.4323584
        elif units == Weight.Kilogram:
            return value / 15432.3584
        elif units == Weight.Newton:
            return value / 151339.73750336
        elif units == Weight.Pound:
            return value * 0.000142857143
        elif units == Weight.Ounce:
            return value / 437.5
        super(Weight, self).from_raw(value, units)

    Grain = Unit.Grain
    Ounce = Unit.Ounce
    Gram = Unit.Gram
    Pound = Unit.Pound
    Kilogram = Unit.Kilogram
    Newton = Unit.Newton


class Temperature(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        elif units == Temperature.Rankin:
            return value - 459.67
        elif units == Temperature.Celsius:
            return value * 9 / 5 + 32
        elif units == Temperature.Kelvin:
            return (value - 273.15) * 9 / 5 + 32
        super(Temperature, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        elif units == Temperature.Rankin:
            return value + 459.67
        elif units == Temperature.Celsius:
            return (value - 32) * 5 / 9
        elif units == Temperature.Kelvin:
            return (value - 32) * 5 / 9 + 273.15
        super(Temperature, self).from_raw(value, units)

    Fahrenheit = Unit.Fahrenheit
    Celsius = Unit.Celsius
    Kelvin = Unit.Kelvin
    Rankin = Unit.Rankin


class Angular(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        elif units == Angular.Degree:
            return value / 180 * pi
        elif units == Angular.MOA:
            return value / 180 * pi / 60
        elif units == Angular.Mil:
            return value / 3200 * pi
        elif units == Angular.MRad:
            return value / 1000
        elif units == Angular.Thousand:
            return value / 3000 * pi
        elif units == Angular.InchesPer100Yd:
            return atan(value / 3600)
        elif units == Angular.CmPer100M:
            return atan(value / 10000)
        super(Angular, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        elif units == Angular.Degree:
            return value * 180 / pi
        elif units == Angular.MOA:
            return value * 180 / pi * 60
        elif units == Angular.Mil:
            return value * 3200 / pi
        elif units == Angular.MRad:
            return value * 1000
        elif units == Angular.Thousand:
            return value * 3000 / pi
        elif units == Angular.InchesPer100Yd:
            return tan(value) * 3600
        elif units == Angular.CmPer100M:
            return tan(value) * 10000
        super(Angular, self).from_raw(value, units)

    Radian = Unit.Radian
    Degree = Unit.Degree
    MOA = Unit.MOA
    Mil = Unit.Mil
    MRad = Unit.MRad
    Thousand = Unit.Thousand
    InchesPer100Yd = Unit.InchesPer100Yd
    CmPer100M = Unit.CmPer100M


class Velocity(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Velocity.MPS:
            return value
        elif units == Velocity.KMH:
            return value / 3.6
        elif units == Velocity.FPS:
            return value / 3.2808399
        elif units == Velocity.MPH:
            return value / 2.23693629
        elif units == Velocity.KT:
            return value / 1.94384449
        super(Velocity, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Velocity.MPS:
            return value
        elif units == Velocity.KMH:
            return value * 3.6
        elif units == Velocity.FPS:
            return value * 3.2808399
        elif units == Velocity.MPH:
            return value * 2.23693629
        elif units == Velocity.KT:
            return value * 1.94384449
        super(Velocity, self).from_raw(value, units)

    MPS = Unit.MPS
    KMH = Unit.KMH
    FPS = Unit.FPS
    MPH = Unit.MPH
    KT = Unit.KT


class Energy(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        elif units == Energy.Joule:
            return value * 0.737562149277
        super(Energy, self).to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        elif units == Energy.Joule:
            return value / 0.737562149277
        super(Energy, self).from_raw(value, units)

    FootPound = Unit.FootPound
    Joule = Unit.Joule

# class Convertor:
#     def __init__(self, measure=None, unit: int = 0, default_unit: int = 0):
#         self.measure = measure
#         self.unit = unit
#         self.default_unit = default_unit
#
#     def fromRaw(self, value):
#         return self.measure(value, self.default_unit).get_in(self.unit)
#
#     def toRaw(self, value):
#         return self.measure(value, self.unit).get_in(self.default_unit)
#
#     @property
#     def accuracy(self):
#         return self.measure.accuracy(self.unit)
#
#     @property
#     def unit_name(self):
#         return self.measure.name(self.unit)


# u = Weight
# for k, v in u.__dict__.items():
#     if k in Unit.__members__:
#         print(f"Unit.{k}: UnitProps('{k.lower()}', {u.accuracy(v)}, '{u.name(v)}'),")
