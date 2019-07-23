package unit

import "fmt"

const Temperature_Fahrenheit byte = 50
const Temperature_Celsius byte = 51
const Temperature_Kelvin byte = 52
const Temperature_Rankin byte = 53

func temperatureToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Temperature_Fahrenheit:
		return value, nil
	case Temperature_Rankin:
		return value - 459.67, nil
	case Temperature_Celsius:
		return value*9/5 + 32, nil
	case Temperature_Kelvin:
		return (value-273.15)*9/5 + 32, nil
	default:
		return 0, fmt.Errorf("Temperature: unit %d is not supported", units)
	}

}

func temperatureFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Temperature_Fahrenheit:
		return value, nil
	case Temperature_Rankin:
		return value + 459.67, nil
	case Temperature_Celsius:
		return (value - 32) * 5 / 9, nil
	case Temperature_Kelvin:
		return (value-32)*5/9 + 273.15, nil
	default:
		return 0, fmt.Errorf("Temperature: unit %d is not supported", units)
	}
}

//The temperature
type Temperature struct {
	value        float64
	defaultUnits byte
}

//Creates a temperature value.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
func CreateTemperature(value float64, units byte) (Temperature, error) {
	v, err := temperatureToDefault(value, units)
	if err != nil {
		return Temperature{}, err
	} else {
		return Temperature{value: v, defaultUnits: units}, nil
	}
}

//Returns the value of the temperature in the specified units.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Temperature) Value(units byte) (float64, error) {
	return temperatureFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Temperature_* constants.
func (v Temperature) Convert(units byte) Temperature {
	return Temperature{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Temperature) ValueOrZero(units byte) float64 {
	x, e := temperatureFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Temperature) String() string {
	x, e := temperatureFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Temperature_Fahrenheit:
			unitName = "°F"
			accuracy = 1
		case Temperature_Rankin:
			unitName = "°R"
			accuracy = 1
		case Temperature_Celsius:
			unitName = "°C"
			accuracy = 1
		case Temperature_Kelvin:
			unitName = "°K"
			accuracy = 1
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}
