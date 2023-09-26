from math import pow, sqrt, fabs

from .settings import Settings as Set
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


class Atmo:
    __slots__ = ('altitude', 'pressure',
                 'temperature', 'humidity',
                 'density', 'mach', '_mach1')

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
            self.altitude: Distance = altitude if is_unit(altitude) else Set.Units.distance(altitude)
            self.pressure: Pressure = pressure if is_unit(pressure) else Set.Units.pressure(pressure)
            self.temperature: Temperature = temperature if is_unit(temperature) else Set.Units.temperature(temperature)
            self.humidity: float = humidity

        self.density, self.mach, self._mach1, = None, None, None

        self.calculate()

    @staticmethod
    def ICAO(altitude: [float, Distance] = 0):
        altitude = altitude if is_unit(altitude) else Distance(altitude, Set.Units.distance)
        temperature = Temperature.Fahrenheit(
            cIcaoStandardTemperatureR + (altitude >> Distance.Foot)
            * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        )

        pressure = Pressure.InHg(
            cStandardPressure * pow(cIcaoStandardTemperatureR / (
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

    def create_default(self):
        self.altitude = Distance.Foot(0)
        self.pressure = Pressure.InHg(cStandardPressure)
        self.temperature = Temperature.Fahrenheit(cStandardTemperature)
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
        self._mach1 = mach
        self.mach = Velocity(mach, Velocity.FPS)

    def get_density_factor_and_mach_for_altitude(self, altitude: float):

        org_altitude = self.altitude >> Distance.Foot
        if fabs(org_altitude - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self._mach1
            return density, mach

        t0 = self.temperature >> Temperature.Fahrenheit
        p = self.pressure >> Pressure.InHg

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * pow(t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach


class Wind:
    """
    Represents wind info valid to desired distance

    Attributes:
        until_distance (Distance): default 9999 - represents inf
        velocity (Velocity): default 0
        direction (Angular): default 0
    """

    __slots__ = ('velocity', 'direction', 'until_distance')

    def __init__(self, velocity: [float, Velocity] = Velocity.FPS(0),
                 direction: [float, Angular] = Angular.Degree(0),
                 until_distance: [float, Distance] = Distance.Kilometer(9999)):
        self.velocity: Velocity = velocity if is_unit(velocity) else Set.Units.velocity(velocity)
        self.direction: Angular = direction if is_unit(direction) else Set.Units.angular(direction)
        self.until_distance: Distance = until_distance \
            if is_unit(until_distance) else Set.Units.distance(until_distance)


class Shot:
    __slots__ = ('sight_angle', 'max_range', 'step', 'shot_angle', 'cant_angle')

    def __init__(self,
                 max_range: [float, Distance],
                 step: [float, Distance],
                 shot_angle: [float, Angular] = 0,
                 cant_angle: [float, Angular] = 0,
                 sight_angle: [float, Angular] = 0
                 ):
        self.sight_angle: Angular = sight_angle if is_unit(sight_angle) else Set.Units.angular(sight_angle)
        self.max_range: Distance = max_range if is_unit(max_range) else Set.Units.distance(max_range)
        self.step: Distance = step if is_unit(step) else Set.Units.distance(step)
        self.shot_angle: Angular = shot_angle if is_unit(shot_angle) else Set.Units.angular(shot_angle)
        self.cant_angle: Angular = cant_angle if is_unit(cant_angle) else Set.Units.angular(cant_angle)