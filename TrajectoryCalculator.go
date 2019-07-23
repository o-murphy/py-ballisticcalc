package go_ballisticcalc

import (
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/vector"
)

const cZERO_FINDING_ACCURACY float64 = 0.000005
const cMINIMIM_VELOCITY float64 = 50.0
const cMAXIMUM_DROP float64 = -15000
const cMAX_ITERATIONS_COUNT int = 10
const cGRAVITY_CONSTANT float64 = -32.17405

type TrajectoryCalculator struct {
	maximumCalculatorStepSize unit.Distance
}

func (v TrajectoryCalculator) MaximumCalculatorStepSize() unit.Distance {
	return v.maximumCalculatorStepSize
}

func (v *TrajectoryCalculator) SetMaximumCalculatorStepSize(x unit.Distance) {
	v.maximumCalculatorStepSize = x
}

func (v TrajectoryCalculator) getCalculationStep(step float64) float64 {
	step = step / 2 //do it twice for increased accuracy of velocity calculation and 10 times per step

	var maximumStep float64 = v.maximumCalculatorStepSize.In(unit.Distance_Foot)
	if step > maximumStep {

		var stepOrder int = int(math.Floor(math.Log10(step)))
		var maximumOrder int = int(math.Floor(math.Log10(maximumStep)))

		step = step / math.Pow(10, float64(stepOrder-maximumOrder+1))
	}
	return step
}

func CreateTrajectoryCalculator() TrajectoryCalculator {
	return TrajectoryCalculator{
		maximumCalculatorStepSize: unit.MustCreateDistance(1, unit.Distance_Foot),
	}
}

//Calculates the sight angle for a rifle with scope height specified and zeroed using the ammo specified at
//the range specified and under the conditions (atmosphere) specified.
//
//The calculated value is to be used as sightAngle parameter of the ShotParameters structure
func (v TrajectoryCalculator) SightAngle(ammunition Ammunition, weapon Weapon, atmosphere Atmosphere) unit.Angular {
	var calculationStep float64 = v.getCalculationStep(unit.MustCreateDistance(10, weapon.Zero().ZeroDistance().Units()).In(unit.Distance_Foot))

	var deltaRangeVector, rangeVector, velocityVector, gravityVector vector.Vector
	var muzzleVelocity, velocity, barrelAzimuth, barrelElevation float64
	var densityFactor, mach, drag, zeroFindingError float64
	var time, deltaTime float64
	var maximumRange float64

	mach = atmosphere.Mach().In(unit.Velocity_FPS)
	densityFactor = atmosphere.DensityFactor()
	muzzleVelocity = ammunition.MuzzleVelocity().In(unit.Velocity_FPS)
	barrelAzimuth = 0.0
	barrelElevation = 0

	zeroFindingError = cZERO_FINDING_ACCURACY * 2
	var iterationsCount int = 0

	gravityVector = vector.Create(0, cGRAVITY_CONSTANT, 0)
	for zeroFindingError > cZERO_FINDING_ACCURACY && iterationsCount < cMAX_ITERATIONS_COUNT {
		velocity = muzzleVelocity
		time = 0.0

		//x - distance towards target,
		//y - drop and
		//z - windage
		rangeVector = vector.Create(0.0, -weapon.SightHeight().In(unit.Distance_Foot), 0)
		velocityVector = vector.Create(math.Cos(barrelElevation)*math.Cos(barrelAzimuth), math.Sin(barrelElevation), math.Cos(barrelElevation)*math.Sin(barrelAzimuth)).MultiplyByConst(velocity)
		var zeroDistance float64 = weapon.Zero().ZeroDistance().In(unit.Distance_Foot)
		maximumRange = zeroDistance + calculationStep

		for rangeVector.X <= maximumRange {
			if velocity < cMINIMIM_VELOCITY || rangeVector.Y < cMAXIMUM_DROP {
				break
			}

			deltaTime = calculationStep / velocityVector.X
			velocity = velocityVector.Magnitude()
			drag = densityFactor * velocity * ammunition.Bullet().BallisticCoefficient().Drag(velocity/mach)
			velocityVector = velocityVector.Subtract((velocityVector.MultiplyByConst(drag).Subtract(gravityVector)).MultiplyByConst(deltaTime))
			deltaRangeVector = vector.Create(calculationStep, velocityVector.Y*deltaTime, velocityVector.Z*deltaTime)
			rangeVector = rangeVector.Add(deltaRangeVector)
			velocity = velocityVector.Magnitude()
			time = time + deltaRangeVector.Magnitude()/velocity

			if math.Abs(rangeVector.X-zeroDistance) < 0.5*calculationStep {
				zeroFindingError = math.Abs(rangeVector.Y)
				barrelElevation = barrelElevation - rangeVector.Y/rangeVector.X
				break
			}
		}
		iterationsCount++
	}
	return unit.MustCreateAngular(barrelElevation, unit.Angular_Radian)
}

