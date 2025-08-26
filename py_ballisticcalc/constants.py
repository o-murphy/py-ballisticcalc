"""Global physical and atmospheric constants for ballistic calculations.

This module defines scientific constants used throughout the ballistic calculations,
including atmospheric model constants, physical constants, and runtime limits.
All constants follow international standards (ISA, ICAO) where applicable.

Constant Categories:
    - Global atmosphere constants: Standard conditions and coefficients
    - ISA metric constants: International Standard Atmosphere in metric units  
    - ICAO constants: International Civil Aviation Organization standards
    - Conversion factors: Unit conversion constants
    - Runtime limits: Computational bounds and validation limits

References:
    - ISA: https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html
    - ICAO: International Civil Aviation Organization standards
    - Physical constants: NIST and other authoritative sources
"""

# Third-party imports
from typing_extensions import Final

# =============================================================================
# Global Atmosphere Constants
# =============================================================================

cStandardHumidity: Final[float] = 0.0  # Relative Humidity in percent
"""Standard relative humidity used in atmospheric calculations (%)"""

cPressureExponent: Final[float] = 5.255876  # =g*M/R*L
"""Pressure exponent constant for barometric formula (dimensionless)"""

# Atmospheric model coefficients (used in air density calculations)
cA0: Final[float] = 1.24871
cA1: Final[float] = 0.0988438
cA2: Final[float] = 0.00152907
cA3: Final[float] = -3.07031e-06
cA4: Final[float] = 4.21329e-07
cA5: Final[float] = 3.342e-04

# =============================================================================
# ISA Metric Constants (International Standard Atmosphere)
# =============================================================================

cStandardTemperatureC: Final[float] = 15.0  # °C
"""Standard temperature at sea level in Celsius (°C)"""

cLapseRateKperFoot: Final[float] = -0.0019812  # Lapse Rate, K/ft
"""Temperature lapse rate in Kelvin per foot (K/ft)"""

cLapseRateMetric: Final[float] = -6.5e-03  # Lapse Rate, °C/m
"""Temperature lapse rate in metric units (°C/m)"""

cStandardPressureMetric: Final[float] = 1013.25  # hPa
"""Standard atmospheric pressure at sea level (hPa)"""

cSpeedOfSoundMetric: Final[float] = 20.0467  # Mach1 in m/s = cSpeedOfSound * sqrt(K)
"""Speed of sound coefficient in metric units (m/s per √K)"""

cStandardDensityMetric: Final[float] = 1.2250  # kg/m^3
"""Standard air density at sea level in metric units (kg/m³)"""

# =============================================================================
# ICAO Standard Atmosphere Constants
# =============================================================================

cStandardTemperatureF: Final[float] = 59.0  # °F
"""Standard temperature at sea level in Fahrenheit (°F)"""

cLapseRateImperial: Final[float] = -3.56616e-03  # Lapse rate, °F/ft
"""Temperature lapse rate in imperial units (°F/ft)"""

cStandardPressure: Final[float] = 29.92  # InHg
"""Standard atmospheric pressure at sea level (InHg)"""

cSpeedOfSoundImperial: Final[float] = 49.0223  # Mach1 in fps = cSpeedOfSound * sqrt(°R)
"""Speed of sound coefficient in imperial units (fps per √°R)"""

cStandardDensity: Final[float] = 0.076474  # lb/ft^3
"""Standard air density at sea level in imperial units (lb/ft³)"""

# =============================================================================
# Conversion Factors
# =============================================================================

cDegreesCtoK: Final[float] = 273.15  # K = °C + 273.15
"""Celsius to Kelvin conversion constant (K)"""

cDegreesFtoR: Final[float] = 459.67  # °R = °F + 459.67
"""Fahrenheit to Rankine conversion constant (°R)"""

cDensityImperialToMetric: Final[float] = 16.0185  # lb/ft^3 to kg/m^3
"""Density conversion factor from imperial to metric units (kg/m³ per lb/ft³)"""

# =============================================================================
# Runtime Limits and Validation Constants  
# =============================================================================

cLowestTempF: Final[float] = -130  # °F
"""Minimum allowed temperature for atmospheric calculations (°F)"""

cMaxWindDistanceFeet: Final[float] = 1e8
"""Maximum wind effect distance for computational limits (ft)"""

__all__ = (
    # Global atmosphere constants
    'cStandardHumidity',
    'cPressureExponent', 
    'cA0', 'cA1', 'cA2', 'cA3', 'cA4', 'cA5',
    # ISA metric constants
    'cDegreesCtoK',
    'cStandardTemperatureC',
    'cLapseRateKperFoot',
    'cLapseRateMetric', 
    'cStandardPressureMetric',
    'cSpeedOfSoundMetric',
    'cStandardDensityMetric',
    # ICAO constants
    'cDegreesFtoR',
    'cStandardTemperatureF',
    'cLapseRateImperial',
    'cStandardPressure',
    'cSpeedOfSoundImperial',
    'cStandardDensity',
    # Conversion factors
    'cDensityImperialToMetric',
    # Runtime limits
    'cLowestTempF',
    'cMaxWindDistanceFeet',
)
