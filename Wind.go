package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//WindInfo structure keeps information about wind
type WindInfo struct {
	untilDistance unit.Distance
	velocity      unit.Velocity
	direction     unit.Angular
}

//UntilDistance returns the distance from the shooter until which the wind blows
func (v WindInfo) UntilDistance() unit.Distance {
	return v.untilDistance
}

//Velocity returns the wind velocity
func (v WindInfo) Velocity() unit.Velocity {
	return v.velocity
}

//Direction returns the wind direction.
//
//0 degrees means wind blowing into the face
//90 degrees means wind blowing from the left
//-90 or 270 degrees means wind blowing from the right
//180 degrees means wind blowing from the back
func (v WindInfo) Direction() unit.Angular {
	return v.direction
}

//CreateNoWind creates wind description with no wind
func CreateNoWind() []WindInfo {
	return make([]WindInfo, 1)
}

//CreateOnlyWindInfo creates the wind information for the constant wind for the whole distance of the shot
func CreateOnlyWindInfo(windVelocity unit.Velocity, direction unit.Angular) []WindInfo {
	w := WindInfo{
		untilDistance: unit.MustCreateDistance(9999, unit.DistanceKilometer),
		velocity:      windVelocity,
		direction:     direction,
	}
	a := make([]WindInfo, 1)
	a[0] = w
	return a

}

//AddWindInfo creates description of one wind
func AddWindInfo(untilRange unit.Distance, windVelocity unit.Velocity, direction unit.Angular) WindInfo {
	w := WindInfo{
		untilDistance: untilRange,
		velocity:      windVelocity,
		direction:     direction,
	}
	return w
}

//CreateWindInfo creates a wind descriptor from multiple winds
//
//winds must be ordered from the closest to the muzzlepoint to the farest to the muzzlepoint
func CreateWindInfo(winds ...WindInfo) []WindInfo {
	return winds
}
