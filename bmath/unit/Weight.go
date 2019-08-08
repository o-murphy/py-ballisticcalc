package unit

import "fmt"

//WeightGrain is the value indicating that weight value is expressed in grains
const WeightGrain byte = 70

//WeightOunce is the value indicating that weight value is expressed in ounces
const WeightOunce byte = 71

//WeightGram is the value indicating that weight value is expressed in grams
const WeightGram byte = 72

//WeightPound is the value indicating that weight value is expressed in pounds
const WeightPound byte = 73

//WeightKilogram is the value indicating that weight value is expressed in kilograms
const WeightKilogram byte = 74

//WeightNewton is the value indicating that weight value is expressed in newtons of power
const WeightNewton byte = 75

func weightToDefault(value float64, units byte) (float64, error) {
	switch units {
	case WeightGrain:
		return value, nil
	case WeightGram:
		return value * 15.4323584, nil
	case WeightKilogram:
		return value * 15432.3584, nil
	case WeightNewton:
		return value * 151339.73750336, nil
	case WeightPound:
		return value / 0.000142857143, nil
	case WeightOunce:
		return value * 437.5, nil
	default:
		return 0, fmt.Errorf("Weight: unit %d is not supported", units)

	}
}

func weightFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case WeightGrain:
		return value, nil
	case WeightGram:
		return value / 15.4323584, nil
	case WeightKilogram:
		return value / 15432.3584, nil
	case WeightNewton:
		return value / 151339.73750336, nil
	case WeightPound:
		return value * 0.000142857143, nil
	case WeightOunce:
		return value / 437.5, nil
	default:
		return 0, fmt.Errorf("Weight: unit %d is not supported", units)

	}
}

//Weight structure keeps data about weight
type Weight struct {
	value        float64
	defaultUnits byte
}

//CreateWeight creates a weight value.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
func CreateWeight(value float64, units byte) (Weight, error) {
	v, err := weightToDefault(value, units)
	if err != nil {
		return Weight{}, err
	}
	return Weight{value: v, defaultUnits: units}, nil

}

//MustCreateWeight creates the weight value but panics instead of return error
func MustCreateWeight(value float64, units byte) Weight {
	v, err := CreateWeight(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Value returns the value of the weight in the specified units.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Weight) Value(units byte) (float64, error) {
	return weightFromDefault(v.value, units)
}

//Convert returns the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
func (v Weight) Convert(units byte) Weight {
	return Weight{value: v.value, defaultUnits: units}
}

//In converts the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Weight) In(units byte) float64 {
	x, e := weightFromDefault(v.value, units)
	if e != nil {
		return 0
	}
	return x

}

func (v Weight) String() string {
	x, e := weightFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	}
	var unitName, format string
	var accuracy int
	switch v.defaultUnits {
	case WeightGrain:
		unitName = "gr"
		accuracy = 0
	case WeightGram:
		unitName = "g"
		accuracy = 1
	case WeightKilogram:
		unitName = "kg"
		accuracy = 3
	case WeightNewton:
		unitName = "N"
		accuracy = 3
	case WeightPound:
		unitName = "lb"
		accuracy = 3
	case WeightOunce:
		unitName = "oz"
		accuracy = 1
	default:
		unitName = "?"
		accuracy = 6
	}
	format = fmt.Sprintf("%%.%df%%s", accuracy)
	return fmt.Sprintf(format, x, unitName)

}

//Units return the units in which the value is measured
func (v Weight) Units() byte {
	return v.defaultUnits
}
