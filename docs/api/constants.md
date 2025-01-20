::: py_ballisticcalc.constants
    options:
        group_by_category: false
        members:

### Global atmosphere constants

| Constant            | Description                   | Value        | Unit / Notes |
|---------------------|-------------------------------|--------------|--------------|
| `cStandardHumidity` | Relative Humidity in percents | 0.0          | %            |
| `cPressureExponent` | =g*M/R*L                      | 5.255876     | -            |
| `cA0`               | Coefficient A0                | 1.24871      | -            |
| `cA1`               | Coefficient A1                | 0.0988438    | -            |
| `cA2`               | Coefficient A2                | 0.00152907   | -            |
| `cA3`               | Coefficient A3                | -3.07031e-06 | -            |
| `cA4`               | Coefficient A4                | 4.21329e-07  | -            |
| `cA5`               | Coefficient A5                | 3.342e-04    | -            |

### [ISA, metric prefer_units](https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html)

| Constant                   | Description                             | Value    | Unit / Notes     |
|----------------------------|-----------------------------------------|----------|------------------|
| `cDegreesCtoK`             | Celsius to Kelvin conversion            | 273.15   | °K = °C + 273.15 |
| `cStandardTemperatureC`    | Standard temperature in Celsius         | 15.0     | °C               |
| `cLapseRateMetric`         | Metric lapse rate                       | -6.5e-03 | °C/m             |
| `cStandardPressureMetric`  | Standard pressure (metric)              | 1013.25  | hPa              |
| `cSpeedOfSoundMetric`      | Speed of sound in metric                | 331.3    | m/s              |
| `cStandardDensityMetric`   | Standard air density (metric)           | 1.2250   | kg/m³            |
| `cDensityImperialToMetric` | Density conversion (imperial to metric) | 16.0185  | lb/ft³ to kg/m³  |

### ICAO standard atmosphere

| Constant                | Description                        | Value        | Unit / Notes     |
|-------------------------|------------------------------------|--------------|------------------|
| `cDegreesFtoR`          | Fahrenheit to Rankine conversion   | 459.67       | °R = °F + 459.67 |
| `cStandardTemperatureF` | Standard temperature in Fahrenheit | 59.0         | °F               |
| `cLapseRateImperial`    | Imperial lapse rate                | -3.56616e-03 | °F/ft            |
| `cStandardPressure`     | Standard pressure (imperial)       | 29.92        | InHg             |
| `cSpeedOfSoundImperial` | Speed of sound (imperial)          | 49.0223      | fps              |
| `cStandardDensity`      | Standard air density (imperial)    | 0.076474     | lb/ft³           |

### Runtime limits constants

| Constant               | Description                 | Value | Unit / Notes |
|------------------------|-----------------------------|-------|--------------|
| `cLowestTempF`         | Lowest temperature recorded | -130  | °F           |
| `cMaxWindDistanceFeet` | Maximum wind distance       | 1e8   | ft           |
