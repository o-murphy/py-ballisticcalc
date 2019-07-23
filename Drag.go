package go_ballisticcalc

import (
	"fmt"
)

const DragTable_G1 byte = 1
const DragTable_G2 byte = 2
const DragTable_G5 byte = 3
const DragTable_G6 byte = 4
const DragTable_G7 byte = 5
const DragTable_G8 byte = 6
const DragTable_GL byte = 7
const DragTable_GI byte = 8

type dragFunction func(float64) float64

//The ballistic coefficient (BC) of a body is a measure of its
//ability to overcome air resistance in flight.
//
//The small arm ballistics, BC is expressed vs
//a standard projectile. Different ballistic tables
//uses different standard projectiles, for example G1 uses
//flat based 2 caliber length with a 2 caliber ogive
//
//G1 and G7 are the most used for small arms ballistics
type BallisticCoefficient struct {
	value float64
	table byte
	drag  dragFunction
}

func dragFunctionFactory(dragTable byte) dragFunction {
	switch dragTable {
	case DragTable_G1:
		return func(mach float64) float64 {
			switch {
			case mach > 2.0:
				return 0.9482590 + mach*(-0.248367+mach*0.0344343)
			case mach > 1.40:
				return 0.6796810 + mach*(0.0705311-mach*0.0570628)
			case mach > 1.10:
				return -1.471970 + mach*(3.1652900-mach*1.1728200)
			case mach > 0.85:
				return -0.647392 + mach*(0.9421060+mach*0.1806040)
			case mach >= 0.55:
				return 0.6224890 + mach*(-1.426820+mach*1.2094500)
			default:
				return 0.2637320 + mach*(-0.165665+mach*0.0852214)
			}
		}
	case DragTable_G2:
		return func(mach float64) float64 {
			switch {
			case mach > 2.5:
				return 0.4465610 + mach*(-0.0958548+mach*0.00799645)
			case mach > 1.2:
				return 0.7016110 + mach*(-0.3075100+mach*0.05192560)
			case mach > 1.0:
				return -1.105010 + mach*(2.77195000-mach*1.26667000)
			case mach > 0.9:
				return -2.240370 + mach*2.63867000
			case mach >= 0.7:
				return 0.9099690 + mach*(-1.9017100+mach*1.21524000)
			default:
				return 0.2302760 + mach*(0.000210564-mach*0.1275050)

			}
		}
	case DragTable_G5:
		return func(mach float64) float64 {
			switch {
			case mach > 2.0:
				return 0.671388 + mach*(-0.185208+mach*0.0204508)
			case mach > 1.1:
				return 0.134374 + mach*(0.4378330-mach*0.1570190)
			case mach > 0.9:
				return -0.924258 + mach*1.24904
			case mach >= 0.6:
				return 0.654405 + mach*(-1.4275000+mach*0.998463)
			default:
				return 0.186386 + mach*(-0.0342136-mach*0.035691)
			}
		}
	case DragTable_G6:
		return func(mach float64) float64 {
			switch {
			case mach > 2.0:
				return 0.746228 + mach*(-0.255926+mach*0.0291726)
			case mach > 1.1:
				return 0.513638 + mach*(-0.015269-mach*0.0331221)
			case mach > 0.9:
				return -0.908802 + mach*1.25814
			case mach >= 0.6:
				return 0.366723 + mach*(-0.458435+mach*0.337906)
			default:
				return 0.264481 + mach*(-0.157237+mach*0.117441)
			}
		}
	case DragTable_G7:
		return func(mach float64) float64 {
			switch {
			case mach > 1.9:
				return 0.439493 + mach*(-0.0793543+mach*0.00448477)
			case mach > 1.05:
				return 0.642743 + mach*(-0.2725450+mach*0.049247500)
			case mach > 0.90:
				return -1.69655 + mach*2.03557
			case mach >= 0.60:
				return 0.353384 + mach*(-0.69240600+mach*0.50946900)
			default:
				return 0.119775 + mach*(-0.00231118+mach*0.00286712)
			}
		}
	case DragTable_G8:
		return func(mach float64) float64 {
			switch {
			case mach > 1.1:
				return 0.639096 + mach*(-0.197471+mach*0.0216221)
			case mach >= 0.925:
				return -12.9053 + mach*(24.9181-mach*11.6191)
			default:
				return 0.210589 + mach*(-0.00184895+mach*0.00211107)
			}
		}
	case DragTable_GI:
		return func(mach float64) float64 {
			switch {
			case mach > 1.65:
				return 0.845362 + mach*(-0.143989+mach*0.0113272)
			case mach > 1.2:
				return 0.630556 + mach*0.00701308
			case mach >= 0.7:
				return 0.531976 + mach*(-1.28079+mach*1.17628)
			default:
				return 0.2282
			}
		}
	case DragTable_GL:
		return func(mach float64) float64 {
			switch {
			case mach > 1.0:
				return 0.286629 + mach*(0.3588930-mach*0.0610598)
			case mach >= 0.8:
				return 1.59969 + mach*(-3.9465500+mach*2.831370)
			default:
				return 0.333118 + mach*(-0.498448+mach*0.474774)
			}
		}
	default:
		panic(fmt.Errorf("Unknown drag table type"))
	}
}

func CreateBallisticCoefficient(value float64, dragTable byte) (BallisticCoefficient, error) {
	if dragTable < DragTable_G1 || DragTable_G1 > DragTable_GI {
		return BallisticCoefficient{}, fmt.Errorf("BallisticCoefficient: Unknown drag table %d", dragTable)
	}
	if value <= 0 {
		return BallisticCoefficient{}, fmt.Errorf("BallisticCoefficient: Drag coefficient must be greater than zero")
	}
	return BallisticCoefficient{
		value: value,
		table: dragTable,
		drag:  dragFunctionFactory(dragTable),
	}, nil
}

func (v BallisticCoefficient) Value() float64 {
	return v.value
}

func (v BallisticCoefficient) Table() byte {
	return v.table
}

func (v BallisticCoefficient) Drag(mach float64) float64 {
	return v.drag(mach) * 2.08551e-04 / v.value
}
