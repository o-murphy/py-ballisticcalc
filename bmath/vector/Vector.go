//The package provides simple operations on 3d vector
//required for 3DF trajectory calculation
package vector

import (
	"fmt"
	"math"
)

//3D vector structure
type Vector struct {
	X float64 //X-coordinate
	Y float64 //Y-coordinate
	Z float64 //Z-coordinate
}

//Converts a vector into a string
func (v Vector) String() string {
	return fmt.Sprintf("[X=%f,Y=%f,Z=%f]", v.X, v.Y, v.Z)
}

//Creates a vector from its coordinates
func Create(x, y, z float64) Vector {
	return Vector{X: x, Y: y, Z: z}
}

//Create a copy of the vector
func (v Vector) Copy() Vector {
	return Vector{X: v.X, Y: v.Y, Z: v.Z}
}

//Return a product of two vectors
//
//The product of two vectors is a sum of products of each coordinate
func (v Vector) MultiplyByVector(b Vector) float64 {
	return v.X*b.X + v.Y*v.Y + v.Z*b.Z
}

//Retruns a magnitude of the vector
//
//The magnitude of the vector is the length of a line that starts in point (0,0,0)
//and ends in the point set by the vector coordinates
func (v Vector) Magnitude() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y + v.Z*v.Z)
}

//Multiplies the vector by the constant
func (v Vector) MultiplyByConst(a float64) Vector {
	return Create(a*v.X, a*v.Y, a*v.Z)
}

//Adds two vectors
func (a Vector) Add(b Vector) Vector {
	return Create(a.X+b.X, a.Y+b.Y, a.Z+b.Z)
}

//Subtracts one vector from another
func (a Vector) Subtract(b Vector) Vector {
	return Create(a.X-b.X, a.Y-b.Y, a.Z-b.Z)
}

//Returns a vector which is simmetrical to this vector vs (0,0,0) point
func (v Vector) Negate() Vector {
	return Create(-v.X, -v.Y, -v.Z)
}

//Returns a vector of magnitude one which is collinear to this vector
func (v Vector) Normalize() Vector {
	var magnitude float64

	magnitude = v.Magnitude()

	if math.Abs(magnitude) < 1e-10 {
		return v.Copy()
	} else {
		return v.MultiplyByConst(1.0 / magnitude)
	}
}
