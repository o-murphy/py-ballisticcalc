from libc.math cimport pow, sqrt, fabs
from py_ballisticcalc.bmath.cunit import *


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


cdef class Atmosphere:
    cdef float _density, _humidity, _mach1
    cdef _mach
    cdef _altitude
    cdef _pressure
    cdef _temperature

    def __init__(self, altitude: Distance, pressure: Pressure, temperature: Temperature, humidity: float):
        if humidity > 1:
            humidity = humidity / 100

        if humidity < 0 or humidity > 100:
            self.create_default()
        elif not altitude or not pressure or not temperature:
            self.create_default()
        else:
            self._altitude = altitude
            self._pressure = pressure
            self._temperature = temperature
            self._humidity = humidity

        self.calculate()

    def __str__(self) -> str:
        return f'Altitude: {self._altitude}, Pressure: {self._pressure}, ' \
               f'Temperature: {self._temperature}, Humidity: {self.humidity_in_percent:.2f}'

    cdef string(self):
        return self.__str__()

    cpdef create_default(self):
        self._altitude = Distance(0.0, DistanceFoot)
        self._pressure = Pressure(cStandardPressure, PressureInHg)
        self._temperature = Temperature(cStandardTemperature, TemperatureFahrenheit)
        self._humidity = 0.78

    cpdef altitude(self):
        return self._altitude

    cpdef temperature(self):
        return self._temperature

    cpdef pressure(self):
        return self._pressure

    cpdef float humidity(self):
        return self._humidity

    cpdef float humidity_in_percent(self):
        return self._humidity * 100

    cpdef float density(self):
        return self._density

    cpdef float density_factor(self):
        return self._density / cStandardDensity

    cpdef float mach(self):
        return self._mach

    cpdef (float, float) calculate0(self, t: float, p: float):
        cdef float et0, et, hc, density, mach

        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self._humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)) * hc
        mach = sqrt(t + cIcaoFreezingPointTemperatureR) * cSpeedOfSound
        return density, mach

    cpdef calculate(self):
        cdef float density, mach, mach1, t, p
        t = self._temperature.get_in(TemperatureFahrenheit)
        p = self._pressure.get_in(PressureInHg)
        density, mach = self.calculate0(t, p)
        self._density = density
        self._mach1 = mach
        self._mach = Velocity(mach, VelocityFPS)

    cpdef (float, float) get_density_factor_and_mach_for_altitude(self, altitude: float):
        cdef float density, mach, t0, p, ta, tb, t, org_altitude
        org_altitude = self._altitude.get_in(DistanceFoot)
        if fabs(org_altitude - altitude) < 30:
            density = self._density / cStandardDensity
            mach = self._mach1
            return density, mach

        t0 = self._temperature.get_in(TemperatureFahrenheit)
        p = self._pressure.get_in(PressureInHg)

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * pow(t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach

cpdef IcaoAtmosphere(altitude: Distance):
    cdef float temperature, pressure
    temperature = Temperature(
        cIcaoStandardTemperatureR + altitude.get_in(DistanceFoot)
        * cTemperatureGradient - cIcaoFreezingPointTemperatureR, TemperatureFahrenheit)

    pressure = Pressure(
        cStandardPressure *
        pow(cIcaoStandardTemperatureR / (
                temperature.get_in(TemperatureFahrenheit) + cIcaoFreezingPointTemperatureR),
                 cPressureExponent),
        PressureInHg)

    return Atmosphere(altitude, pressure, temperature, cIcaoStandardHumidity)
