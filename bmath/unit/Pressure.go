package unit

import "fmt"

const Pressure_MmHg byte = 40
const Pressure_InHg byte = 41
const Pressure_Bar byte = 42
const Pressure_HP byte = 43
const Pressure_PSI byte = 44

func pressureToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Pressure_MmHg:
		return value, nil
	case Pressure_InHg:
		return value * 25.4, nil
	case Pressure_Bar:
		return value * 750.061683, nil
	case Pressure_HP:
		return value * 750.061683 / 1000, nil
	case Pressure_PSI:
		return value * 51.714924102396, nil
	default:
		return 0, fmt.Errorf("Pressure: unit %d is not supported", units)

	}
}

func pressureFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Pressure_MmHg:
		return value, nil
	case Pressure_InHg:
		return value / 25.4, nil
	case Pressure_Bar:
		return value / 750.061683, nil
	case Pressure_HP:
		return value / 750.061683 * 1000, nil
	case Pressure_PSI:
		return value / 51.714924102396, nil
	default:
		return 0, fmt.Errorf("Pressure: unit %d is not supported", units)

	}
}

//The distance
type Pressure struct {
	value        float64
	defaultUnits byte
}

//Creates a pressure value.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
func CreatePressure(value float64, units byte) (Pressure, error) {
	v, err := pressureToDefault(value, units)
	if err != nil {
		return Pressure{}, err
	} else {
		return Pressure{value: v, defaultUnits: units}, nil
	}
}

//Returns the value of the pressure in the specified units.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Pressure) Value(units byte) (float64, error) {
	return pressureFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Pressure_* constants.
func (v Pressure) Convert(units byte) Pressure {
	return Pressure{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Pressure) ValueOrZero(units byte) float64 {
	x, e := pressureFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Pressure) String() string {
	x, e := pressureFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Pressure_MmHg:
			unitName = "mmHg"
			accuracy = 0
		case Pressure_InHg:
			unitName = "inHg"
			accuracy = 2
		case Pressure_Bar:
			unitName = "bar"
			accuracy = 2
		case Pressure_HP:
			unitName = "hPa"
			accuracy = 4
		case Pressure_PSI:
			unitName = "psi"
			accuracy = 4
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}
