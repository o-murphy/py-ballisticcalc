from enum import IntEnum
from math import pi, atan, tan
from typing import NamedTuple, Callable, get_type_hints

__all__ = ('Unit', 'AbstractUnit', 'UnitPropsDict', 'Distance',
           'Velocity', 'Angular', 'Temperature', 'Pressure',
           'Energy', 'Weight', 'is_unit', 'TypedUnits')


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
    InchesPer100Yd = 6
    CmPer100M = 7

    INCH = 10
    FOOT = 11
    YARD = 12
    MILE = 13
    NauticalMile = 14
    MILLIMETER = 15
    CENTIMETER = 16
    METER: Callable = 17
    KILOMETER = 18
    LINE = 19

    FootPound = 30
    JOULE = 31

    MmHg = 40
    InHg = 41
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
    def key(self):
        return UnitPropsDict[self].name

    @property
    def accuracy(self):
        return UnitPropsDict[self].accuracy

    @property
    def symbol(self):
        return UnitPropsDict[self].symbol

    def __call__(self: 'Unit', value: [int, float]) -> 'AbstractUnit':

        if 0 <= self < 10:
            return Angular(value, self)
        if 10 <= self < 20:
            return Distance(value, self)
        if 30 <= self < 40:
            return Energy(value, self)
        if 40 <= self < 50:
            return Pressure(value, self)
        if 50 <= self < 60:
            return Temperature(value, self)
        if 60 <= self < 70:
            return Velocity(value, self)
        if 70 <= self < 80:
            return Weight(value, self)
        raise TypeError(f"{self} Unit is not supports")


class UnitProps(NamedTuple):
    """
    Properties of unit measure
    """
    name: str
    accuracy: int
    symbol: str


UnitPropsDict = {
    Unit.RAD: UnitProps('radian', 6, 'rad'),
    Unit.DEGREE: UnitProps('degree', 4, '°'),
    Unit.MOA: UnitProps('moa', 2, 'moa'),
    Unit.MIL: UnitProps('mil', 2, 'mil'),
    Unit.MRAD: UnitProps('mrad', 2, 'mrad'),
    Unit.THOUSAND: UnitProps('thousand', 2, 'ths'),
    Unit.InchesPer100Yd: UnitProps('inches/100yd', 2, 'in/100yd'),
    Unit.CmPer100M: UnitProps('cm/100m', 2, 'cm/100m'),

    Unit.INCH: UnitProps("inch", 1, "inch"),
    Unit.FOOT: UnitProps("foot", 2, "ft"),
    Unit.YARD: UnitProps("yard", 3, "yd"),
    Unit.MILE: UnitProps("mile", 3, "mi"),
    Unit.NauticalMile: UnitProps("nautical mile", 3, "nm"),
    Unit.MILLIMETER: UnitProps("millimeter", 3, "mm"),
    Unit.CENTIMETER: UnitProps("centimeter", 3, "cm"),
    Unit.METER: UnitProps("meter", 3, "m"),
    Unit.KILOMETER: UnitProps("kilometer", 3, "km"),
    Unit.LINE: UnitProps("line", 3, "ln"),

    Unit.FootPound: UnitProps('foot * pound', 0, 'ft·lb'),
    Unit.JOULE: UnitProps('joule', 0, 'J'),

    Unit.MmHg: UnitProps('mmhg', 0, 'mmHg'),
    Unit.InHg: UnitProps('inhg', 6, '?'),
    Unit.BAR: UnitProps('bar', 2, 'bar'),
    Unit.HP: UnitProps('hp', 4, 'hPa'),
    Unit.PSI: UnitProps('psi', 4, 'psi'),

    Unit.FAHRENHEIT: UnitProps('fahrenheit', 1, '°F'),
    Unit.CELSIUS: UnitProps('celsius', 1, '°C'),
    Unit.KELVIN: UnitProps('kelvin', 1, '°K'),
    Unit.RANKIN: UnitProps('rankin', 1, '°R'),

    Unit.MPS: UnitProps('mps', 0, 'm/s'),
    Unit.KMH: UnitProps('kmh', 1, 'km/h'),
    Unit.FPS: UnitProps('fps', 1, 'ft/s'),
    Unit.MPH: UnitProps('mph', 1, 'mph'),
    Unit.KT: UnitProps('kt', 1, 'kt'),

    Unit.GRAIN: UnitProps('grain', 0, 'gr'),
    Unit.OUNCE: UnitProps('ounce', 1, 'oz'),
    Unit.GRAM: UnitProps('gram', 1, 'g'),
    Unit.POUND: UnitProps('pound', 3, 'lb'),
    Unit.KILOGRAM: UnitProps('kilogram', 3, 'kg'),
    Unit.NEWTON: UnitProps('newton', 3, 'N'),
}


