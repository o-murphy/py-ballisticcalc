package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

type WindInfo struct {
	untilDistance unit.Distance
	velocity      unit.Velocity
	direction     unit.Angular
}

func (v WindInfo) UntilDistance() unit.Distance {
	return v.untilDistance
}

func (v WindInfo) Velocity() unit.Velocity {
	return v.velocity
}

func (v WindInfo) Direction() unit.Angular {
	return v.direction
}

func CreateNoWind() []WindInfo {
	return make([]WindInfo, 1)
}

func CreateOnlyWindInfo(windVelocity unit.Velocity, direction unit.Angular) []WindInfo {
	w := WindInfo{
		untilDistance: unit.MustCreateDistance(9999, unit.Distance_Kilometer),
		velocity:      windVelocity,
		direction:     direction,
	}
	a := make([]WindInfo, 1)
	a[0] = w
	return a

}

func AddWindInfo(untilRange unit.Distance, windVelocity unit.Velocity, direction unit.Angular) WindInfo {
	w := WindInfo{
		untilDistance: untilRange,
		velocity:      windVelocity,
		direction:     direction,
	}
	return w
}

func CreateWindInfo(winds ...WindInfo) []WindInfo {
	return winds
}
