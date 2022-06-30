import math
from .bmath import unit


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

    def __init__(self, altitude: unit.Distance = None, pressure: unit.Pressure = None,
                 temperature: unit.Temperature = None, humidity: float = 0.78):
        """
        Creates the atmosphere with the specified parameter
        :param altitude: unit.Distance instance
        :param pressure: unit.Pressure instance
        :param temperature: unit.Temperature instance
        :param humidity: 0 - 1 or 1 - 100 float
        """
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
        """
        :return: formatted Atmosphere data
        """
        return f'Altitude: {self._altitude}, Pressure: {self._pressure}, ' \
               f'Temperature: {self._temperature}, Humidity: {self.humidity_in_percent:.2f}'

    def create_default(self):
        self._altitude = unit.Distance(0.0, unit.DistanceFoot).validate()
        self._pressure = unit.Pressure(cStandardPressure, unit.PressureInHg).validate()
        self._temperature = unit.Temperature(cStandardTemperature, unit.TemperatureFahrenheit).validate()
        self._humidity = 0.78

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
            et = cA5 * self._humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)) * hc
        mach = math.sqrt(t + cIcaoFreezingPointTemperatureR) * cSpeedOfSound
        return density, mach

    def calculate(self) -> None:
        t = self._temperature.get_in(unit.TemperatureFahrenheit)
        p = self._pressure.get_in(unit.PressureInHg)
        density, mach = self.calculate0(t, p)
        self._density = density
        self._mach1 = mach
        self._mach = unit.Velocity(mach, unit.VelocityFPS).validate()

    def get_density_factor_and_mach_for_altitude(self, altitude: float) -> tuple[float, float]:
        org_altitude = self._altitude.get_in(unit.DistanceFoot)
        if math.fabs(org_altitude - altitude) < 30:
            density = self._density / cStandardDensity
            mach = self._mach1
            return density, mach

        t0 = self._temperature.get_in(unit.TemperatureFahrenheit)
        p = self._pressure.get_in(unit.PressureInHg)

        ta = cIcaoStandardTemperatureR + org_altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        tb = cIcaoStandardTemperatureR + altitude * cTemperatureGradient - cIcaoFreezingPointTemperatureR
        t = t0 + ta - tb
        p = p * math.pow(t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach

    @staticmethod
    def create_icao(altitude: unit.Distance):
        temperature = unit.Temperature(
            cIcaoStandardTemperatureR + altitude.get_in(
                unit.DistanceFoot
            ) * cTemperatureGradient - cIcaoFreezingPointTemperatureR, unit.TemperatureFahrenheit
        ).validate()

        pressure = unit.Pressure(
            cStandardPressure *
            math.pow(cIcaoStandardTemperatureR / (
                        temperature.get_in(unit.TemperatureFahrenheit) + cIcaoFreezingPointTemperatureR),
                     cPressureExponent),
            unit.PressureInHg
        ).validate()

        return Atmosphere(altitude, pressure, temperature, cIcaoStandardHumidity)


if __name__ == '__main__':

    atmo = Atmosphere(
        unit.Distance(500, unit.DistanceMeter),
        unit.Pressure(500, unit.PressureMmHg),
        unit.Temperature(26, unit.TemperatureCelsius),
        humidity=0.5  # 50%
    )

    # get speed of sound in mps at the atmosphere with such parameters
    speed_of_sound_in_mps = unit.Velocity(atmo.mach.get_in(unit.VelocityMPS), unit.VelocityMPS)
