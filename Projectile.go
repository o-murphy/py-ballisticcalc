package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//Projectile keeps description of a projectile
type Projectile struct {
	ballisticCoefficient BallisticCoefficient
	weight               unit.Weight
	hasDimensions        bool
	bulletDiameter       unit.Distance
	bulletLength         unit.Distance
}

//CreateProjectileWithDimensions creates the description of a projectile with dimensions (diameter and length)
//
//Dimensions are only required if you want to take into account projectile spin drift.
//TwistInfo must be also set in this case.
func CreateProjectileWithDimensions(ballisticCoefficient BallisticCoefficient,
	bulletDiameter unit.Distance,
	bulletLength unit.Distance,
	weight unit.Weight) Projectile {

	return Projectile{ballisticCoefficient: ballisticCoefficient,
		hasDimensions:  true,
		bulletDiameter: bulletDiameter,
		bulletLength:   bulletLength,
		weight:         weight}
}

//CreateProjectile create projectile description without dimensions.
//
//If no dimensions set, the trajectory calculator won't be able to calculate spin drift.
func CreateProjectile(ballisticCoefficient BallisticCoefficient,
	weight unit.Weight) Projectile {

	return Projectile{ballisticCoefficient: ballisticCoefficient,
		hasDimensions: false,
		weight:        weight}
}

//BallisticCoefficient returns ballistic coefficient of the projectile
func (v Projectile) BallisticCoefficient() BallisticCoefficient {
	return v.ballisticCoefficient
}

//BulletWeight returns weight of the projectile
func (v Projectile) BulletWeight() unit.Weight {
	return v.weight
}

//BulletDiameter returns the diameter (caliber) of the projectile
func (v Projectile) BulletDiameter() unit.Distance {
	return v.bulletDiameter
}

//BulletLength return the length of the bullet
func (v Projectile) BulletLength() unit.Distance {
	return v.bulletLength
}

//HasDimensions returns the flag indicating whether the projectile
//has dimensions set
func (v Projectile) HasDimensions() bool {
	return v.hasDimensions
}

//Ammunition struct keeps the des of ammunition (e.g. projectile loaded into a case shell)
type Ammunition struct {
	projectile     Projectile
	muzzleVelocity unit.Velocity
}

//CreateAmmunition creates the description of the ammunition
func CreateAmmunition(bullet Projectile, muzzleVelocity unit.Velocity) Ammunition {
	return Ammunition{
		projectile:     bullet,
		muzzleVelocity: muzzleVelocity,
	}
}

//Bullet returns the description of the projectile
func (v Ammunition) Bullet() Projectile {
	return v.projectile
}

//MuzzleVelocity returns the velocity of the projectile at the muzzle
func (v Ammunition) MuzzleVelocity() unit.Velocity {
	return v.muzzleVelocity
}
