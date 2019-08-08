package go_ballisticcalc

import (
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

//Timespan keeps the amount of time spent
type Timespan struct {
	time float64
}

//TotalSeconds returns the total number of seconds
func (v Timespan) TotalSeconds() float64 {
	return v.time
}

//Seconds return the whole number of the seconds
func (v Timespan) Seconds() float64 {
	return math.Mod(math.Floor(v.time), 60)
}

//Minutes return the whole number of minutes
func (v Timespan) Minutes() float64 {
	return math.Mod(math.Floor(v.time/60), 60)
}

//TrajectoryData structure keeps information about one point of the trajectory.
type TrajectoryData struct {
	time              Timespan
	travelDistance    unit.Distance
	velocity          unit.Velocity
	mach              float64
	drop              unit.Distance
	dropAdjustment    unit.Angular
	windage           unit.Distance
	windageAdjustment unit.Angular
	energy            unit.Energy
	optimalGameWeight unit.Weight
}

//Time return the amount of time spent since the shot moment
func (v TrajectoryData) Time() Timespan {
	return v.time
}

//TravelledDistance returns the distance measured between the muzzle and the projection of the current bullet position to
//the line between the muzzle and the target
func (v TrajectoryData) TravelledDistance() unit.Distance {
	return v.travelDistance
}

//Velocity returns the current projectile velocity
func (v TrajectoryData) Velocity() unit.Velocity {
	return v.velocity
}

//MachVelocity returns the proportion between the current projectile velocity and the speed of the sound
func (v TrajectoryData) MachVelocity() float64 {
	return v.mach
}

//Drop returns the shorted distance between the projectile and the shot line
//
//The positive value means the the projectile is above this line and the negative value means that the projectile
//is below this line
func (v TrajectoryData) Drop() unit.Distance {
	return v.drop
}

//DropAdjustment returns the angle between the shot line and the line from the muzzle to the current projectile position
//in the plane perpendicular to the ground
func (v TrajectoryData) DropAdjustment() unit.Angular {
	return v.dropAdjustment
}

//Windage returns the distance to which the projectile is displaced by wind
func (v TrajectoryData) Windage() unit.Distance {
	return v.windage
}

//WindageAdjustment returns the angle between the shot line and the line from the muzzle to the current projectile position
//in the place parallel to the ground
func (v TrajectoryData) WindageAdjustment() unit.Angular {
	return v.windageAdjustment
}

//Energy returns the kinetic energy of the projectile
func (v TrajectoryData) Energy() unit.Energy {
	return v.energy
}

//OptimalGameWeight returns the weight of game to which a kill shot is
//probable with the kinetic energy that the projectile currently  have
func (v TrajectoryData) OptimalGameWeight() unit.Weight {
	return v.optimalGameWeight
}
