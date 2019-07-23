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

type Angular struct {
	value float64
}

func toRadians(value float64, units byte) (float64, error) {
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

func fromRadians(value float64, units byte) (float64, error) {
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

func CreateAngular(value float64, units byte) (Angular, error) {
	v, err := toRadians(value, units)
	if err != nil {
		return Angular{0}, err
	} else {
		return Angular{value: v}, nil
	}
}

func (v Angular) Value(units byte) (float64, error) {
	return fromRadians(v.value, units)
}

func (v Angular) ValueOrZero(units byte) float64 {
	x, e := fromRadians(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}
