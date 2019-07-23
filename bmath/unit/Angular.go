package unit

import (
	"fmt"
	"math"
)

const Angular_Radian byte = 0
const Angular_Degree byte = 1
const Angular_MOA byte = 2
const Angular_Mil byte = 3
const Angular_MRad byte = 4
const Angular_Thousand byte = 5
const Angular_inchesPer100Yd byte = 6
const Angular_cmPer100M byte = 7

//The angle
type Angular struct {
	value        float64
	defaultUnits byte
}

func angularToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Angular_Radian:
		return value, nil
	case Angular_Degree:
		return value / 180 * math.Pi, nil
	case Angular_MOA:
		return value / 180 * math.Pi / 60, nil
	case Angular_Mil:
		return value / 3200 * math.Pi, nil
	case Angular_MRad:
		return value / 1000, nil
	case Angular_Thousand:
		return value / 3000 * math.Pi, nil
	case Angular_inchesPer100Yd:
		return math.Atan(value / 3600), nil
	case Angular_cmPer100M:
		return math.Atan(value / 10000), nil
	default:
		return 0, fmt.Errorf("Angular: unit %d is not supported", units)
	}
}

func angularFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Angular_Radian:
		return value, nil
	case Angular_Degree:
		return value * 180 / math.Pi, nil
	case Angular_MOA:
		return value * 180 / math.Pi * 60, nil
	case Angular_Mil:
		return value * 3200 / math.Pi, nil
	case Angular_MRad:
		return value * 1000, nil
	case Angular_Thousand:
		return value * 3000 / math.Pi, nil
	case Angular_inchesPer100Yd:
		return math.Tan(value) * 3600, nil
	case Angular_cmPer100M:
		return math.Tan(value) * 10000, nil
	default:
		return 0, fmt.Errorf("Angular: unit %d is not supported", units)
	}
}

//Creates an angular value.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
func CreateAngular(value float64, units byte) (Angular, error) {
	v, err := angularToDefault(value, units)
	if err != nil {
		return Angular{}, err
	} else {
		return Angular{value: v, defaultUnits: units}, nil
	}
}

func MustCreateAngular(value float64, units byte) Angular {
	v, err := CreateAngular(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Returns the value of the angle in the specified units.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Angular) Value(units byte) (float64, error) {
	return angularFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Angular_* constants.
func (v Angular) Convert(units byte) Angular {
	return Angular{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Angular) In(units byte) float64 {
	x, e := angularFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

//Prints the value in its default units.
//
//The default unit is the unit used in the CreateAngular function
//or in Convert method.
func (v Angular) String() string {
	x, e := angularFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Angular_Radian:
			unitName = "rad"
			accuracy = 6
		case Angular_Degree:
			unitName = "°"
			accuracy = 4
		case Angular_MOA:
			unitName = "moa"
			accuracy = 2
		case Angular_Mil:
			unitName = "mil"
			accuracy = 2
		case Angular_MRad:
			unitName = "mrad"
			accuracy = 2
		case Angular_Thousand:
			unitName = "ths"
			accuracy = 2
		case Angular_inchesPer100Yd:
			unitName = "in/100yd"
			accuracy = 2
		case Angular_cmPer100M:
			unitName = "cm/100m"
			accuracy = 2
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}

func (v Angular) Units() byte {
	return v.defaultUnits
}
