package go_ballisticcalc

import "github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"

//ZeroInfo structure keeps the information about zeroing of the weapon
type ZeroInfo struct {
	hasAmmunition  bool
	ammunition     Ammunition
	zeroDistance   unit.Distance
	hasAtmosphere  bool
	zeroAtmosphere Atmosphere
}

//HasAmmunition return flag indicating whether other ammo is used to zero
func (v ZeroInfo) HasAmmunition() bool {
	return v.hasAmmunition
}

//Ammunition return ammo used to zero
func (v ZeroInfo) Ammunition() Ammunition {
	return v.ammunition
}

//HasAtmosphere returns flag indicating whether weapon is zeroed under different conditions
func (v ZeroInfo) HasAtmosphere() bool {
	return v.hasAtmosphere
}

//Atmosphere returns conditions at the time of zeroing
func (v ZeroInfo) Atmosphere() Atmosphere {
	return v.zeroAtmosphere
}

//ZeroDistance returns the distance at which the weapon was zeroed
func (v ZeroInfo) ZeroDistance() unit.Distance {
	return v.zeroDistance
}

//CreateZeroInfo creates zero information using distance only
func CreateZeroInfo(distance unit.Distance) ZeroInfo {
	return ZeroInfo{
		hasAmmunition: false,
		hasAtmosphere: false,
		zeroDistance:  distance,
	}
}

//CreateZeroInfoWithAtmosphere creates zero information using distance and conditions
func CreateZeroInfoWithAtmosphere(distance unit.Distance, atmosphere Atmosphere) ZeroInfo {
	return ZeroInfo{
		hasAmmunition:  false,
		hasAtmosphere:  true,
		zeroAtmosphere: atmosphere,
		zeroDistance:   distance,
	}

}

//CreateZeroInfoWithAnotherAmmo creates zero information using distance and other ammunition
func CreateZeroInfoWithAnotherAmmo(distance unit.Distance, ammo Ammunition) ZeroInfo {
	return ZeroInfo{
		hasAmmunition: true,
		ammunition:    ammo,
		hasAtmosphere: false,
		zeroDistance:  distance,
	}
}

//CreateZeroInfoWithAnotherAmmoAndAtmosphere creates zero information using distance, other conditions and other ammunition
func CreateZeroInfoWithAnotherAmmoAndAtmosphere(distance unit.Distance, ammo Ammunition, atmosphere Atmosphere) ZeroInfo {
	return ZeroInfo{
		hasAmmunition:  true,
		ammunition:     ammo,
		hasAtmosphere:  true,
		zeroAtmosphere: atmosphere,
		zeroDistance:   distance,
	}
}

//TwistRight is the flag indiciating that the barrel is right-hand twisted
const TwistRight byte = 1

//TwistLeft is the flag indiciating that the barrel is left-hand twisted
const TwistLeft byte = 2

//TwistInfo contains the rifling twist information
//
//The rifling twist is used to calculate spin drift only
type TwistInfo struct {
	twistDirection byte
	riflingTwist   unit.Distance
}

//CreateTwist creates twist information
//
//Direction must be either Twist_Right or Twist_Left constant
func CreateTwist(direction byte, twist unit.Distance) TwistInfo {
	return TwistInfo{
		twistDirection: direction,
		riflingTwist:   twist,
	}
}

//Direction returns the twist direction (see TwistRight and TwistLeft)
func (v TwistInfo) Direction() byte {
	return v.twistDirection
}

//Twist returns the twist step (the distance inside the barrel at which the projectile makes one turn)
func (v TwistInfo) Twist() unit.Distance {
	return v.riflingTwist
}

//Weapon struct contains the weapon description
type Weapon struct {
	sightHeight  unit.Distance
	zeroInfo     ZeroInfo
	hasTwistInfo bool
	twist        TwistInfo
	clickValue   unit.Angular
}

//SightHeight returns the height of the sight centerline over the barrel centerline
func (v Weapon) SightHeight() unit.Distance {
	return v.sightHeight
}

//Zero returns the zeroing information
func (v Weapon) Zero() ZeroInfo {
	return v.zeroInfo
}

//HasTwist returns the flag indicating whether the rifling twist information is set
func (v Weapon) HasTwist() bool {
	return v.hasTwistInfo
}

//Twist returns the rifling twist information
func (v Weapon) Twist() TwistInfo {
	return v.twist
}

//ClickValue returns the value of one click of the scope
func (v Weapon) ClickValue() unit.Angular {
	return v.clickValue
}

//SetClickValue sets the value of one click of the scope
func (v *Weapon) SetClickValue(click unit.Angular) {
	v.clickValue = click
}

//CreateWeapon creates the weapon definition with no twist info
//
//If no twist info is set, spin drift won't be calculated
func CreateWeapon(sightHeight unit.Distance, zeroInfo ZeroInfo) Weapon {
	return Weapon{sightHeight: sightHeight, zeroInfo: zeroInfo, hasTwistInfo: false}
}

//CreateWeaponWithTwist creates weapon description with twist info
//
//If twist info AND bullet dimensions are set, spin drift will be calculated
func CreateWeaponWithTwist(sightHeight unit.Distance, zeroInfo ZeroInfo, twist TwistInfo) Weapon {
	return Weapon{sightHeight: sightHeight, zeroInfo: zeroInfo, hasTwistInfo: true, twist: twist}
}
