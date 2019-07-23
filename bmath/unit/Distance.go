package unit

import "fmt"

const Distance_Inch byte = 10
const Distance_Foot byte = 11
const Distance_Yard byte = 12
const Distance_Mile byte = 13
const Distance_NauticalMile byte = 14
const Distance_Millimeter byte = 15
const Distance_Centimeter byte = 16
const Distance_Meter byte = 17
const Distance_Kilometer byte = 18
const Distance_Line byte = 19

//The distance
type Distance struct {
	value        float64
	defaultUnits byte
}

func distanceToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Distance_Inch:
		return value, nil
	case Distance_Foot:
		return value * 12, nil
	case Distance_Yard:
		return value * 36, nil
	case Distance_Mile:
		return value * 63360, nil
	case Distance_NauticalMile:
		return value * 72913.3858, nil
	case Distance_Line:
		return value / 10, nil
	case Distance_Millimeter:
		return value / 25.4, nil
	case Distance_Centimeter:
		return value / 2.54, nil
	case Distance_Meter:
		return value / 25.4 * 1000, nil
	case Distance_Kilometer:
		return value / 25.4 * 1000000, nil
	default:
		return 0, fmt.Errorf("Distance: unit %d is not supported", units)
	}

}

func distanceFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Distance_Inch:
		return value, nil
	case Distance_Foot:
		return value / 12, nil
	case Distance_Yard:
		return value / 36, nil
	case Distance_Mile:
		return value / 63360, nil
	case Distance_NauticalMile:
		return value / 72913.3858, nil
	case Distance_Line:
		return value * 10, nil
	case Distance_Millimeter:
		return value * 25.4, nil
	case Distance_Centimeter:
		return value * 2.54, nil
	case Distance_Meter:
		return value * 25.4 / 1000, nil
	case Distance_Kilometer:
		return value * 25.4 / 1000000, nil
	default:
		return 0, fmt.Errorf("Distance: unit %d is not supported", units)
	}
}

//Creates a distance value.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
func CreateDistance(value float64, units byte) (Distance, error) {
	v, err := distanceToDefault(value, units)
	if err != nil {
		return Distance{}, err
	} else {
		return Distance{value: v, defaultUnits: units}, nil
	}
}

//Returns the value of the distance in the specified units.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Distance) Value(units byte) (float64, error) {
	return distanceFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
func (v Distance) Convert(units byte) Distance {
	return Distance{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Distance) ValueOrZero(units byte) float64 {
	x, e := distanceFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Distance) String() string {
	x, e := distanceFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Distance_Inch:
			unitName = "\""
			accuracy = 1
		case Distance_Foot:
			unitName = "'"
			accuracy = 2
		case Distance_Yard:
			unitName = "yd"
			accuracy = 3
		case Distance_Mile:
			unitName = "mi"
			accuracy = 3
		case Distance_NauticalMile:
			unitName = "nm"
			accuracy = 3
		case Distance_Line:
			unitName = "ln"
			accuracy = 1
		case Distance_Millimeter:
			unitName = "mm"
			accuracy = 0
		case Distance_Centimeter:
			unitName = "cm"
			accuracy = 1
		case Distance_Meter:
			unitName = "m"
			accuracy = 2
		case Distance_Kilometer:
			unitName = "km"
			accuracy = 3
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}
