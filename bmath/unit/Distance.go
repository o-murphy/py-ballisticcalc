package unit

import "fmt"

//DistanceInch is the value indicating that the distance value is set in inches
const DistanceInch byte = 10

//DistanceFoot is the value indicating that the distance value is set in feet
const DistanceFoot byte = 11

//DistanceYard is the value indicating that the distance value is set in yards
const DistanceYard byte = 12

//DistanceMile is the value indicating that the distance value is set in miles
const DistanceMile byte = 13

//DistanceNauticalMile is the value indicating that the distance value is set in nautical miles
const DistanceNauticalMile byte = 14

//DistanceMillimeter is the value indicating that the distance value is set in millimeters
const DistanceMillimeter byte = 15

//DistanceCentimeter is the value indicating that the distance value is set in centimeters
const DistanceCentimeter byte = 16

//DistanceMeter is the value indicating that the distance value is set in meters
const DistanceMeter byte = 17

//DistanceKilometer is the value indicating that the distance value is set in kilometers
const DistanceKilometer byte = 18

//DistanceLine is the value indicating that the distance value is set in lines (1/10 of inch)
const DistanceLine byte = 19

//Distance structure keeps the The distance value
type Distance struct {
	value        float64
	defaultUnits byte
}

func distanceToDefault(value float64, units byte) (float64, error) {
	switch units {
	case DistanceInch:
		return value, nil
	case DistanceFoot:
		return value * 12, nil
	case DistanceYard:
		return value * 36, nil
	case DistanceMile:
		return value * 63360, nil
	case DistanceNauticalMile:
		return value * 72913.3858, nil
	case DistanceLine:
		return value / 10, nil
	case DistanceMillimeter:
		return value / 25.4, nil
	case DistanceCentimeter:
		return value / 2.54, nil
	case DistanceMeter:
		return value / 25.4 * 1000, nil
	case DistanceKilometer:
		return value / 25.4 * 1000000, nil
	default:
		return 0, fmt.Errorf("Distance: unit %d is not supported", units)
	}

}

func distanceFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case DistanceInch:
		return value, nil
	case DistanceFoot:
		return value / 12, nil
	case DistanceYard:
		return value / 36, nil
	case DistanceMile:
		return value / 63360, nil
	case DistanceNauticalMile:
		return value / 72913.3858, nil
	case DistanceLine:
		return value * 10, nil
	case DistanceMillimeter:
		return value * 25.4, nil
	case DistanceCentimeter:
		return value * 2.54, nil
	case DistanceMeter:
		return value * 25.4 / 1000, nil
	case DistanceKilometer:
		return value * 25.4 / 1000000, nil
	default:
		return 0, fmt.Errorf("Distance: unit %d is not supported", units)
	}
}

//CreateDistance creates a distance value.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
func CreateDistance(value float64, units byte) (Distance, error) {
	v, err := distanceToDefault(value, units)
	if err != nil {
		return Distance{}, err
	}
	return Distance{value: v, defaultUnits: units}, nil

}

//MustCreateDistance creates the distance value but panics instead of returned a error
func MustCreateDistance(value float64, units byte) Distance {
	v, err := CreateDistance(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the distance in the specified units.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Distance) Value(units byte) (float64, error) {
	return distanceFromDefault(v.value, units)
}

//Convert converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Distance_* constants.
func (v Distance) Convert(units byte) Distance {
	return Distance{value: v.value, defaultUnits: units}
}

//In converts the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Distance) In(units byte) float64 {
	x, e := distanceFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x
}

func (v Distance) String() string {
	x, e := distanceFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case DistanceInch:
		unitName = "\""
		accuracy = 1
	case DistanceFoot:
		unitName = "'"
		accuracy = 2
	case DistanceYard:
		unitName = "yd"
		accuracy = 3
	case DistanceMile:
		unitName = "mi"
		accuracy = 3
	case DistanceNauticalMile:
		unitName = "nm"
		accuracy = 3
	case DistanceLine:
		unitName = "ln"
		accuracy = 1
	case DistanceMillimeter:
		unitName = "mm"
		accuracy = 0
	case DistanceCentimeter:
		unitName = "cm"
		accuracy = 1
	case DistanceMeter:
		unitName = "m"
		accuracy = 2
	case DistanceKilometer:
		unitName = "km"
		accuracy = 3
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Distance) Units() byte {
	return v.defaultUnits
}
