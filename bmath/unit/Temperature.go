package unit

import "fmt"

//TemperatureFahrenheit is the value indicating that temperature value is expressed in degrees of Fahrenheit
const TemperatureFahrenheit byte = 50

//TemperatureCelsius is the value indicating that temperature value is expressed in degrees of Celsius
const TemperatureCelsius byte = 51

//TemperatureKelvin is the value indicating that temperature value is expressed in degrees of Kelvin
const TemperatureKelvin byte = 52

//TemperatureRankin is the value indicating that temperature value is expressed in degrees of Rankin
const TemperatureRankin byte = 53

func temperatureToDefault(value float64, units byte) (float64, error) {
	switch units {
	case TemperatureFahrenheit:
		return value, nil
	case TemperatureRankin:
		return value - 459.67, nil
	case TemperatureCelsius:
		return value*9/5 + 32, nil
	case TemperatureKelvin:
		return (value-273.15)*9/5 + 32, nil
	default:
		return 0, fmt.Errorf("Temperature: unit %d is not supported", units)
	}

}

func temperatureFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case TemperatureFahrenheit:
		return value, nil
	case TemperatureRankin:
		return value + 459.67, nil
	case TemperatureCelsius:
		return (value - 32) * 5 / 9, nil
	case TemperatureKelvin:
		return (value-32)*5/9 + 273.15, nil
	default:
		return 0, fmt.Errorf("Temperature: unit %d is not supported", units)
	}
}

//Temperature struct keeps information about the temperature
type Temperature struct {
	value        float64
	defaultUnits byte
}

//CreateTemperature creates a temperature value.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
func CreateTemperature(value float64, units byte) (Temperature, error) {
	v, err := temperatureToDefault(value, units)
	if err != nil {
		return Temperature{}, err
	}
	return Temperature{value: v, defaultUnits: units}, nil

}

//MustCreateTemperature creates the temperature value but panics instead of returned a error
func MustCreateTemperature(value float64, units byte) Temperature {
	v, err := CreateTemperature(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the temperature in the specified units.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Temperature) Value(units byte) (float64, error) {
	return temperatureFromDefault(v.value, units)
}

//Convert converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
func (v Temperature) Convert(units byte) Temperature {
	return Temperature{value: v.value, defaultUnits: units}
}

//In convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Temperature) In(units byte) float64 {
	x, e := temperatureFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x

}

func (v Temperature) String() string {
	x, e := temperatureFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case TemperatureFahrenheit:
		unitName = "°F"
		accuracy = 1
	case TemperatureRankin:
		unitName = "°R"
		accuracy = 1
	case TemperatureCelsius:
		unitName = "°C"
		accuracy = 1
	case TemperatureKelvin:
		unitName = "°K"
		accuracy = 1
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Temperature) Units() byte {
	return v.defaultUnits
}
