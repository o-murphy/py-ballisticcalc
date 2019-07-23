package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

type ShotParameters struct {
	sightAngle      unit.Angular
	shotAngle       unit.Angular
	cantAngle       unit.Angular
	maximumDistance unit.Distance
	step            unit.Distance
}

func CreateShotParameters(sightAngle unit.Angular, maxDistance unit.Distance, step unit.Distance) ShotParameters {
	return ShotParameters{
		sightAngle:      sightAngle,
		shotAngle:       unit.MustCreateAngular(0, unit.Angular_Radian),
		cantAngle:       unit.MustCreateAngular(0, unit.Angular_Radian),
		maximumDistance: maxDistance,
		step:            step,
	}
}

func (v ShotParameters) SightAngle() unit.Angular {
	return v.sightAngle
}

func (v ShotParameters) ShotAngle() unit.Angular {
	return v.shotAngle
}

func (v ShotParameters) CantAngle() unit.Angular {
	return v.cantAngle
}

func (v ShotParameters) MaximumDistance() unit.Distance {
	return v.maximumDistance
}

func (v ShotParameters) Step() unit.Distance {
	return v.step
}

func CreateShotParameterUnlevel(sightAngle unit.Angular, maxDistance unit.Distance, step unit.Distance, shotAngle unit.Angular, cantAngle unit.Angular) ShotParameters {
	return ShotParameters{
		sightAngle:      sightAngle,
		shotAngle:       shotAngle,
		cantAngle:       cantAngle,
		maximumDistance: maxDistance,
		step:            step,
	}
}
