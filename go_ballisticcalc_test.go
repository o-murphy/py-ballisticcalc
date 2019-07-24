package go_ballisticcalc_test

import (
	"math"
	"testing"

	"github.com/gehtsoft-usa/go_ballisticcalc"
	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

func TestZero1(t *testing.T) {
	bc, _ := go_ballisticcalc.CreateBallisticCoefficient(0.365, go_ballisticcalc.DragTable_G1)
	projectile := go_ballisticcalc.CreateProjectile(bc, unit.MustCreateWeight(69, unit.Weight_Grain))
	ammo := go_ballisticcalc.CreateAmmunition(projectile, unit.MustCreateVelocity(2600, unit.Velocity_FPS))
	zero := go_ballisticcalc.CreateZeroInfo(unit.MustCreateDistance(100, unit.Distance_Yard))
	weapon := go_ballisticcalc.CreateWeapon(unit.MustCreateDistance(3.2, unit.Distance_Inch), zero)
	atmosphere := go_ballisticcalc.CreateDefaultAtmosphere()
	calc := go_ballisticcalc.CreateTrajectoryCalculator()

	sightAngle := calc.SightAngle(ammo, weapon, atmosphere)
	if math.Abs(sightAngle.In(unit.Angular_Radian)-0.001651) > 1e-6 {
		t.Errorf("TestZero1 failed %.10f", sightAngle.In(unit.Angular_Radian))
	}
}

func TestZero2(t *testing.T) {
	bc, _ := go_ballisticcalc.CreateBallisticCoefficient(0.223, go_ballisticcalc.DragTable_G7)
	projectile := go_ballisticcalc.CreateProjectile(bc, unit.MustCreateWeight(168, unit.Weight_Grain))
	ammo := go_ballisticcalc.CreateAmmunition(projectile, unit.MustCreateVelocity(2750, unit.Velocity_FPS))
	zero := go_ballisticcalc.CreateZeroInfo(unit.MustCreateDistance(100, unit.Distance_Yard))
	weapon := go_ballisticcalc.CreateWeapon(unit.MustCreateDistance(2, unit.Distance_Inch), zero)
	atmosphere := go_ballisticcalc.CreateDefaultAtmosphere()

	calc := go_ballisticcalc.CreateTrajectoryCalculator()

	sightAngle := calc.SightAngle(ammo, weapon, atmosphere)
	if math.Abs(sightAngle.In(unit.Angular_Radian)-0.001228) > 1e-6 {
		t.Errorf("TestZero1 failed %.10f", sightAngle.In(unit.Angular_Radian))
	}
}

func assertEqual(t *testing.T, a, b, accuracy float64, name string) {
	if math.Abs(a-b) > accuracy {
		t.Errorf("Assertion %s failed (%f/%f)", name, a, b)
	}
}

func validateOne(t *testing.T, data go_ballisticcalc.TrajectoryData,
	distance, velocity, mach, energy, path, hold, windage, windAdjustment, time, ogv float64,
	adjustmentUnit byte) {
	assertEqual(t, distance, data.TravelledDistance().In(unit.Distance_Yard), 0.001, "Distance")
	assertEqual(t, velocity, data.Velocity().In(unit.Velocity_FPS), 5, "Velocity")
	assertEqual(t, mach, data.MachVelocity(), 0.005, "Mach")
	assertEqual(t, energy, data.Energy().In(unit.Energy_FootPound), 5, "Energy")
	assertEqual(t, time, data.Time().TotalSeconds(), 0.06, "Time")
	assertEqual(t, ogv, data.OptimalGameWeight().In(unit.Weight_Pound), 1, "OGV")

	if distance >= 800 {
		assertEqual(t, path, data.Drop().In(unit.Distance_Inch), 4, "Drop")
	} else if distance >= 500 {
		assertEqual(t, path, data.Drop().In(unit.Distance_Inch), 1, "Drop")
	} else {
		assertEqual(t, path, data.Drop().In(unit.Distance_Inch), 0.5, "Drop")
	}

	if distance > 1 {
		assertEqual(t, hold, data.DropAdjustment().In(adjustmentUnit), 0.5, "Hold")
	}

	if distance >= 800 {
		assertEqual(t, windage, data.Windage().In(unit.Distance_Inch), 1.5, "Windage")
	} else if distance >= 500 {
		assertEqual(t, windage, data.Windage().In(unit.Distance_Inch), 1, "Windage")
	} else {
		assertEqual(t, windage, data.Windage().In(unit.Distance_Inch), 0.5, "Windage")
	}

	if distance > 1 {
		assertEqual(t, windAdjustment, data.WindageAdjustment().In(adjustmentUnit), 0.5, "WAdj")
	}
}

func TestPathG1(t *testing.T) {
	bc, _ := go_ballisticcalc.CreateBallisticCoefficient(0.223, go_ballisticcalc.DragTable_G1)
	projectile := go_ballisticcalc.CreateProjectile(bc, unit.MustCreateWeight(168, unit.Weight_Grain))
	ammo := go_ballisticcalc.CreateAmmunition(projectile, unit.MustCreateVelocity(2750, unit.Velocity_FPS))
	zero := go_ballisticcalc.CreateZeroInfo(unit.MustCreateDistance(100, unit.Distance_Yard))
	weapon := go_ballisticcalc.CreateWeapon(unit.MustCreateDistance(2, unit.Distance_Inch), zero)
	atmosphere := go_ballisticcalc.CreateDefaultAtmosphere()
	shotInfo := go_ballisticcalc.CreateShotParameters(unit.MustCreateAngular(0.001228, unit.Angular_Radian),
		unit.MustCreateDistance(1000, unit.Distance_Yard),
		unit.MustCreateDistance(100, unit.Distance_Yard))
	wind := go_ballisticcalc.CreateOnlyWindInfo(unit.MustCreateVelocity(5, unit.Velocity_MPH),
		unit.MustCreateAngular(-45, unit.Angular_Degree))

	calc := go_ballisticcalc.CreateTrajectoryCalculator()
	data := calc.Trajectory(ammo, weapon, atmosphere, shotInfo, wind)

	assertEqual(t, float64(len(data)), 11, 0.1, "Length")

	validateOne(t, data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.Angular_MOA)
	validateOne(t, data[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, unit.Angular_MOA)
	validateOne(t, data[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, unit.Angular_MOA)
	validateOne(t, data[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, unit.Angular_MOA)
}

func TestPathG7(t *testing.T) {
	bc, _ := go_ballisticcalc.CreateBallisticCoefficient(0.223, go_ballisticcalc.DragTable_G7)
	projectile := go_ballisticcalc.CreateProjectileWithDimensions(bc, unit.MustCreateDistance(0.308, unit.Distance_Inch),
		unit.MustCreateDistance(1.282, unit.Distance_Inch), unit.MustCreateWeight(168, unit.Weight_Grain))
	ammo := go_ballisticcalc.CreateAmmunition(projectile, unit.MustCreateVelocity(2750, unit.Velocity_FPS))
	zero := go_ballisticcalc.CreateZeroInfo(unit.MustCreateDistance(100, unit.Distance_Yard))
	twist := go_ballisticcalc.CreateTwist(go_ballisticcalc.Twist_Right, unit.MustCreateDistance(11.24, unit.Distance_Inch))
	weapon := go_ballisticcalc.CreateWeaponWithTwist(unit.MustCreateDistance(2, unit.Distance_Inch), zero, twist)
	atmosphere := go_ballisticcalc.CreateDefaultAtmosphere()
	shotInfo := go_ballisticcalc.CreateShotParameters(unit.MustCreateAngular(4.221, unit.Angular_MOA),
		unit.MustCreateDistance(1000, unit.Distance_Yard),
		unit.MustCreateDistance(100, unit.Distance_Yard))
	wind := go_ballisticcalc.CreateOnlyWindInfo(unit.MustCreateVelocity(5, unit.Velocity_MPH),
		unit.MustCreateAngular(-45, unit.Angular_Degree))

	calc := go_ballisticcalc.CreateTrajectoryCalculator()
	data := calc.Trajectory(ammo, weapon, atmosphere, shotInfo, wind)

	assertEqual(t, float64(len(data)), 11, 0.1, "Length")

	validateOne(t, data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.Angular_Mil)
	validateOne(t, data[1], 100, 2544.3, 2.279, 2416, 0, 0, -0.35, -0.09, 0.113, 698, unit.Angular_Mil)
	validateOne(t, data[5], 500, 1810.7, 1.622, 1226, -56.3, -3.18, -9.96, -0.55, 0.673, 252, unit.Angular_Mil)
	validateOne(t, data[10], 1000, 1081.3, 0.968, 442, -401.6, -11.32, -50.98, -1.44, 1.748, 55, unit.Angular_Mil)
}
