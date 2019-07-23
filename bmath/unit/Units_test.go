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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
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
	if !(e2 == nil && math.Abs(v-value) < 1e-7 && math.Abs(v-u.ValueOrZero(units)) < 1e-7) {
		t.Errorf("Read back failed for %d", units)
		return

	}

}

func TestAngular(t *testing.T) {
	angularBackAndForth(t, 3, unit.Angular_Degree)
	angularBackAndForth(t, 3, unit.Angular_MOA)
	angularBackAndForth(t, 3, unit.Angular_MRad)
	angularBackAndForth(t, 3, unit.Angular_Mil)
	angularBackAndForth(t, 3, unit.Angular_Radian)
	angularBackAndForth(t, 3, unit.Angular_Thousand)
	angularBackAndForth(t, 3, unit.Angular_cmPer100M)
	angularBackAndForth(t, 3, unit.Angular_inchesPer100Yd)

	var u unit.Angular
	u, _ = unit.CreateAngular(1, unit.Angular_inchesPer100Yd)
	if math.Abs(0.954930-u.ValueOrZero(unit.Angular_MOA)) > 1e-5 {
		t.Errorf("Conversion failed")
	}

	u, _ = unit.CreateAngular(1, unit.Angular_inchesPer100Yd)
	u = u.Convert(unit.Angular_cmPer100M)
	if u.String() != "2.78cm/100m" {
		t.Errorf("To string failed: %s", u.String())
	}
}

func TestDistance(t *testing.T) {
	distanceBackAndForth(t, 3, unit.Distance_Centimeter)
	distanceBackAndForth(t, 3, unit.Distance_Foot)
	distanceBackAndForth(t, 3, unit.Distance_Inch)
	distanceBackAndForth(t, 3, unit.Distance_Kilometer)
	distanceBackAndForth(t, 3, unit.Distance_Line)
	distanceBackAndForth(t, 3, unit.Distance_Meter)
	distanceBackAndForth(t, 3, unit.Distance_Mile)
	distanceBackAndForth(t, 3, unit.Distance_Millimeter)
	distanceBackAndForth(t, 3, unit.Distance_NauticalMile)
	distanceBackAndForth(t, 3, unit.Distance_Yard)
}

func TestEnergy(t *testing.T) {
	energyBackAndForth(t, 3, unit.Energy_FootPound)
	energyBackAndForth(t, 3, unit.Energy_Joule)
}

func TestPressure(t *testing.T) {
	pressureBackAndForth(t, 3, unit.Pressure_Bar)
	pressureBackAndForth(t, 3, unit.Pressure_HP)
	pressureBackAndForth(t, 3, unit.Pressure_MmHg)
	pressureBackAndForth(t, 3, unit.Pressure_InHg)
}

func TestTemperature(t *testing.T) {
	temperatureBackAndForth(t, 3, unit.Temperature_Celsius)
	temperatureBackAndForth(t, 3, unit.Temperature_Fahrenheit)
	temperatureBackAndForth(t, 3, unit.Temperature_Kelvin)
	temperatureBackAndForth(t, 3, unit.Temperature_Rankin)
}

func TestVelocity(t *testing.T) {
	velocityBackAndForth(t, 3, unit.Velocity_FPS)
	velocityBackAndForth(t, 3, unit.Velocity_KMH)
	velocityBackAndForth(t, 3, unit.Velocity_KT)
	velocityBackAndForth(t, 3, unit.Velocity_MPH)
	velocityBackAndForth(t, 3, unit.Velocity_MPS)
}

func TestWeight(t *testing.T) {
	weightBackAndForth(t, 3, unit.Weight_Grain)
	weightBackAndForth(t, 3, unit.Weight_Gram)
	weightBackAndForth(t, 3, unit.Weight_Kilogram)
	weightBackAndForth(t, 3, unit.Weight_Newton)
	weightBackAndForth(t, 3, unit.Weight_Ounce)
	weightBackAndForth(t, 3, unit.Weight_Pound)
}
