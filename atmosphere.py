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
    _mach: unit.Velocity = None
    _mach1: float = None

    def __init__(self, altitude: unit.Distance, pressure: unit.Pressure,
                 temperature: unit.Temperature, humidity: float = 0.78):
        """
        Creates the atmosphere with the specified parameter
        :param altitude: unit.Distance
        :param pressure: unit.Pressure
        :param temperature: unit.Temperature
        :param humidity: 0 - 1 float
        """
        self._humidity = humidity / 100

        if not (0 < humidity < 100):
            self._altitude = unit.Distance().must_create(0.0, unit.DistanceFoot)
            self._pressure = unit.Pressure().must_create(cStandardPressure, unit.UniPressureInHg)
            self._temperature = unit.Pressure().must_create(cStandardTemperature, unit.TemperatureFahrenheit)
        else:
            self._altitude = altitude
            self._pressure = pressure
            self._temperature = temperature

    def __str__(self) -> str:
        return f'Altitude: {self.altitude}, Pressure: {self.pressure}, ' \
               f'Temperature: {self.temperature}, Humidity: {self.humidity_in_percent:.2f}'

    @property
    def altitude(self) -> unit.Distance:
        return self._altitude

    @property
    def temperature(self) -> unit.Temperature:
        return self._temperature

    @property
    def pressure(self) -> unit.Pressure:
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
    def mach(self) -> unit.Velocity:
        """
        :return: the speed of sound at the atmosphere with such parameters
        """
        return self._mach

    def calculate0(self):
        return

    def calculate(self):
        """TODO:"""
        return


def CreateICAOAtmosphere():
    """TODO:"""
    return