class AbstractUnit:

    __slots__ = ('_value', '_defined_units')

    def __init__(self, value: [float, int], units: Unit):
        self._value: float = self.to_raw(value, units)
        self._defined_units: Unit = units

    def __str__(self):
        units = self._defined_units
        props = UnitPropsDict[units]
        v = self.from_raw(self._value, units)
        return f'{round(v, props.accuracy)} {props.symbol}'

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self >> self.units} {self.units.symbol} ({self._value})>'

    def __format__(self, format_spec: str = "{v:.{a}f} {s}"):
        """
        :param format_spec: (str) - TODO: currently not implemented
        """
        raise NotImplementedError

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
            error_message = f"Type expected: {Unit}, {type(Unit).__name__} found: {type(units).__name__} ({value})"
            raise TypeError(error_message)
        raise KeyError(f'{self.__class__.__name__}: unit {units} is not supported')

    def from_raw(self, value: float, units: Unit):
        if not isinstance(units, Unit):
            error_message = f"Type expected: {Unit}, {type(Unit).__name__} found: {type(units).__name__} ({value})"
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
        if units == Distance.Foot:
            return value * 12
        if units == Distance.Yard:
            return value * 36
        if units == Distance.Mile:
            return value * 63360
        if units == Distance.NauticalMile:
            return value * 72913.3858
        if units == Distance.Line:
            return value / 10
        if units == Distance.Millimeter:
            return value / 25.4
        if units == Distance.Centimeter:
            return value / 2.54
        if units == Distance.Meter:
            return value / 25.4 * 1000
        if units == Distance.Kilometer:
            return value / 25.4 * 1000000
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Distance.Inch:
            return value
        if units == Distance.Foot:
            return value / 12
        if units == Distance.Yard:
            return value / 36
        if units == Distance.Mile:
            return value / 63360
        if units == Distance.NauticalMile:
            return value / 72913.3858
        if units == Distance.Line:
            return value * 10
        if units == Distance.Millimeter:
            return value * 25.4
        if units == Distance.Centimeter:
            return value * 2.54
        if units == Distance.Meter:
            return value * 25.4 / 1000
        if units == Distance.Kilometer:
            return value * 25.4 / 1000000
        super().from_raw(value, units)

    Inch = Unit.INCH
    Foot = Unit.FOOT
    Yard = Unit.YARD
    Mile = Unit.MILE
    NauticalMile = Unit.NauticalMile
    Millimeter = Unit.MILLIMETER
    Centimeter = Unit.CENTIMETER
    Meter = Unit.METER
    Kilometer = Unit.KILOMETER
    Line = Unit.LINE


