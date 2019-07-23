package go_ballisticcalc

import (
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

type Timespan struct {
	time float64
}

func (v Timespan) TotalSeconds() float64 {
	return v.time
}

func (v Timespan) Seconds() float64 {
	return math.Mod(math.Floor(v.time), 60)
}

func (v Timespan) Minutes() float64 {
	return math.Mod(math.Floor(v.time/60), 60)
}

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

func (v TrajectoryData) Time() Timespan {
	return v.time
}

func (v TrajectoryData) TravelledDistance() unit.Distance {
	return v.travelDistance
}

func (v TrajectoryData) Velocity() unit.Velocity {
	return v.velocity
}

func (v TrajectoryData) MachVelocity() float64 {
	return v.mach
}

func (v TrajectoryData) Drop() unit.Distance {
	return v.drop
}

func (v TrajectoryData) DropAdjustment() unit.Angular {
	return v.dropAdjustment
}

func (v TrajectoryData) Windage() unit.Distance {
	return v.windage
}

func (v TrajectoryData) WindageAdjustment() unit.Angular {
	return v.windageAdjustment
}

func (v TrajectoryData) Energy() unit.Energy {
	return v.energy
}

func (v TrajectoryData) OptimalGameWeight() unit.Weight {
	return v.optimalGameWeight
}
