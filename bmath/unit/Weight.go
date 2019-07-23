package unit

import "fmt"

const Weight_Grain byte = 70
const Weight_Ounce byte = 71
const Weight_Gram byte = 72
const Weight_Pound byte = 73
const Weight_Kilogram byte = 74
const Weight_Newton byte = 75

func weightToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Weight_Grain:
		return value, nil
	case Weight_Gram:
		return value * 15.4323584, nil
	case Weight_Kilogram:
		return value * 15432.3584, nil
	case Weight_Newton:
		return value * 151339.73750336, nil
	case Weight_Pound:
		return value / 0.000142857143, nil
	case Weight_Ounce:
		return value * 437.5, nil
	default:
		return 0, fmt.Errorf("Weight: unit %d is not supported", units)

	}
}

func weightFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Weight_Grain:
		return value, nil
	case Weight_Gram:
		return value / 15.4323584, nil
	case Weight_Kilogram:
		return value / 15432.3584, nil
	case Weight_Newton:
		return value / 151339.73750336, nil
	case Weight_Pound:
		return value * 0.000142857143, nil
	case Weight_Ounce:
		return value / 437.5, nil
	default:
		return 0, fmt.Errorf("Weight: unit %d is not supported", units)

	}
}

//The weight
type Weight struct {
	value        float64
	defaultUnits byte
}

//Creates a weight value.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
func CreateWeight(value float64, units byte) (Weight, error) {
	v, err := weightToDefault(value, units)
	if err != nil {
		return Weight{}, err
	} else {
		return Weight{value: v, defaultUnits: units}, nil
	}
}

func MustCreateWeight(value float64, units byte) Weight {
	v, err := CreateWeight(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Returns the value of the weight in the specified units.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Weight) Value(units byte) (float64, error) {
	return weightFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Weight_* constants.
func (v Weight) Convert(units byte) Weight {
	return Weight{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Weight) In(units byte) float64 {
	x, e := weightFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Weight) String() string {
	x, e := weightFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Weight_Grain:
			unitName = "gr"
			accuracy = 0
		case Weight_Gram:
			unitName = "g"
			accuracy = 1
		case Weight_Kilogram:
			unitName = "kg"
			accuracy = 3
		case Weight_Newton:
			unitName = "N"
			accuracy = 3
		case Weight_Pound:
			unitName = "lb"
			accuracy = 3
		case Weight_Ounce:
			unitName = "oz"
			accuracy = 1
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}

func (v Weight) Units() byte {
	return v.defaultUnits
}
