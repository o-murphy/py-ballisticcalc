package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//ShotParameters struct keeps parameters of the shot to be calculated
type ShotParameters struct {
	sightAngle      unit.Angular
	shotAngle       unit.Angular
	cantAngle       unit.Angular
	maximumDistance unit.Distance
	step            unit.Distance
}

//CreateShotParameters creates parameters of the shot
//
//sightAngle - is the angle between scope centerline and the barrel centerline
func CreateShotParameters(sightAngle unit.Angular, maxDistance unit.Distance, step unit.Distance) ShotParameters {
	return ShotParameters{
		sightAngle:      sightAngle,
		shotAngle:       unit.MustCreateAngular(0, unit.AngularRadian),
		cantAngle:       unit.MustCreateAngular(0, unit.AngularRadian),
		maximumDistance: maxDistance,
		step:            step,
	}
}

//SightAngle returns the angle of the sight
func (v ShotParameters) SightAngle() unit.Angular {
	return v.sightAngle
}

//ShotAngle returns the angle of the short
func (v ShotParameters) ShotAngle() unit.Angular {
	return v.shotAngle
}

//CantAngle returns the cant angle (the angle between centers of scope and the barrel projection and zenith line)
func (v ShotParameters) CantAngle() unit.Angular {
	return v.cantAngle
}

//MaximumDistance returns the maximum distance to be calculated
func (v ShotParameters) MaximumDistance() unit.Distance {
	return v.maximumDistance
}

//Step returns the step between calculation results
func (v ShotParameters) Step() unit.Distance {
	return v.step
}

//CreateShotParameterUnlevel creates the parameter of the shot aimed at the target which is not on th same level
//as the shooter
//
//sightAngle - is the angle between scope centerline and the barrel centerline
//
//shotAngle - is the angle between lines drawn from the shooter to the target and the horizon. The positive angle
//means that the target is higher and the negative angle means that the target is lower
func CreateShotParameterUnlevel(sightAngle unit.Angular, maxDistance unit.Distance, step unit.Distance, shotAngle unit.Angular, cantAngle unit.Angular) ShotParameters {
	return ShotParameters{
		sightAngle:      sightAngle,
		shotAngle:       shotAngle,
		cantAngle:       cantAngle,
		maximumDistance: maxDistance,
		step:            step,
	}
}
