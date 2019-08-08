package unit_test

import (
	"math"
	"testing"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

func angularBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Angular
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateAngular(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return
	}
}

func distanceBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Distance
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateDistance(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}
}

func energyBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Energy
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateEnergy(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}

}

func pressureBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Pressure
	var e1, e2 error
	var v float64
	u, e1 = unit.CreatePressure(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}
}

func temperatureBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Temperature
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateTemperature(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}

}

func velocityBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Velocity
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateVelocity(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}

}

func weightBackAndForth(t *testing.T, value float64, units byte) {
	var u unit.Weight
	var e1, e2 error
	var v float64
	u, e1 = unit.CreateWeight(value, units)
	if e1 != nil {
		t.Errorf("Creation failed for %d", units)
		return
	}
	v, e2 = u.Value(units)
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.In(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}

}

func TestAngular(t *testing.T) {
	angularBackAndForth(t, 3, unit.AngularDegree)
	angularBackAndForth(t, 3, unit.AngularMOA)
	angularBackAndForth(t, 3, unit.AngularMRad)
	angularBackAndForth(t, 3, unit.AngularMil)
	angularBackAndForth(t, 3, unit.AngularRadian)
	angularBackAndForth(t, 3, unit.AngularThousand)
	angularBackAndForth(t, 3, unit.AngularCmPer100M)
	angularBackAndForth(t, 3, unit.AngularInchesPer100Yd)

	var u unit.Angular
	u, _ = unit.CreateAngular(1, unit.AngularInchesPer100Yd)
	if math.Abs(0.954930-u.In(unit.AngularMOA)) > 1e-5 {
		t.Errorf("Conversion failed")
	}

	u, _ = unit.CreateAngular(1, unit.AngularInchesPer100Yd)
	u = u.Convert(unit.AngularCmPer100M)
	if u.String() != "2.78cm/100m" {
		t.Errorf("To string failed: %s", u.String())
	}
}

func TestDistance(t *testing.T) {
	distanceBackAndForth(t, 3, unit.DistanceCentimeter)
	distanceBackAndForth(t, 3, unit.DistanceFoot)
	distanceBackAndForth(t, 3, unit.DistanceInch)
	distanceBackAndForth(t, 3, unit.DistanceKilometer)
	distanceBackAndForth(t, 3, unit.DistanceLine)
	distanceBackAndForth(t, 3, unit.DistanceMeter)
	distanceBackAndForth(t, 3, unit.DistanceMile)
	distanceBackAndForth(t, 3, unit.DistanceMillimeter)
	distanceBackAndForth(t, 3, unit.DistanceNauticalMile)
	distanceBackAndForth(t, 3, unit.DistanceYard)
}

func TestEnergy(t *testing.T) {
	energyBackAndForth(t, 3, unit.EnergyFootPound)
	energyBackAndForth(t, 3, unit.EnergyJoule)
}

func TestPressure(t *testing.T) {
	pressureBackAndForth(t, 3, unit.PressureBar)
	pressureBackAndForth(t, 3, unit.PressureHP)
	pressureBackAndForth(t, 3, unit.PressureMmHg)
	pressureBackAndForth(t, 3, unit.PressureInHg)
}

func TestTemperature(t *testing.T) {
	temperatureBackAndForth(t, 3, unit.TemperatureCelsius)
	temperatureBackAndForth(t, 3, unit.TemperatureFahrenheit)
	temperatureBackAndForth(t, 3, unit.TemperatureKelvin)
	temperatureBackAndForth(t, 3, unit.TemperatureRankin)
}

func TestVelocity(t *testing.T) {
	velocityBackAndForth(t, 3, unit.VelocityFPS)
	velocityBackAndForth(t, 3, unit.VelocityKMH)
	velocityBackAndForth(t, 3, unit.VelocityKT)
	velocityBackAndForth(t, 3, unit.VelocityMPH)
	velocityBackAndForth(t, 3, unit.VelocityMPS)
}

func TestWeight(t *testing.T) {
	weightBackAndForth(t, 3, unit.WeightGrain)
	weightBackAndForth(t, 3, unit.WeightGram)
	weightBackAndForth(t, 3, unit.WeightKilogram)
	weightBackAndForth(t, 3, unit.WeightNewton)
	weightBackAndForth(t, 3, unit.WeightOunce)
	weightBackAndForth(t, 3, unit.WeightPound)
}
