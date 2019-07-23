package vector_test

import (
	"math"
	"testing"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/vector"
)

func TestVectorCreation(t *testing.T) {
	var v, c vector.Vector

	v = vector.Create(1, 2, 3)
	if v.X != 1 || v.Y != 2 || v.Z != 3 {
		t.Error("Creation failed")
	}

	c = v.Copy()

	if c.X != 1 || c.Y != 2 || c.Z != 3 {
		t.Error("Copy failed")
	}
}

func TestUnary(t *testing.T) {
	var v1, v2 vector.Vector

	v1 = vector.Create(1, 2, 3)
	if math.Abs(v1.Magnitude()-3.74165738677) > 1e-7 {
		t.Error("Magnitude failed")
	}

	v2 = v1.Negate()
	if v2.X != -1 || v2.Y != -2 || v2.Z != -3 {
		t.Error("Negate failed")
	}

	v2 = v1.Normalize()
	if v2.X > 1 || v2.Y > 1 || v2.Z > 1 {
		t.Error("Normalize failed")
	}

	v1 = vector.Create(0, 0, 0)
	v2 = v1.Normalize()
	if v2.X != 0 || v2.Y != 0 || v2.Z != 0 {
		t.Error("Normalize failed")
	}
}

func TestBinary(t *testing.T) {
	var v1, v2 vector.Vector
	v1 = vector.Create(1, 2, 3)
	v2 = v1.Add(v1.Copy())
	if v2.X != 2 || v2.Y != 4 || v2.Z != 6 {
		t.Error("Add failed")
	}

	v2 = v1.Subtract(v2)
	if v2.X != -1 || v2.Y != -2 || v2.Z != -3 {
		t.Error("Subtract failed")
	}

	if v1.MultiplyByVector(v1.Copy()) != (1 + 4 + 9) {
		t.Error("MultiplyByVector failed")
	}

	v2 = v1.MultiplyByConst(3)
	if v2.X != 3 || v2.Y != 6 || v2.Z != 9 {
		t.Error("MultiplyByConst failed")
	}
}
