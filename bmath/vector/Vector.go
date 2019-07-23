package vector

import (
	"fmt"
	"math"
)

type Vector struct {
	X float64
	Y float64
	Z float64
}

func (v Vector) String() string {
	return fmt.Sprintf("[X=%f,Y=%f,Z=%f]", v.X, v.Y, v.Z)
}

func Create(x, y, z float64) Vector {
	return Vector{X: x, Y: y, Z: z}
}

func (v Vector) Copy() Vector {
	return Vector{X: v.X, Y: v.Y, Z: v.Z}
}

func (v Vector) MultiplyByVector(b Vector) float64 {
	return v.X*b.X + v.Y*v.Y + v.Z*b.Z
}

func (v Vector) Magnitude() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y + v.Z*v.Z)
}

func (v Vector) MultiplyByConst(a float64) Vector {
	return Create(a*v.X, a*v.Y, a*v.Z)
}

func (a Vector) Add(b Vector) Vector {
	return Create(a.X+b.X, a.Y+b.Y, a.Z+b.Z)
}

func (a Vector) Subtract(b Vector) Vector {
	return Create(a.X-b.X, a.Y-b.Y, a.Z-b.Z)
}

func (v Vector) Negate() Vector {
	return Create(-v.X, -v.Y, -v.Z)
}

func (v Vector) Normalize() Vector {
	var magnitude float64

	magnitude = v.Magnitude()

	if math.Abs(magnitude) < 1e-10 {
		return v.Copy()
	} else {
		return v.MultiplyByConst(1.0 / magnitude)
	}
}