class Pressure(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        if units == Pressure.InHg:
            return value * 25.4
        if units == Pressure.Bar:
            return value * 750.061683
        if units == Pressure.HP:
            return value * 750.061683 / 1000
        if units == Pressure.PSI:
            return value * 51.714924102396
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Pressure.MmHg:
            return value
        if units == Pressure.InHg:
            return value / 25.4
        if units == Pressure.Bar:
            return value / 750.061683
        if units == Pressure.HP:
            return value / 750.061683 * 1000
        if units == Pressure.PSI:
            return value / 51.714924102396
        super().from_raw(value, units)

    MmHg = Unit.MmHg
    InHg = Unit.InHg
    Bar = Unit.BAR
    HP = Unit.HP
    PSI = Unit.PSI


class Weight(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        if units == Weight.Gram:
            return value * 15.4323584
        if units == Weight.Kilogram:
            return value * 15432.3584
        if units == Weight.Newton:
            return value * 151339.73750336
        if units == Weight.Pound:
            return value / 0.000142857143
        if units == Weight.Ounce:
            return value * 437.5
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Weight.Grain:
            return value
        if units == Weight.Gram:
            return value / 15.4323584
        if units == Weight.Kilogram:
            return value / 15432.3584
        if units == Weight.Newton:
            return value / 151339.73750336
        if units == Weight.Pound:
            return value * 0.000142857143
        if units == Weight.Ounce:
            return value / 437.5
        super().from_raw(value, units)

    Grain = Unit.GRAIN
    Ounce = Unit.OUNCE
    Gram = Unit.GRAM
    Pound = Unit.POUND
    Kilogram = Unit.KILOGRAM
    Newton = Unit.NEWTON


class Temperature(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        if units == Temperature.Rankin:
            return value - 459.67
        if units == Temperature.Celsius:
            return value * 9 / 5 + 32
        if units == Temperature.Kelvin:
            return (value - 273.15) * 9 / 5 + 32
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Temperature.Fahrenheit:
            return value
        if units == Temperature.Rankin:
            return value + 459.67
        if units == Temperature.Celsius:
            return (value - 32) * 5 / 9
        if units == Temperature.Kelvin:
            return (value - 32) * 5 / 9 + 273.15
        super().from_raw(value, units)

    Fahrenheit = Unit.FAHRENHEIT
    Celsius = Unit.CELSIUS
    Kelvin = Unit.KELVIN
    Rankin = Unit.RANKIN


class Angular(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        if units == Angular.Degree:
            return value / 180 * pi
        if units == Angular.MOA:
            return value / 180 * pi / 60
        if units == Angular.Mil:
            return value / 3200 * pi
        if units == Angular.MRad:
            return value / 1000
        if units == Angular.Thousand:
            return value / 3000 * pi
        if units == Angular.InchesPer100Yd:
            return atan(value / 3600)
        if units == Angular.CmPer100M:
            return atan(value / 10000)
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Angular.Radian:
            return value
        if units == Angular.Degree:
            return value * 180 / pi
        if units == Angular.MOA:
            return value * 180 / pi * 60
        if units == Angular.Mil:
            return value * 3200 / pi
        if units == Angular.MRad:
            return value * 1000
        if units == Angular.Thousand:
            return value * 3000 / pi
        if units == Angular.InchesPer100Yd:
            return tan(value) * 3600
        if units == Angular.CmPer100M:
            return tan(value) * 10000
        super().from_raw(value, units)

    Radian = Unit.RAD
    Degree = Unit.DEGREE
    MOA = Unit.MOA
    Mil = Unit.MIL
    MRad = Unit.MRAD
    Thousand = Unit.THOUSAND
    InchesPer100Yd = Unit.InchesPer100Yd
    CmPer100M = Unit.CmPer100M


class Velocity(AbstractUnit):

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
        super().to_raw(value, units)

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
        super().from_raw(value, units)

    MPS = Unit.MPS
    KMH = Unit.KMH
    FPS = Unit.FPS
    MPH = Unit.MPH
    KT = Unit.KT


class Energy(AbstractUnit):

    def to_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        if units == Energy.Joule:
            return value * 0.737562149277
        super().to_raw(value, units)

    def from_raw(self, value: float, units: Unit):
        if units == Energy.FootPound:
            return value
        if units == Energy.Joule:
            return value / 0.737562149277
        super().from_raw(value, units)

    FootPound = Unit.FootPound
    Joule = Unit.JOULE


class TypedUnits:
    def __setattr__(self, key, value):
        if hasattr(self, key):
            if not isinstance(value, AbstractUnit) and isinstance(get_type_hints(self)[key], Unit):
                value = get_type_hints(self)[key](value)
        super().__setattr__(key, value)


def is_unit(obj: [AbstractUnit, float, int]):
    """
    Check if obj is inherited by AbstractUnit
    :return: False - if float or int
    """
    if isinstance(obj, AbstractUnit):
        return True
    if isinstance(obj, (float, int)):
        return False
    if obj is None:
        return None
    raise TypeError(f"Expected Unit, int, or float, found {obj.__class__.__name__}")


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

# Unit.Centimeter.meta = 1
#
# m = MetaUnit(17, MeasureType.Distance)
# print(m, m.measure_type)
#
# print(Unit.Meter.measure_type)


# Default units
# Angular.Radian
# Distance.Inch
# Energy.FootPound
# Weight.Grain
# Velocity.MPS
# Temperature.Fahrenheit
# Pressure.MmHg
