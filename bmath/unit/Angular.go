package unit

import (
	"fmt"
	"math"
)

//AngularRadian is the value indicating that the angular value is set in radians
const AngularRadian byte = 0

//AngularDegree is the value indicating that the angular value is set in degrees
const AngularDegree byte = 1

//AngularMOA is the value indicating that the angular value is set in minutes of angle
const AngularMOA byte = 2

//AngularMil is the value indicating that the angular value is set in mils (1/6400 of circle)
const AngularMil byte = 3

//AngularMRad is the value indicating that the angular value is set in milliradians
const AngularMRad byte = 4

//AngularThousand is the value indicating that the angular value is set in thousands (1/6000 of circle)
const AngularThousand byte = 5

//AngularInchesPer100Yd is the value indicating that the angular value is set in inches per 100 yard
const AngularInchesPer100Yd byte = 6

//AngularCmPer100M is the value indicating that the angular value is set in centimeters per 100 meters
const AngularCmPer100M byte = 7

//Angular structure keeps information about angular units
type Angular struct {
	value        float64
	defaultUnits byte
}

func angularToDefault(value float64, units byte) (float64, error) {
	switch units {
	case AngularRadian:
		return value, nil
	case AngularDegree:
		return value / 180 * math.Pi, nil
	case AngularMOA:
		return value / 180 * math.Pi / 60, nil
	case AngularMil:
		return value / 3200 * math.Pi, nil
	case AngularMRad:
		return value / 1000, nil
	case AngularThousand:
		return value / 3000 * math.Pi, nil
	case AngularInchesPer100Yd:
		return math.Atan(value / 3600), nil
	case AngularCmPer100M:
		return math.Atan(value / 10000), nil
	default:
		return 0, fmt.Errorf("Angular: unit %d is not supported", units)
	}
}

func angularFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case AngularRadian:
		return value, nil
	case AngularDegree:
		return value * 180 / math.Pi, nil
	case AngularMOA:
		return value * 180 / math.Pi * 60, nil
	case AngularMil:
		return value * 3200 / math.Pi, nil
	case AngularMRad:
		return value * 1000, nil
	case AngularThousand:
		return value * 3000 / math.Pi, nil
	case AngularInchesPer100Yd:
		return math.Tan(value) * 3600, nil
	case AngularCmPer100M:
		return math.Tan(value) * 10000, nil
	default:
		return 0, fmt.Errorf("Angular: unit %d is not supported", units)
	}
}

//CreateAngular creates an angular value.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
func CreateAngular(value float64, units byte) (Angular, error) {
	v, err := angularToDefault(value, units)
	if err != nil {
		return Angular{}, err
	}
	return Angular{value: v, defaultUnits: units}, nil
}

//MustCreateAngular creates an angular value and panics instead of returned the error
func MustCreateAngular(value float64, units byte) Angular {
	v, err := CreateAngular(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the angle in the specified units.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Angular) Value(units byte) (float64, error) {
	return angularFromDefault(v.value, units)
}

//Convert converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
func (v Angular) Convert(units byte) Angular {
	return Angular{value: v.value, defaultUnits: units}
}

//In converts the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Angular) In(units byte) float64 {
	x, e := angularFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x

}

//Prints the value in its default units.
//
//The default unit is the unit used in the CreateAngular function
//or in Convert method.
func (v Angular) String() string {
	x, e := angularFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case AngularRadian:
		unitName = "rad"
		accuracy = 6
	case AngularDegree:
		unitName = "°"
		accuracy = 4
	case AngularMOA:
		unitName = "moa"
		accuracy = 2
	case AngularMil:
		unitName = "mil"
		accuracy = 2
	case AngularMRad:
		unitName = "mrad"
		accuracy = 2
	case AngularThousand:
		unitName = "ths"
		accuracy = 2
	case AngularInchesPer100Yd:
		unitName = "in/100yd"
		accuracy = 2
	case AngularCmPer100M:
		unitName = "cm/100m"
		accuracy = 2
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Angular) Units() byte {
	return v.defaultUnits
}
