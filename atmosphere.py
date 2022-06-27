import math
from bmath import unit


cIcaoStandardTemperatureR = 518.67
cIcaoFreezingPointTemperatureR = 459.67
cTemperatureGradient = -3.56616e-03
cIcaoStandardHumidity = 0.0
cPressureExponent = -5.255876
cSpeedOfSound = 49.0223
cA0 = 1.24871
cA1 = 0.0988438
cA2 = 0.00152907
cA3 = -3.07031e-06
cA4 = 4.21329e-07
cA5 = 3.342e-04
cStandardTemperature = 59.0
cStandardPressure = 29.92
cStandardDensity = 0.076474


class Atmosphere(object):
    """ Atmosphere describes the atmosphere conditions """

    _density: float = None
    _mach: [unit.Velocity, float] = None
    _mach1: float = None

    def __init__(self, altitude: unit.Distance, pressure: unit.Pressure,
                 temperature: unit.Temperature, humidity: float = 0.78):
        """
        Creates the atmosphere with the specified parameter
        :param altitude: unit.Distance instance
        :param pressure: unit.Pressure instance
        :param temperature: unit.Temperature instance
        :param humidity: 0 - 1 float
        """
        self._humidity = humidity / 100

        if not (0 < humidity < 100):
            self._altitude = unit.Distance(0.0, unit.DistanceFoot).must_create()
            self._pressure = unit.Pressure(cStandardPressure, unit.PressureInHg).must_create()
            self._temperature = unit.Pressure(cStandardTemperature, unit.TemperatureFahrenheit).must_create()
        else:
            self._altitude = altitude
            self._pressure = pressure
            self._temperature = temperature

        self.calculate()

    def __str__(self) -> str:
        """
        :return: formatted Atmosphere data
        """
        return f'Altitude: {self.altitude}, Pressure: {self.pressure}, ' \
               f'Temperature: {self.temperature}, Humidity: {self.humidity_in_percent:.2f}'

    @property
    def altitude(self) -> unit.Distance:
        """
        :return: the ground level altitude over the sea level
        """
        return self._altitude

    @property
    def temperature(self) -> unit.Temperature:
        """
        :return: the temperature at the ground level
        """
        return self._temperature

    @property
    def pressure(self) -> unit.Pressure:
        """
        :return: the pressure at the ground level
        """
        return self._pressure

    @property
    def humidity(self) -> float:
        """
        :return: the relative humidity set in 0 to 1 coefficient
        multiply this value by 100 to get percents
        """
        return self._humidity

    @property
    def humidity_in_percent(self) -> float:
        """
        :return: relative humidity in percents (0..100)
        """
        return self._humidity * 100

    @property
    def density(self) -> float:
        return self._density

    @property
    def density_factor(self) -> float:
        return self._density / cStandardDensity

    @property
    def mach(self) -> [unit.Velocity, float]:
        """
        :return: the speed of sound at the atmosphere with such parameters
        """
        return self._mach

    def calculate0(self, t, p) -> tuple[float, float]:
        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self.humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)) * hc
        mach = math.sqrt(t + cIcaoFreezingPointTemperatureR) * cSpeedOfSound
        return density, mach

    def calculate(self) -> None:
        t = self.temperature.get_in(unit.TemperatureFahrenheit)
        p = self.pressure.get_in(unit.PressureInHg)
        density, mach = self.calculate0(t, p)
        self._density = density
        self._mach1 = mach
        self._mach = unit.Velocity(mach, unit.VelocityFPS).must_create()

    def get_density_factor_and_mach_for_altitude(self, altitude: float) -> tuple[float, float]:
        org_altitude = self.altitude.get_in(unit.DistanceFoot)
        if abs(org_altitude - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self._mach1
            return density, mach

        t0 = self.temperature.get_in(unit.TemperatureFahrenheit)
        p = self.pressure.get_in(unit.PressureInHg)

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * ((t0 / t) ** cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach


class ICAOAtmosphere(Atmosphere):
    def __init__(self, altitude: unit.Distance):
        temperature = unit.Temperature(
            cIcaoStandardTemperatureR + altitude.get_in(
                unit.DistanceFoot
            ) * cTemperatureGradient - cIcaoFreezingPointTemperatureR, unit.TemperatureFahrenheit
        ).must_create()

        pressure = unit.Pressure(cStandardPressure * (
                (cIcaoStandardTemperatureR / (
                        temperature.get_in(unit.TemperatureFahrenheit) + cIcaoFreezingPointTemperatureR
                )) ** cPressureExponent),
            unit.PressureInHg
        ).must_create()

        super().__init__(altitude, pressure, temperature, cIcaoStandardHumidity)
