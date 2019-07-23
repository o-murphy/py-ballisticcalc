package unit

import "fmt"

const Energy_FootPound byte = 30
const Energy_Joule byte = 31

func energyToDefault(value float64, units byte) (float64, error) {
	switch units {
	case Energy_FootPound:
		return value, nil
	case Energy_Joule:
		return value * 0.737562149277, nil
	default:
		return 0, fmt.Errorf("Energy: unit %d is not supported", units)
	}
}

func energyFromDefault(value float64, units byte) (float64, error) {
	switch units {
	case Energy_FootPound:
		return value, nil
	case Energy_Joule:
		return value / 0.737562149277, nil
	default:
		return 0, fmt.Errorf("Energy: unit %d is not supported", units)
	}
}

//The energy
type Energy struct {
	value        float64
	defaultUnits byte
}

//Creates a energy value.
//
//units are measurement unit and may be any value from
//unit.Energy_* constants.
func CreateEnergy(value float64, units byte) (Energy, error) {
	v, err := energyToDefault(value, units)
	if err != nil {
		return Energy{}, err
	} else {
		return Energy{value: v, defaultUnits: units}, nil
	}
}

func MustCreateEnergy(value float64, units byte) Energy {
	v, err := CreateEnergy(value, units)
	if err != nil {
		panic(err)
	}
	return v
}

//Returns the value of the energy in the specified units.
//
//units are measurement unit and may be any value from
//unit.Energy_* constants.
//
//The method returns a error in case the unit is
//not supported.
func (v Energy) Value(units byte) (float64, error) {
	return energyFromDefault(v.value, units)
}

//Converts the value into the specified units.
//
//units are measurement unit and may be any value from
//unit.Energy_* constants.
func (v Energy) Convert(units byte) Energy {
	return Energy{value: v.value, defaultUnits: units}
}

//Convert the value in the specified units.
//Returns 0 if unit conversion is not possible.
func (v Energy) In(units byte) float64 {
	x, e := energyFromDefault(v.value, units)
	if e != nil {
		return 0
	} else {
		return x
	}
}

func (v Energy) String() string {
	x, e := energyFromDefault(v.value, v.defaultUnits)
	if e != nil {
		return "!error: default units aren't correct"
	} else {
		var unitName, format string
		var accuracy int
		switch v.defaultUnits {
		case Energy_FootPound:
			unitName = "ft·lb"
			accuracy = 0
		case Energy_Joule:
			unitName = "J"
			accuracy = 0
		default:
			unitName = "?"
			accuracy = 6
		}
		format = fmt.Sprintf("%%.%df%%s", accuracy)
		return fmt.Sprintf(format, x, unitName)
	}
}

func (v Energy) Units() byte {
	return v.defaultUnits
}
