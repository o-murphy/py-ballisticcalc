package go_ballisticcalc

import (
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/vector"
)

const cZeroFindingAccuracy float64 = 0.000005
const cMinimumVelocity float64 = 50.0
const cMaximumDrop float64 = -15000
const cMaxIterations int = 10
const cGravityConstant float64 = -32.17405

//TrajectoryCalculator table is used to calculate the trajectory of a projectile shot with the parameters specified
type TrajectoryCalculator struct {
	maximumCalculatorStepSize unit.Distance
}

//MaximumCalculatorStepSize returns the maximum size of one calculation iteration.
func (v TrajectoryCalculator) MaximumCalculatorStepSize() unit.Distance {
	return v.maximumCalculatorStepSize
}

//SetMaximumCalculatorStepSize sets the maximum size of one calculation iteration.
//
//As the generic rule, the maximum step of the calculation must not be greater than
//a half of the step used in the short parameter. The smaller value is, the calculation is more precise but
//takes more time to calculate. From practical standpoint the value in range from 0.5 to 5 feet produces
//good enough accuracy.
func (v *TrajectoryCalculator) SetMaximumCalculatorStepSize(x unit.Distance) {
	v.maximumCalculatorStepSize = x
}

func (v TrajectoryCalculator) getCalculationStep(step float64) float64 {
	step = step / 2 //do it twice for increased accuracy of velocity calculation and 10 times per step

	var maximumStep float64 = v.maximumCalculatorStepSize.In(unit.DistanceFoot)
	if step > maximumStep {

		var stepOrder = int(math.Floor(math.Log10(step)))
		var maximumOrder = int(math.Floor(math.Log10(maximumStep)))

		step = step / math.Pow(10, float64(stepOrder-maximumOrder+1))
	}
	return step
}

//CreateTrajectoryCalculator creates and instance of the trajectory calculator
func CreateTrajectoryCalculator() TrajectoryCalculator {
	return TrajectoryCalculator{
		maximumCalculatorStepSize: unit.MustCreateDistance(1, unit.DistanceFoot),
	}
}

