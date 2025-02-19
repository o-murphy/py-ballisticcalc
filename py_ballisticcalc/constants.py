"""Global Constants"""

from typing_extensions import Final

# Global atmosphere constants
cStandardHumidity: Final[float] = 0.0  # Relative Humidity
cPressureExponent: Final[float] = 5.255876  # =g*M/R*L

# ISA, metric prefer_units: (https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html)
cDegreesCtoK: Final[float] = 273.15  # °K = °C + 273.15
cStandardTemperatureC: Final[float] = 15.0  # °C
cLapseRateKperFoot: Final[float] = -0.0019812  # Lapse Rate, °K/ft
cLapseRateMetric: Final[float] = -6.5e-03  # Lapse Rate, °C/m
cStandardPressureMetric: Final[float] = 1013.25  # hPa
cSpeedOfSoundMetric: Final[float] = 20.0467  # Mach1 in m/s = cSpeedOfSound * sqrt(°K)
cStandardDensityMetric: Final[float] = 1.2250  # kg/m^3
cDensityImperialToMetric: Final[float] = 16.0185  # lb/ft^3 to kg/m^3

# ICAO standard atmosphere:
cDegreesFtoR: Final[float] = 459.67  # °R = °F + 459.67
cStandardTemperatureF: Final[float] = 59.0  # °F
cLapseRateImperial: Final[float] = -3.56616e-03  # Lapse rate, °F/ft
cStandardPressure: Final[float] = 29.92  # InHg
cSpeedOfSoundImperial: Final[float] = 49.0223  # Mach1 in fps = cSpeedOfSound * sqrt(°R)
cStandardDensity: Final[float] = 0.076474  # lb/ft^3

# Runtime constants
cLowestTempF: Final[float] = -130  # °F
cMaxWindDistanceFeet: Final[float] = 1e8
