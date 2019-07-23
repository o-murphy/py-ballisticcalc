package unit

import "fmt"

const Velocity_MPS byte = 60
const Velocity_KMH byte = 61
const Velocity_FPS byte = 62
const Velocity_MPH byte = 63
const Velocity_KT byte = 64

func velocityToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Velocity_MPS:
		return value, nil
	case Velocity_KMH:
		return value / 3.6, nil
	case Velocity_FPS:
		return value / 3.2808399, nil
	case Velocity_MPH:
		return value / 2.23693629, nil
	case Velocity_KT:
		return value / 1.94384449, nil
	default:
		return 0, fmt.Errorf("Velocity: unit %d is not supported", units)
	}
}

func velocityFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Velocity_MPS:
		return value, nil
	case Velocity_KMH:
		return value * 3.6, nil
	case Velocity_FPS:
		return value * 3.2808399, nil
	case Velocity_MPH:
		return value * 2.23693629, nil
	case Velocity_KT:
		return value * 1.94384449, nil
	default:
		return 0, fmt.Errorf("Velocity: unit %d is not supported", units)
	}
}

//The velocity
type Velocity struct {
	value        float64
	defaultUnits byte
}

//Creates a velocity value.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
func CreateVelocity(value float64, units byte) (Velocity, error) {
	v, err := velocityToDefault(value, units)
	if err != nil {
		return Velocity{}, err
	} else {
		return Velocity{value: v, defaultUnits: units}, nil
	}
}

//Returns the value of the velocity in the specified units.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Velocity) Value(units byte) (float64, error) {
	return velocityFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
func (v Velocity) Convert(units byte) Velocity {
	return Velocity{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Velocity) ValueOrZero(units byte) float64 {
	x, e := velocityFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Velocity) String() string {
	x, e := velocityFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Velocity_MPS:
			unitName = "m/s"
			accuracy = 0
		case Velocity_KMH:
			unitName = "km/h"
			accuracy = 1
		case Velocity_FPS:
			unitName = "ft/s"
			accuracy = 1
		case Velocity_MPH:
			unitName = "mph"
			accuracy = 1
		case Velocity_KT:
			unitName = "kt"
			accuracy = 1
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}