func (v TrajectoryCalculator) Trajectory(ammunition Ammunition, weapon Weapon, atmosphere Atmosphere, shotInfo ShotParameters, windInfo []WindInfo) []TrajectoryData {
	var rangeTo float64 = shotInfo.MaximumDistance().In(unit.Distance_Foot)
	var step float64 = shotInfo.Step().In(unit.Distance_Foot)

	var calculationStep float64 = v.getCalculationStep(step)

	var deltaRangeVector, rangeVector, velocityAdjusted, velocityVector, windVector, gravityVector vector.Vector
	var muzzleVelocity, velocity, barrelAzimuth, barrelElevation float64
	var densityFactor, mach, drag float64
	var time, deltaTime float64
	var maximumRange, nextRangeDistance float64
	var bulletWeight float64

	bulletWeight = ammunition.Bullet().BulletWeight().In(unit.Weight_Grain)

	var stabilityCoefficient float64 = 1.0
	var calculateDrift bool = false

	if weapon.HasTwist() && ammunition.Bullet().HasDimensions() {
		stabilityCoefficient = calculateStabilityCoefficient(ammunition, weapon, atmosphere)
		calculateDrift = true
	}

	var rangesLength = int(math.Floor(rangeTo/step)) + 1
	var ranges []TrajectoryData = make([]TrajectoryData, rangesLength)

	barrelAzimuth = 0.0
	barrelElevation = shotInfo.SightAngle().In(unit.Angular_Radian)

	mach = atmosphere.Mach().In(unit.Velocity_FPS)
	densityFactor = atmosphere.DensityFactor()
	var currentWind int = 0
	var nextWindRange float64 = 1e7

	if len(windInfo) < 1 {
		windVector = vector.Create(0, 0, 0)
	} else {
		if len(windInfo) > 1 {
			nextWindRange = windInfo[0].untilDistance.In(unit.Distance_Foot)
		}
		windVector = windToVector(shotInfo, windInfo[0])
	}

	muzzleVelocity = ammunition.MuzzleVelocity().In(unit.Velocity_FPS)
	gravityVector = vector.Create(0, cGRAVITY_CONSTANT, 0)
	velocity = muzzleVelocity
	time = 0.0

	//x - distance towards target,
	//y - drop and
	//z - windage
	rangeVector = vector.Create(0.0, -weapon.SightHeight().In(unit.Distance_Foot), 0)
	velocityVector = vector.Create(math.Cos(barrelElevation)*math.Cos(barrelAzimuth), math.Sin(barrelElevation), math.Cos(barrelElevation)*math.Sin(barrelAzimuth)).MultiplyByConst(velocity)

	var currentItem int = 0
	maximumRange = rangeTo
	nextRangeDistance = 0

	var twistCoefficient float64 = 0

	if calculateDrift {
		if weapon.Twist().Direction() == Twist_Left {
			twistCoefficient = 1
		} else {
			twistCoefficient = -1
		}
	}

	//run all the way down the range
	for rangeVector.X <= maximumRange+calculationStep {
		if velocity < cMINIMIM_VELOCITY || rangeVector.Y < cMAXIMUM_DROP {
			break
		}

		if rangeVector.X >= nextWindRange {
			currentWind++
			windVector = windToVector(shotInfo, windInfo[currentWind])

			if currentWind == len(windInfo)-1 {
				nextWindRange = 1e7
			} else {
				nextWindRange = windInfo[currentWind].untilDistance.In(unit.Distance_Foot)
			}
		}

		if rangeVector.X >= nextRangeDistance {
			var windage float64 = rangeVector.Z
			if calculateDrift {
				windage += (1.25 * (stabilityCoefficient + 1.2) * math.Pow(time, 1.83) * twistCoefficient) / 12.0
			}

			var dropAdjustment float64 = getCorrection(rangeVector.X, rangeVector.Y)
			var windageAdjustment float64 = getCorrection(rangeVector.X, windage)

			ranges[currentItem] = TrajectoryData{
				time:              Timespan{time: time},
				travelDistance:    unit.MustCreateDistance(rangeVector.X, unit.Distance_Foot),
				drop:              unit.MustCreateDistance(rangeVector.Y, unit.Distance_Foot),
				dropAdjustment:    unit.MustCreateAngular(dropAdjustment, unit.Angular_Radian),
				windage:           unit.MustCreateDistance(windage, unit.Distance_Foot),
				windageAdjustment: unit.MustCreateAngular(windageAdjustment, unit.Angular_Radian),
				velocity:          unit.MustCreateVelocity(velocity, unit.Velocity_FPS),
				mach:              velocity / mach,
				energy:            unit.MustCreateEnergy(calculateEnergy(bulletWeight, velocity), unit.Energy_FootPound),
				optimalGameWeight: unit.MustCreateWeight(calculateOgv(bulletWeight, velocity), unit.Weight_Pound),
			}
			nextRangeDistance += step
			currentItem++
			if currentItem == len(ranges) {
				break
			}
		}

		deltaTime = calculationStep / velocityVector.X
		velocityAdjusted = velocityVector.Subtract(windVector)
		velocity = velocityAdjusted.Magnitude()
		drag = densityFactor * velocity * ammunition.Bullet().BallisticCoefficient().Drag(velocity/mach)
		velocityVector = velocityVector.Subtract((velocityAdjusted.MultiplyByConst(drag).Subtract(gravityVector)).MultiplyByConst(deltaTime))
		deltaRangeVector = vector.Create(calculationStep, velocityVector.Y*deltaTime, velocityVector.Z*deltaTime)
		rangeVector = rangeVector.Add(deltaRangeVector)
		velocity = velocityVector.Magnitude()
		time = time + deltaRangeVector.Magnitude()/velocity
	}
	return ranges
}

