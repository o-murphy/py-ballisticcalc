import math
from dataclasses import dataclass, field

from .settings import Settings as Set
from .unit import Distance, Velocity, Temperature, Pressure, is_unit, TypedUnits, Angular

__all__ = ('Atmo', 'Wind', 'Shot')

cIcaoStandardTemperatureR: float = 518.67
cIcaoFreezingPointTemperatureR: float = 459.67
cTemperatureGradient: float = -3.56616e-03
cIcaoStandardHumidity: float = 0.0
cPressureExponent: float = -5.255876
cSpeedOfSound: float = 49.0223
cA0: float = 1.24871
cA1: float = 0.0988438
cA2: float = 0.00152907
cA3: float = -3.07031e-06
cA4: float = 4.21329e-07
cA5: float = 3.342e-04
cStandardTemperature: float = 59.0
cStandardPressure: float = 29.92
cStandardDensity: float = 0.076474

cIcaoTemperatureDeltaR: float = cIcaoStandardTemperatureR - cIcaoFreezingPointTemperatureR


@dataclass
class Atmo(TypedUnits):

    altitude: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    pressure: [float, Pressure] = field(default_factory=lambda: Set.Units.pressure)
    temperature: [float, Temperature] = field(default_factory=lambda: Set.Units.temperature)
    humidity: float = 0.78
    mach: Velocity = field(init=False)
    _mach1: Velocity = field(init=False)
    _a0: float = field(init=False)
    _t0: float = field(init=False)
    _p0: float = field(init=False)
    _ta: float = field(init=False)

    def __post_init__(self):

        if self.humidity > 1:
            self.humidity = self.humidity / 100
        if not (0 <= self.humidity <= 1):
            self.humidity = 0.78
        if not self.altitude:
            self.altitude = Distance.Foot(0)
        if not self.pressure:
            self.pressure = Pressure.InHg(cStandardPressure)
        if not self.temperature:
            self.temperature = Temperature.Fahrenheit(cStandardTemperature)

        self.calculate()

    @staticmethod
    def icao(altitude: [float, Distance] = 0):
        """Creates Atmosphere with ICAO values"""
        altitude = altitude if is_unit(altitude) else Distance(altitude, Set.Units.distance)
        temperature = Temperature.Fahrenheit(
            cIcaoStandardTemperatureR + (altitude >> Distance.Foot)
            * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        )

        pressure = Pressure.InHg(
            cStandardPressure * math.pow(cIcaoStandardTemperatureR / (
                    (temperature >> Temperature.Fahrenheit) + cIcaoFreezingPointTemperatureR),
                                    cPressureExponent
                                    )
        )

        return Atmo(
            altitude >> Set.Units.distance,
            pressure >> Set.Units.pressure,
            temperature >> Set.Units.temperature,
            cIcaoStandardHumidity
        )

    def density_factor(self):
        return self.density / cStandardDensity

    def calculate0(self, t, p):

        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self.humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (
                cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)
        ) * hc
        mach = math.sqrt(t + cIcaoFreezingPointTemperatureR) * cSpeedOfSound
        return density, mach

    def calculate(self):
        self._t0 = self.temperature >> Temperature.Fahrenheit
        self._p0 = self.pressure >> Pressure.InHg
        self._a0 = self.altitude >> Distance.Foot
        self._ta = self._a0 * cTemperatureGradient + cIcaoTemperatureDeltaR

        self.density, self._mach1 = self.calculate0(self._t0, self._p0)
        self.mach = Velocity(self._mach1, Velocity.FPS)

    def get_density_factor_and_mach_for_altitude(self, altitude: float):

        if math.fabs(self._a0 - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self._mach1
            return density, mach

        tb = altitude * cTemperatureGradient + cIcaoTemperatureDeltaR
        t = self._t0 + self._ta - tb
        p = self._p0 * math.pow(self._t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach


@dataclass
class Wind(TypedUnits):
    velocity: [float, Velocity] = field(default_factory=lambda: Set.Units.velocity)
    direction_from: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    until_distance: [float, Distance] = field(default_factory=lambda: Set.Units.distance)

    def __post_init__(self):
        if not self.until_distance:
            self.until_distance = Distance.Meter(9999)
        if not self.direction_from or not self.velocity:
            self.direction_from = 0
            self.velocity = 0


@dataclass
class Shot(TypedUnits):
    max_range: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    step: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    shot_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    cant_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    sight_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)

    def __post_init__(self):
        if not self.shot_angle:
            self.shot_angle = 0
        if not self.cant_angle:
            self.cant_angle = 0
        if not self.sight_angle:
            self.sight_angle = 0
