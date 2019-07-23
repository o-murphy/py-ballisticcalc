package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//Description of the projectile
type Projectile struct {
	ballisticCoefficient BallisticCoefficient
	weight               unit.Weight
	hasDimensions        bool
	bulletDiameter       unit.Distance
	bulletLength         unit.Distance
}

//Creates a projectile with dimensions (diameter and length)
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

//Create projectile without dimensions.
//
//If no dimensions set, the trajectory calculator won't be able to calculate spin drift.
func CreateProjectile(ballisticCoefficient BallisticCoefficient,
	weight unit.Weight) Projectile {

	return Projectile{ballisticCoefficient: ballisticCoefficient,
		hasDimensions: false,
		weight:        weight}
}

func (v Projectile) BallisticCoefficient() BallisticCoefficient {
	return v.ballisticCoefficient
}

func (v Projectile) BulletWeight() unit.Weight {
	return v.weight
}

func (v Projectile) BulletDiameter() unit.Distance {
	return v.bulletDiameter
}

func (v Projectile) BulletLength() unit.Distance {
	return v.bulletLength
}

func (v Projectile) HasDimensions() bool {
	return v.hasDimensions
}

//Descrition of ammunition
type Ammunition struct {
	projectile     Projectile
	muzzleVelocity unit.Velocity
}

func CreateAmmunition(bullet Projectile, muzzleVelocity unit.Velocity) Ammunition {
	return Ammunition{
		projectile:     bullet,
		muzzleVelocity: muzzleVelocity,
	}
}

func (v Ammunition) Bullet() Projectile {
	return v.projectile
}

func (v Ammunition) MuzzleVelocity() unit.Velocity {
	return v.muzzleVelocity
}
