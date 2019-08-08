package unit

import "fmt"

//VelocityMPS is the value indicating that velocity value is expressed in meters per second
const VelocityMPS byte = 60

//VelocityKMH is the value indicating that velocity value is expressed in kilometers per hour
const VelocityKMH byte = 61

//VelocityFPS is the value indicating that velocity value is expressed in feet per second
const VelocityFPS byte = 62

//VelocityMPH is the value indicating that velocity value is expressed in miles per hour
const VelocityMPH byte = 63

//VelocityKT is the value indicating that velocity value is expressed in knots
const VelocityKT byte = 64

func velocityToDefault(value float64, units byte) (float64, error) {
	switch units {
	case VelocityMPS:
		return value, nil
	case VelocityKMH:
		return value / 3.6, nil
	case VelocityFPS:
		return value / 3.2808399, nil
	case VelocityMPH:
		return value / 2.23693629, nil
	case VelocityKT:
		return value / 1.94384449, nil
	default:
		return 0, fmt.Errorf("Velocity: unit %d is not supported", units)
	}
}

func velocityFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case VelocityMPS:
		return value, nil
	case VelocityKMH:
		return value * 3.6, nil
	case VelocityFPS:
		return value * 3.2808399, nil
	case VelocityMPH:
		return value * 2.23693629, nil
	case VelocityKT:
		return value * 1.94384449, nil
	default:
		return 0, fmt.Errorf("Velocity: unit %d is not supported", units)
	}
}

//Velocity struct keeps velocity or speed values
type Velocity struct {
	value        float64
	defaultUnits byte
}

//CreateVelocity creates a velocity value.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
func CreateVelocity(value float64, units byte) (Velocity, error) {
	v, err := velocityToDefault(value, units)
	if err != nil {
		return Velocity{}, err
	}
	return Velocity{value: v, defaultUnits: units}, nil

}

//MustCreateVelocity creates the velocity value but panics instead of returned a error
func MustCreateVelocity(value float64, units byte) Velocity {
	v, err := CreateVelocity(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the velocity in the specified units.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Velocity) Value(units byte) (float64, error) {
	return velocityFromDefault(v.value, units)
}

//Convert converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Velocity_* constants.
func (v Velocity) Convert(units byte) Velocity {
	return Velocity{value: v.value, defaultUnits: units}
}

//In converts the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Velocity) In(units byte) float64 {
	x, e := velocityFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x

}

func (v Velocity) String() string {
	x, e := velocityFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case VelocityMPS:
		unitName = "m/s"
		accuracy = 0
	case VelocityKMH:
		unitName = "km/h"
		accuracy = 1
	case VelocityFPS:
		unitName = "ft/s"
		accuracy = 1
	case VelocityMPH:
		unitName = "mph"
		accuracy = 1
	case VelocityKT:
		unitName = "kt"
		accuracy = 1
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Velocity) Units() byte {
	return v.defaultUnits
}