//SightAngle calculates the sight angle for a rifle with scope height specified and zeroed using the ammo specified at
//the range specified and under the conditions (atmosphere) specified.
//
//The calculated value is to be used as sightAngle parameter of the ShotParameters structure
func (v TrajectoryCalculator) SightAngle(ammunition Ammunition, weapon Weapon, atmosphere Atmosphere) unit.Angular {
	var calculationStep = v.getCalculationStep(unit.MustCreateDistance(10, weapon.Zero().ZeroDistance().Units()).In(unit.DistanceFoot))

	var deltaRangeVector, rangeVector, velocityVector, gravityVector vector.Vector
	var muzzleVelocity, velocity, barrelAzimuth, barrelElevation float64
	var densityFactor, mach, drag, zeroFindingError float64
	var time, deltaTime float64
	var maximumRange float64

	mach = atmosphere.Mach().In(unit.VelocityFPS)
	densityFactor = atmosphere.getDensityFactor()
	muzzleVelocity = ammunition.MuzzleVelocity().In(unit.VelocityFPS)
	barrelAzimuth = 0.0
	barrelElevation = 0

	zeroFindingError = cZeroFindingAccuracy * 2
	var iterationsCount int

	gravityVector = vector.Create(0, cGravityConstant, 0)
	for zeroFindingError > cZeroFindingAccuracy && iterationsCount < cMaxIterations {
		velocity = muzzleVelocity
		time = 0.0

		//x - distance towards target,
		//y - drop and
		//z - windage
		rangeVector = vector.Create(0.0, -weapon.SightHeight().In(unit.DistanceFoot), 0)
		velocityVector = vector.Create(math.Cos(barrelElevation)*math.Cos(barrelAzimuth), math.Sin(barrelElevation), math.Cos(barrelElevation)*math.Sin(barrelAzimuth)).MultiplyByConst(velocity)
		var zeroDistance float64 = weapon.Zero().ZeroDistance().In(unit.DistanceFoot)
		maximumRange = zeroDistance + calculationStep

		for rangeVector.X <= maximumRange {
			if velocity < cMinimumVelocity || rangeVector.Y < cMaximumDrop {
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
	return unit.MustCreateAngular(barrelElevation, unit.AngularRadian)
}

//Trajectory calculates the trajectory with the parameters specified
func (v TrajectoryCalculator) Trajectory(ammunition Ammunition, weapon Weapon, atmosphere Atmosphere, shotInfo ShotParameters, windInfo []WindInfo) []TrajectoryData {
	var rangeTo float64 = shotInfo.MaximumDistance().In(unit.DistanceFoot)
	var step float64 = shotInfo.Step().In(unit.DistanceFoot)

	var calculationStep = v.getCalculationStep(step)

	var deltaRangeVector, rangeVector, velocityAdjusted, velocityVector, windVector, gravityVector vector.Vector
	var muzzleVelocity, velocity, barrelAzimuth, barrelElevation float64
	var densityFactor, mach, drag float64
	var time, deltaTime float64
	var maximumRange, nextRangeDistance float64
	var bulletWeight float64

	bulletWeight = ammunition.Bullet().BulletWeight().In(unit.WeightGrain)

	var stabilityCoefficient = 1.0
	var calculateDrift bool

	if weapon.HasTwist() && ammunition.Bullet().HasDimensions() {
		stabilityCoefficient = calculateStabilityCoefficient(ammunition, weapon, atmosphere)
		calculateDrift = true
	}

	var rangesLength = int(math.Floor(rangeTo/step)) + 1
	var ranges = make([]TrajectoryData, rangesLength)

	barrelAzimuth = 0.0
	barrelElevation = shotInfo.SightAngle().In(unit.AngularRadian)
	barrelElevation = barrelElevation + shotInfo.ShotAngle().In(unit.AngularRadian)
	var alt0 float64 = atmosphere.Altitude().In(unit.DistanceFoot)
	densityFactor, mach = atmosphere.getDensityFactorAndMachForAltitude(alt0)
	var currentWind int
	var nextWindRange = 1e7

	if len(windInfo) < 1 {
		windVector = vector.Create(0, 0, 0)
	} else {
		if len(windInfo) > 1 {
			nextWindRange = windInfo[0].untilDistance.In(unit.DistanceFoot)
		}
		windVector = windToVector(shotInfo, windInfo[0])
	}

	muzzleVelocity = ammunition.MuzzleVelocity().In(unit.VelocityFPS)
	gravityVector = vector.Create(0, cGravityConstant, 0)
	velocity = muzzleVelocity
	time = 0.0

	//x - distance towards target,
	//y - drop and
	//z - windage
	rangeVector = vector.Create(0.0, -weapon.SightHeight().In(unit.DistanceFoot), 0)
	velocityVector = vector.Create(math.Cos(barrelElevation)*math.Cos(barrelAzimuth), math.Sin(barrelElevation), math.Cos(barrelElevation)*math.Sin(barrelAzimuth)).MultiplyByConst(velocity)

	var currentItem int
	maximumRange = rangeTo
	nextRangeDistance = 0

	var twistCoefficient float64

	if calculateDrift {
		if weapon.Twist().Direction() == TwistLeft {
			twistCoefficient = 1
		} else {
			twistCoefficient = -1
		}
	}

	//run all the way down the range
	for rangeVector.X <= maximumRange+calculationStep {
		if velocity < cMinimumVelocity || rangeVector.Y < cMaximumDrop {
			break
		}

		densityFactor, mach = atmosphere.getDensityFactorAndMachForAltitude(alt0 + rangeVector.Y)
		//densityFactor = atmosphere.DensityFactor()
		//mach = atmosphere.Mach().In(unit.Velocity_FPS)

		if rangeVector.X >= nextWindRange {
			currentWind++
			windVector = windToVector(shotInfo, windInfo[currentWind])

			if currentWind == len(windInfo)-1 {
				nextWindRange = 1e7
			} else {
				nextWindRange = windInfo[currentWind].untilDistance.In(unit.DistanceFoot)
			}
		}

		if rangeVector.X >= nextRangeDistance {
			var windage float64 = rangeVector.Z
			if calculateDrift {
				windage += (1.25 * (stabilityCoefficient + 1.2) * math.Pow(time, 1.83) * twistCoefficient) / 12.0
			}

			var dropAdjustment = getCorrection(rangeVector.X, rangeVector.Y)
			var windageAdjustment = getCorrection(rangeVector.X, windage)

			ranges[currentItem] = TrajectoryData{
				time:              Timespan{time: time},
				travelDistance:    unit.MustCreateDistance(rangeVector.X, unit.DistanceFoot),
				drop:              unit.MustCreateDistance(rangeVector.Y, unit.DistanceFoot),
				dropAdjustment:    unit.MustCreateAngular(dropAdjustment, unit.AngularRadian),
				windage:           unit.MustCreateDistance(windage, unit.DistanceFoot),
				windageAdjustment: unit.MustCreateAngular(windageAdjustment, unit.AngularRadian),
				velocity:          unit.MustCreateVelocity(velocity, unit.VelocityFPS),
				mach:              velocity / mach,
				energy:            unit.MustCreateEnergy(calculateEnergy(bulletWeight, velocity), unit.EnergyFootPound),
				optimalGameWeight: unit.MustCreateWeight(calculateOgv(bulletWeight, velocity), unit.WeightPound),
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
	var weight float64 = ammunitionInfo.Bullet().BulletWeight().In(unit.WeightGrain)
	var diameter float64 = ammunitionInfo.Bullet().BulletDiameter().In(unit.DistanceInch)
	var twist float64 = rifleInfo.Twist().Twist().In(unit.DistanceInch) / diameter
	var length float64 = ammunitionInfo.Bullet().BulletLength().In(unit.DistanceInch) / diameter
	var sd = 30 * weight / (math.Pow(twist, 2) * math.Pow(diameter, 3) * length * (1 + math.Pow(length, 2)))
	var fv = math.Pow(ammunitionInfo.MuzzleVelocity().In(unit.VelocityFPS)/2800, 1.0/3.0)

	var ft float64 = atmosphere.Temperature().In(unit.TemperatureFahrenheit)
	var pt float64 = atmosphere.Pressure().In(unit.PressureInHg)
	var ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)

	return sd * fv * ftp
}

func windToVector(shot ShotParameters, wind WindInfo) vector.Vector {
	var sightCosine = math.Cos(shot.SightAngle().In(unit.AngularRadian))
	var sightSine = math.Sin(shot.SightAngle().In(unit.AngularRadian))
	var cantCosine = math.Cos(shot.CantAngle().In(unit.AngularRadian))
	var cantSine = math.Sin(shot.CantAngle().In(unit.AngularRadian))
	var rangeVelocity = wind.velocity.In(unit.VelocityFPS) * math.Cos(wind.direction.In(unit.AngularRadian))
	var crossComponent = wind.velocity.In(unit.VelocityFPS) * math.Sin(wind.direction.In(unit.AngularRadian))
	var rangeFactor = -rangeVelocity * sightSine
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
