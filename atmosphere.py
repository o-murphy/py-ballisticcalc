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

    density: float = None
    mach: unit.Velocity = None
    mach1: float = None

    def __init__(self, altitude: unit.Distance, pressure: unit.Pressure,
                 temperature: unit.Temperature, humidity: float = 0.78):
        self.humidity = humidity

        if not (0 < humidity < 100):
            self.altitude = unit.Distance().must_create(0.0, unit.DistanceFoot)
            self.pressure = unit.Pressure().must_create(cStandardPressure, unit.UniPressureInHg)
            self.temperature = unit.Pressure().must_create(cStandardTemperature, unit.TemperatureFahrenheit)

        else:
            self.altitude = altitude
            self.pressure = pressure
            self.temperature = temperature

