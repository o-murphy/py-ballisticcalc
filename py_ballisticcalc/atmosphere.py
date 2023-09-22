from dataclasses import dataclass
from math import pow, sqrt, fabs

from .unit import *

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
class Atmosphere:
    altitude: Distance
    pressure: Pressure
    temperature: Temperature
    humidity: float
    density: float = None
    mach: Velocity = None
    mach1: float = None

    def __init__(self, altitude: Distance, pressure: Pressure, temperature: Temperature, humidity: float):
        if humidity > 1:
            humidity = humidity / 100
        if not (0 <= humidity <= 1) or not (altitude and pressure and temperature):
            self.create_default()
            # TODO: maby have to raise ValueError instead of create_default
        else:
            self.altitude = altitude
            self.pressure = pressure
            self.temperature = temperature
            self.humidity = humidity

        self.calculate()

    @staticmethod
    def ICAO(altitude: Distance = Distance(0, Distance.Foot)):

        temperature = Temperature(
            cIcaoStandardTemperatureR + altitude.get_in(Distance.Foot)
            * cTemperatureGradient - cIcaoFreezingPointTemperatureR, Temperature.Fahrenheit)

        pressure = Pressure(
            cStandardPressure *
            pow(cIcaoStandardTemperatureR / (
                    temperature.get_in(Temperature.Fahrenheit) + cIcaoFreezingPointTemperatureR),
                cPressureExponent),
            Pressure.InHg)

        return Atmosphere(altitude, pressure, temperature, cIcaoStandardHumidity)

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
        t = self.temperature.get_in(Temperature.Fahrenheit)
        p = self.pressure.get_in(Pressure.InHg)
        density, mach = self.calculate0(t, p)
        self.density = density
        self.mach1 = mach
        self.mach = Velocity(mach, Velocity.FPS)

    def get_density_factor_and_mach_for_altitude(self, altitude: float):

        org_altitude = self.altitude.get_in(Distance.Foot)
        if fabs(org_altitude - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self.mach1
            return density, mach

        t0 = self.temperature.get_in(Temperature.Fahrenheit)
        p = self.pressure.get_in(Pressure.InHg)

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * pow(t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach
