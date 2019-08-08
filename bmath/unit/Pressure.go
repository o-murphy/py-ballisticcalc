package unit

import "fmt"

//PressureMmHg is the value indicating that pressure value is expressed in millimeters of Mercury
const PressureMmHg byte = 40

//PressureInHg is the value indicating that pressure value is expressed in inches of Mercury
const PressureInHg byte = 41

//PressureBar is the value indicating that pressure value is expressed in bars
const PressureBar byte = 42

//PressureHP is the value indicating that pressure value is expressed in hectopascals
const PressureHP byte = 43

//PressurePSI is the value indicating that pressure value is expressed in pounds per square inch
const PressurePSI byte = 44

func pressureToDefault(value float64, units byte) (float64, error) {
	switch units {
	case PressureMmHg:
		return value, nil
	case PressureInHg:
		return value * 25.4, nil
	case PressureBar:
		return value * 750.061683, nil
	case PressureHP:
		return value * 750.061683 / 1000, nil
	case PressurePSI:
		return value * 51.714924102396, nil
	default:
		return 0, fmt.Errorf("Pressure: unit %d is not supported", units)

	}
}

func pressureFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case PressureMmHg:
		return value, nil
	case PressureInHg:
		return value / 25.4, nil
	case PressureBar:
		return value / 750.061683, nil
	case PressureHP:
		return value / 750.061683 * 1000, nil
	case PressurePSI:
		return value / 51.714924102396, nil
	default:
		return 0, fmt.Errorf("Pressure: unit %d is not supported", units)

	}
}

//Pressure structure keeps information about atmospheric pressure
type Pressure struct {
	value        float64
	defaultUnits byte
}

//CreatePressure creates a pressure value.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
func CreatePressure(value float64, units byte) (Pressure, error) {
	v, err := pressureToDefault(value, units)
	if err != nil {
		return Pressure{}, err
	}
	return Pressure{value: v, defaultUnits: units}, nil

}

//MustCreatePressure creates the pressure value but panics instead of returned a error
func MustCreatePressure(value float64, units byte) Pressure {
	v, err := CreatePressure(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the pressure in the specified units.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Pressure) Value(units byte) (float64, error) {
	return pressureFromDefault(v.value, units)
}

//Convert converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
func (v Pressure) Convert(units byte) Pressure {
	return Pressure{value: v.value, defaultUnits: units}
}

//In converts the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Pressure) In(units byte) float64 {
	x, e := pressureFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x

}

func (v Pressure) String() string {
	x, e := pressureFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case PressureMmHg:
		unitName = "mmHg"
		accuracy = 0
	case PressureInHg:
		unitName = "inHg"
		accuracy = 2
	case PressureBar:
		unitName = "bar"
		accuracy = 2
	case PressureHP:
		unitName = "hPa"
		accuracy = 4
	case PressurePSI:
		unitName = "psi"
		accuracy = 4
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Pressure) Units() byte {
	return v.defaultUnits
}
