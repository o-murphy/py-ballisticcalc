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
		t.Errorf("Conversion 1 failed")
	}
}
