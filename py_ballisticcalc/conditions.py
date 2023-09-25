from dataclasses import dataclass
from math import pow, sqrt, fabs

from .unit import *

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


@dataclass
class Atmo:
    altitude: Distance
    pressure: Pressure
    temperature: Temperature
    humidity: float
    density: float = None
    mach: Velocity = None
    mach1: float = None

    def __init__(self, altitude: [float, Distance],
                 pressure: [float, Pressure],
                 temperature: [float, Temperature],
                 humidity: float):

        if humidity > 1:
            humidity = humidity / 100
        if not (0 <= humidity <= 1) or not (altitude and pressure and temperature):
            self.create_default()
            # TODO: maby have to raise ValueError instead of create_default
        else:
            self.altitude = altitude if is_unit(altitude) else Distance(altitude, DefaultUnits.distance)
            self.pressure = pressure if is_unit(pressure) else Pressure(pressure, DefaultUnits.pressure)
            self.temperature = temperature if is_unit(temperature) else Temperature(
                temperature, DefaultUnits.temperature
            )
            self.humidity = humidity

        self.calculate()

    @staticmethod
    def ICAO(altitude: [float, Distance] = 0):
        altitude = altitude if is_unit(altitude) else Distance(altitude, DefaultUnits.distance)
        temperature = Temperature(
            cIcaoStandardTemperatureR + (altitude >> Distance.Foot)
            * cTemperatureGradient - cIcaoFreezingPointTemperatureR, Temperature.Fahrenheit)

        pressure = Pressure(
            cStandardPressure *
            pow(cIcaoStandardTemperatureR / (
                    (temperature >> Temperature.Fahrenheit) + cIcaoFreezingPointTemperatureR),
                cPressureExponent),
            Pressure.InHg)

        return Atmo(
            altitude >> DefaultUnits.distance,
            pressure >> DefaultUnits.pressure,
            temperature >> DefaultUnits.temperature,
            cIcaoStandardHumidity
        )

    def create_default(self):
        self.altitude = Distance(0.0, Distance.Foot)
        self.pressure = Pressure(cStandardPressure, Pressure.InHg)
        self.temperature = Temperature(cStandardTemperature, Temperature.Fahrenheit)
        self.humidity = 0.78

    def density_factor(self):
        return self.density / cStandardDensity

    def calculate0(self, t, p):

        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self.humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)) * hc
        mach = sqrt(t + cIcaoFreezingPointTemperatureR) * cSpeedOfSound
        return density, mach

    def calculate(self):
        t = self.temperature >> Temperature.Fahrenheit
        p = self.pressure >> Pressure.InHg
        density, mach = self.calculate0(t, p)
        self.density = density
        self.mach1 = mach
        self.mach = Velocity(mach, Velocity.FPS)

    def get_density_factor_and_mach_for_altitude(self, altitude: float):

        org_altitude = self.altitude >> Distance.Foot
        if fabs(org_altitude - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self.mach1
            return density, mach

        t0 = self.temperature >> Temperature.Fahrenheit
        p = self.pressure >> Pressure.InHg

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * pow(t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach


@dataclass
class Wind:
    """
    Represents wind info valid to desired distance

    Attributes:
        until_distance (Distance): default 9999 - represents inf
        velocity (Velocity): default 0
        direction (Angular): default 0
    """

    velocity: Velocity = Velocity(0, Velocity.FPS)
    direction: Angular = Angular(0, Angular.Degree)
    until_distance: Distance = Distance(9999, Distance.Kilometer)

    def __init__(self, velocity: [float, Velocity] = 0,
                 direction: [float, Angular] = 0,
                 until_distance: [float, Distance] = 9999):
        self.velocity = velocity if is_unit(velocity) else Velocity(velocity, DefaultUnits.velocity)
        self.direction = direction if is_unit(direction) else Angular(direction, DefaultUnits.angular)
        self.until_distance = until_distance if is_unit(until_distance) else Distance(until_distance, DefaultUnits.distance)


@dataclass
class Shot:
    sight_angle: Angular
    max_range: Distance
    step: Distance
    shot_angle: Angular = Angular(0, Angular.Radian)
    cant_angle: Angular = Angular(0, Angular.Radian)

    def __init__(self, sight_angle: [float, Angular],
                 max_range: [float, Distance] = 100,
                 step: [float, Distance] = 0,
                 shot_angle: [float, Angular] = 0,
                 cant_angle: [float, Angular] = 0):

        self.sight_angle = sight_angle if is_unit(sight_angle) else Angular(sight_angle, DefaultUnits.angular)
        self.max_range = max_range if is_unit(max_range) else Distance(max_range, DefaultUnits.distance)
        self.step = step if is_unit(step) else Distance(step, DefaultUnits.distance)
        self.shot_angle = shot_angle if is_unit(shot_angle) else Angular(shot_angle, DefaultUnits.angular)
        self.cant_angle = cant_angle if is_unit(cant_angle) else Angular(cant_angle, DefaultUnits.angular)
