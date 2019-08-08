//Package vector provides simple operations on 3d vector
//required for 3DF trajectory calculation
package vector

import (
	"fmt"
	"math"
)

//Vector struct keeps data about a 3D vector
type Vector struct {
	X float64 //X-coordinate
	Y float64 //Y-coordinate
	Z float64 //Z-coordinate
}

//Converts a vector into a string
func (v Vector) String() string {
	return fmt.Sprintf("[X=%f,Y=%f,Z=%f]", v.X, v.Y, v.Z)
}

//Create create a vector from its coordinates
func Create(x, y, z float64) Vector {
	return Vector{X: x, Y: y, Z: z}
}

//Copy creates a copy of the vector
func (v Vector) Copy() Vector {
	return Vector{X: v.X, Y: v.Y, Z: v.Z}
}

//MultiplyByVector returns a product of two vectors
//
//The product of two vectors is a sum of products of each coordinate
func (v Vector) MultiplyByVector(b Vector) float64 {
	return v.X*b.X + v.Y*v.Y + v.Z*b.Z
}

//Magnitude retruns a magnitude of the vector
//
//The magnitude of the vector is the length of a line that starts in point (0,0,0)
//and ends in the point set by the vector coordinates
func (v Vector) Magnitude() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y + v.Z*v.Z)
}

//MultiplyByConst multiplies the vector by the constant
func (v Vector) MultiplyByConst(a float64) Vector {
	return Create(a*v.X, a*v.Y, a*v.Z)
}

//Add adds two vectors
func (v Vector) Add(b Vector) Vector {
	return Create(v.X+b.X, v.Y+b.Y, v.Z+b.Z)
}

//Subtract subtracts one vector from another
func (v Vector) Subtract(b Vector) Vector {
	return Create(v.X-b.X, v.Y-b.Y, v.Z-b.Z)
}

//Negate returns a vector which is simmetrical to this vector vs (0,0,0) point
func (v Vector) Negate() Vector {
	return Create(-v.X, -v.Y, -v.Z)
}

//Normalize returns a vector of magnitude one which is collinear to this vector
func (v Vector) Normalize() Vector {
	var magnitude float64

	magnitude = v.Magnitude()

	if math.Abs(magnitude) < 1e-10 {
		return v.Copy()
	}
	return v.MultiplyByConst(1.0 / magnitude)

}