func calculateStabilityCoefficient(ammunitionInfo Ammunition, rifleInfo Weapon, atmosphere Atmosphere) float64 {
	var weight float64 = ammunitionInfo.Bullet().BulletWeight().In(unit.Weight_Grain)
	var diameter float64 = ammunitionInfo.Bullet().BulletDiameter().In(unit.Distance_Inch)
	var twist float64 = rifleInfo.Twist().Twist().In(unit.Distance_Inch) / diameter
	var length float64 = ammunitionInfo.Bullet().BulletLength().In(unit.Distance_Inch) / diameter
	var sd = 30 * weight / (math.Pow(twist, 2) * math.Pow(diameter, 3) * length * (1 + math.Pow(length, 2)))
	var fv = math.Pow(ammunitionInfo.MuzzleVelocity().In(unit.Velocity_FPS)/2800, 1.0/3.0)

	var ft float64 = atmosphere.Temperature().In(unit.Temperature_Fahrenheit)
	var pt float64 = atmosphere.Pressure().In(unit.Pressure_InHg)
	var ftp float64 = ((ft + 460) / (59 + 460)) * (29.92 / pt)

	return sd * fv * ftp
}

func windToVector(shot ShotParameters, wind WindInfo) vector.Vector {
	var sightCosine float64 = math.Cos(shot.SightAngle().In(unit.Angular_Radian))
	var sightSine float64 = math.Sin(shot.SightAngle().In(unit.Angular_Radian))
	var cantCosine float64 = math.Cos(shot.CantAngle().In(unit.Angular_Radian))
	var cantSine float64 = math.Sin(shot.CantAngle().In(unit.Angular_Radian))
	var rangeVelocity float64 = wind.velocity.In(unit.Velocity_FPS) * math.Cos(wind.direction.In(unit.Angular_Radian))
	var crossComponent float64 = wind.velocity.In(unit.Velocity_FPS) * math.Sin(wind.direction.In(unit.Angular_Radian))
	var rangeFactor float64 = -rangeVelocity * sightSine
	return vector.Create(rangeVelocity*sightCosine, rangeFactor*cantCosine+crossComponent*cantSine, crossComponent*cantCosine-rangeFactor*cantSine)
}

func getCorrection(distance, offset float64) float64 {
	return math.Atan(offset / distance)
}

func calculateEnergy(bulletWeight, velocity float64) float64 {
	return bulletWeight * math.Pow(velocity, 2) / 450400
}

func calculateOgv(bulletWeight, velocity float64) float64 {
	return math.Pow(bulletWeight, 2) * math.Pow(velocity, 3) * 1.5e-12
}
