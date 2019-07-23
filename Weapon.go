package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//The information about zeroing of the weapon
type ZeroInfo struct {
	hasAmmunition  bool
	ammunition     Ammunition
	zeroDistance   unit.Distance
	hasAtmosphere  bool
	zeroAtmosphere Atmosphere
}

//Return flag indicating whether other ammo is used to zero
func (v ZeroInfo) HasAmmunition() bool {
	return v.hasAmmunition
}

//Return ammo used to zero
func (v ZeroInfo) Ammunition() Ammunition {
	return v.ammunition
}

//Returns flag indicating whether weapon is zeroed under different conditions
func (v ZeroInfo) HasAtmosphere() bool {
	return v.hasAtmosphere
}

//Returns conditions at the time of zeroing
func (v ZeroInfo) Atmosphere() Atmosphere {
	return v.zeroAtmosphere
}

//Returns the distance at which the weapon was zeroed
func (v ZeroInfo) ZeroDistance() unit.Distance {
	return v.zeroDistance
}

//Creates zero information using distance only
func CreateZeroInfo(distance unit.Distance) ZeroInfo {
	return ZeroInfo{
		hasAmmunition: false,
		hasAtmosphere: false,
		zeroDistance:  distance,
	}
}

//Creates zero information using distance and conditions
func CreateZeroInfoWithAtmosphere(distance unit.Distance, atmosphere Atmosphere) ZeroInfo {
	return ZeroInfo{
		hasAmmunition:  false,
		hasAtmosphere:  true,
		zeroAtmosphere: atmosphere,
		zeroDistance:   distance,
	}

}

//Creates zero information using distance and other ammunition
func CreateZeroInfoWithAnotherAmmo(distance unit.Distance, ammo Ammunition) ZeroInfo {
	return ZeroInfo{
		hasAmmunition: true,
		ammunition:    ammo,
		hasAtmosphere: false,
		zeroDistance:  distance,
	}
}

//Creates zero information using distance, other conditions and other ammunition
func CreateZeroInfoWithAnotherAmmoAndAtmosphere(distance unit.Distance, ammo Ammunition, atmosphere Atmosphere) ZeroInfo {
	return ZeroInfo{
		hasAmmunition:  true,
		ammunition:     ammo,
		hasAtmosphere:  true,
		zeroAtmosphere: atmosphere,
		zeroDistance:   distance,
	}
}

const Twist_Right byte = 1
const Twist_Left byte = 2

//The rifling twist information
//
//The rifling twist is used to calculate spin drift only
type TwistInfo struct {
	twistDirection byte
	riflingTwist   unit.Distance
}

//Creates twist
//
//Direction must be either Twist_Right or Twist_Left constant
func CreateTwist(direction byte, twist unit.Distance) TwistInfo {
	return TwistInfo{
		twistDirection: direction,
		riflingTwist:   twist,
	}
}

func (v TwistInfo) Direction() byte {
	return v.twistDirection
}

func (v TwistInfo) Twist() unit.Distance {
	return v.riflingTwist
}

//The weapon direction
type Weapon struct {
	sightHeight  unit.Distance
	zeroInfo     ZeroInfo
	hasTwistInfo bool
	twist        TwistInfo
	clickValue   unit.Angular
}

func (v Weapon) SightHeight() unit.Distance {
	return v.sightHeight
}

func (v Weapon) Zero() ZeroInfo {
	return v.zeroInfo
}

func (v Weapon) HasTwist() bool {
	return v.hasTwistInfo
}

func (v Weapon) Twist() TwistInfo {
	return v.twist
}

func (v Weapon) ClickValue() unit.Angular {
	return v.clickValue
}

func (v *Weapon) SetClickValue(click unit.Angular) {
	v.clickValue = click
}

//Create weapon with no twist info
//
//If no twist info is set, spin drift won't be calculated
func CreateWeapon(sightHeight unit.Distance, zeroInfo ZeroInfo) Weapon {
	return Weapon{sightHeight: sightHeight, zeroInfo: zeroInfo, hasTwistInfo: false}
}

//Create weapon with twist info
//
//If twist info AND bullet dimensions are set, spin drift will be calculated
func CreateWeaponWithTwist(sightHeight unit.Distance, zeroInfo ZeroInfo, twist TwistInfo) Weapon {
	return Weapon{sightHeight: sightHeight, zeroInfo: zeroInfo, hasTwistInfo: true, twist: twist}
}
