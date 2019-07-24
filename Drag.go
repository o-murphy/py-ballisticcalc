package go_ballisticcalc

import (
	"fmt"
	"math"
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
			return calculateByCurve(g1_table, g1_curve, mach)
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
			return calculateByCurve(g7_table, g7_curve, mach)
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

type DataPoint struct {
	A, B float64
}

type CurvePoint struct {
	A, B, C float64
}

var g1_table []DataPoint = []DataPoint{
	DataPoint{A: 0.00, B: 0.2629},
	DataPoint{A: 0.05, B: 0.2558},
	DataPoint{A: 0.10, B: 0.2487},
	DataPoint{A: 0.15, B: 0.2413},
	DataPoint{A: 0.20, B: 0.2344},
	DataPoint{A: 0.25, B: 0.2278},
	DataPoint{A: 0.30, B: 0.2214},
	DataPoint{A: 0.35, B: 0.2155},
	DataPoint{A: 0.40, B: 0.2104},
	DataPoint{A: 0.45, B: 0.2061},
	DataPoint{A: 0.50, B: 0.2032},
	DataPoint{A: 0.55, B: 0.2020},
	DataPoint{A: 0.60, B: 0.2034},
	DataPoint{A: 0.70, B: 0.2165},
	DataPoint{A: 0.725, B: 0.2230},
	DataPoint{A: 0.75, B: 0.2313},
	DataPoint{A: 0.775, B: 0.2417},
	DataPoint{A: 0.80, B: 0.2546},
	DataPoint{A: 0.825, B: 0.2706},
	DataPoint{A: 0.85, B: 0.2901},
	DataPoint{A: 0.875, B: 0.3136},
	DataPoint{A: 0.90, B: 0.3415},
	DataPoint{A: 0.925, B: 0.3734},
	DataPoint{A: 0.95, B: 0.4084},
	DataPoint{A: 0.975, B: 0.4448},
	DataPoint{A: 1.0, B: 0.4805},
	DataPoint{A: 1.025, B: 0.5136},
	DataPoint{A: 1.05, B: 0.5427},
	DataPoint{A: 1.075, B: 0.5677},
	DataPoint{A: 1.10, B: 0.5883},
	DataPoint{A: 1.125, B: 0.6053},
	DataPoint{A: 1.15, B: 0.6191},
	DataPoint{A: 1.20, B: 0.6393},
	DataPoint{A: 1.25, B: 0.6518},
	DataPoint{A: 1.30, B: 0.6589},
	DataPoint{A: 1.35, B: 0.6621},
	DataPoint{A: 1.40, B: 0.6625},
	DataPoint{A: 1.45, B: 0.6607},
	DataPoint{A: 1.50, B: 0.6573},
	DataPoint{A: 1.55, B: 0.6528},
	DataPoint{A: 1.60, B: 0.6474},
	DataPoint{A: 1.65, B: 0.6413},
	DataPoint{A: 1.70, B: 0.6347},
	DataPoint{A: 1.75, B: 0.6280},
	DataPoint{A: 1.80, B: 0.6210},
	DataPoint{A: 1.85, B: 0.6141},
	DataPoint{A: 1.90, B: 0.6072},
	DataPoint{A: 1.95, B: 0.6003},
	DataPoint{A: 2.00, B: 0.5934},
	DataPoint{A: 2.05, B: 0.5867},
	DataPoint{A: 2.10, B: 0.5804},
	DataPoint{A: 2.15, B: 0.5743},
	DataPoint{A: 2.20, B: 0.5685},
	DataPoint{A: 2.25, B: 0.5630},
	DataPoint{A: 2.30, B: 0.5577},
	DataPoint{A: 2.35, B: 0.5527},
	DataPoint{A: 2.40, B: 0.5481},
	DataPoint{A: 2.45, B: 0.5438},
	DataPoint{A: 2.50, B: 0.5397},
	DataPoint{A: 2.60, B: 0.5325},
	DataPoint{A: 2.70, B: 0.5264},
	DataPoint{A: 2.80, B: 0.5211},
	DataPoint{A: 2.90, B: 0.5168},
	DataPoint{A: 3.00, B: 0.5133},
	DataPoint{A: 3.10, B: 0.5105},
	DataPoint{A: 3.20, B: 0.5084},
	DataPoint{A: 3.30, B: 0.5067},
	DataPoint{A: 3.40, B: 0.5054},
	DataPoint{A: 3.50, B: 0.5040},
	DataPoint{A: 3.60, B: 0.5030},
	DataPoint{A: 3.70, B: 0.5022},
	DataPoint{A: 3.80, B: 0.5016},
	DataPoint{A: 3.90, B: 0.5010},
	DataPoint{A: 4.00, B: 0.5006},
	DataPoint{A: 4.20, B: 0.4998},
	DataPoint{A: 4.40, B: 0.4995},
	DataPoint{A: 4.60, B: 0.4992},
	DataPoint{A: 4.80, B: 0.4990},
	DataPoint{A: 5.00, B: 0.4988},
}

var g1_curve []CurvePoint = calculateCurve(g1_table)

var g7_table []DataPoint = []DataPoint{
	DataPoint{A: 0.00, B: 0.1198},
	DataPoint{A: 0.05, B: 0.1197},
	DataPoint{A: 0.10, B: 0.1196},
	DataPoint{A: 0.15, B: 0.1194},
	DataPoint{A: 0.20, B: 0.1193},
	DataPoint{A: 0.25, B: 0.1194},
	DataPoint{A: 0.30, B: 0.1194},
	DataPoint{A: 0.35, B: 0.1194},
	DataPoint{A: 0.40, B: 0.1193},
	DataPoint{A: 0.45, B: 0.1193},
	DataPoint{A: 0.50, B: 0.1194},
	DataPoint{A: 0.55, B: 0.1193},
	DataPoint{A: 0.60, B: 0.1194},
	DataPoint{A: 0.65, B: 0.1197},
	DataPoint{A: 0.70, B: 0.1202},
	DataPoint{A: 0.725, B: 0.1207},
	DataPoint{A: 0.75, B: 0.1215},
	DataPoint{A: 0.775, B: 0.1226},
	DataPoint{A: 0.80, B: 0.1242},
	DataPoint{A: 0.825, B: 0.1266},
	DataPoint{A: 0.85, B: 0.1306},
	DataPoint{A: 0.875, B: 0.1368},
	DataPoint{A: 0.90, B: 0.1464},
	DataPoint{A: 0.925, B: 0.1660},
	DataPoint{A: 0.95, B: 0.2054},
	DataPoint{A: 0.975, B: 0.2993},
	DataPoint{A: 1.0, B: 0.3803},
	DataPoint{A: 1.025, B: 0.4015},
	DataPoint{A: 1.05, B: 0.4043},
	DataPoint{A: 1.075, B: 0.4034},
	DataPoint{A: 1.10, B: 0.4014},
	DataPoint{A: 1.125, B: 0.3987},
	DataPoint{A: 1.15, B: 0.3955},
	DataPoint{A: 1.20, B: 0.3884},
	DataPoint{A: 1.25, B: 0.3810},
	DataPoint{A: 1.30, B: 0.3732},
	DataPoint{A: 1.35, B: 0.3657},
	DataPoint{A: 1.40, B: 0.3580},
	DataPoint{A: 1.50, B: 0.3440},
	DataPoint{A: 1.55, B: 0.3376},
	DataPoint{A: 1.60, B: 0.3315},
	DataPoint{A: 1.65, B: 0.3260},
	DataPoint{A: 1.70, B: 0.3209},
	DataPoint{A: 1.75, B: 0.3160},
	DataPoint{A: 1.80, B: 0.3117},
	DataPoint{A: 1.85, B: 0.3078},
	DataPoint{A: 1.90, B: 0.3042},
	DataPoint{A: 1.95, B: 0.3010},
	DataPoint{A: 2.00, B: 0.2980},
	DataPoint{A: 2.05, B: 0.2951},
	DataPoint{A: 2.10, B: 0.2922},
	DataPoint{A: 2.15, B: 0.2892},
	DataPoint{A: 2.20, B: 0.2864},
	DataPoint{A: 2.25, B: 0.2835},
	DataPoint{A: 2.30, B: 0.2807},
	DataPoint{A: 2.35, B: 0.2779},
	DataPoint{A: 2.40, B: 0.2752},
	DataPoint{A: 2.45, B: 0.2725},
	DataPoint{A: 2.50, B: 0.2697},
	DataPoint{A: 2.55, B: 0.2670},
	DataPoint{A: 2.60, B: 0.2643},
	DataPoint{A: 2.65, B: 0.2615},
	DataPoint{A: 2.70, B: 0.2588},
	DataPoint{A: 2.75, B: 0.2561},
	DataPoint{A: 2.80, B: 0.2533},
	DataPoint{A: 2.85, B: 0.2506},
	DataPoint{A: 2.90, B: 0.2479},
	DataPoint{A: 2.95, B: 0.2451},
	DataPoint{A: 3.00, B: 0.2424},
	DataPoint{A: 3.10, B: 0.2368},
	DataPoint{A: 3.20, B: 0.2313},
	DataPoint{A: 3.30, B: 0.2258},
	DataPoint{A: 3.40, B: 0.2205},
	DataPoint{A: 3.50, B: 0.2154},
	DataPoint{A: 3.60, B: 0.2106},
	DataPoint{A: 3.70, B: 0.2060},
	DataPoint{A: 3.80, B: 0.2017},
	DataPoint{A: 3.90, B: 0.1975},
	DataPoint{A: 4.00, B: 0.1935},
	DataPoint{A: 4.20, B: 0.1861},
	DataPoint{A: 4.40, B: 0.1793},
	DataPoint{A: 4.60, B: 0.1730},
	DataPoint{A: 4.80, B: 0.1672},
	DataPoint{A: 5.00, B: 0.1618},
}

var g7_curve []CurvePoint = calculateCurve(g7_table)

func calculateCurve(dataPoints []DataPoint) []CurvePoint {
	var curve []CurvePoint
	var numPoints int = len(dataPoints)
	var i int
	var x1, x2, x3, y1, y2, y3, a, b, c float64

	curve = make([]CurvePoint, numPoints)
	var rate float64 = (dataPoints[1].B - dataPoints[0].B) / (dataPoints[1].A - dataPoints[0].A)
	curve[0] = CurvePoint{A: 0, B: rate, C: dataPoints[0].B - dataPoints[0].A*rate}

	// rest as 2nd degree polynomials on three adjacent points
	for i = 1; i < numPoints-1; i++ {
		x1 = dataPoints[i-1].A
		x2 = dataPoints[i].A
		x3 = dataPoints[i+1].A
		y1 = dataPoints[i-1].B
		y2 = dataPoints[i].B
		y3 = dataPoints[i+1].B
		a = ((y3-y1)*(x2-x1) - (y2-y1)*(x3-x1)) / ((x3*x3-x1*x1)*(x2-x1) - (x2*x2-x1*x1)*(x3-x1))
		b = (y2 - y1 - a*(x2*x2-x1*x1)) / (x2 - x1)
		c = y1 - (a*x1*x1 + b*x1)
		curve[i] = CurvePoint{A: a, B: b, C: c}
	}
	rate = (dataPoints[numPoints-1].B - dataPoints[numPoints-2].B) / (dataPoints[numPoints-1].A - dataPoints[numPoints-2].A)
	curve[numPoints-1] = CurvePoint{0, rate, dataPoints[numPoints-1].B - dataPoints[numPoints-2].A*rate}
	return curve
}

func calculateByCurve(data []DataPoint, curve []CurvePoint, mach float64) float64 {
	var numPoints, m, mlo, mhi, mid int

	numPoints = len(curve)
	m = 0
	mlo = 0
	mhi = numPoints - 2

	for (mhi - mlo) > 1 {
		mid = int(math.Floor(float64(mhi+mlo) / 2.0))
		if data[mid].A < mach {
			mlo = mid
		} else {
			mhi = mid
		}
	}

	if (data[mhi].A - mach) > (mach - data[mlo].A) {
		m = mlo
	} else {
		m = mhi
	}

	return curve[m].C + mach*(curve[m].B+curve[m].A*mach)
}
