package go_ballisticcalc

import (
    "fmt"
    "math"
)

//DragTableG1 is identifier for G1 ballistic table
const DragTableG1 byte = 1

//DragTableG2 is identifier for G2 ballistic table
const DragTableG2 byte = 2

//DragTableG5 is identifier for G5 ballistic table
const DragTableG5 byte = 3

//DragTableG6 is identifier for G6 ballistic table
const DragTableG6 byte = 4

//DragTableG7 is identifier for G7 ballistic table
const DragTableG7 byte = 5

//DragTableG8 is identifier for G8 ballistic table
const DragTableG8 byte = 6

//DragTableGL is identifier for GL ballistic table
const DragTableGS byte = 7

//DragTableGI is identifier for GI ballistic table
const DragTableGI byte = 8

type dragFunction func(float64) float64

//BallisticCoefficient keeps data about ballistic coefficient
//of a projectile
//
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
    case DragTableG1:
        return func(mach float64) float64 {
            return calculateByCurve(g1Table, g1Curve, mach)
        }
    case DragTableG2:
         return func(mach float64) float64 {
            return calculateByCurve(g2Table, g2Curve, mach)
        }
    case DragTableG5:
         return func(mach float64) float64 {
            return calculateByCurve(g5Table, g5Curve, mach)
        }
    case DragTableG6:
         return func(mach float64) float64 {
            return calculateByCurve(g6Table, g6Curve, mach)
        }
    case DragTableG7:
        return func(mach float64) float64 {
            return calculateByCurve(g7Table, g7Curve, mach)
        }
    case DragTableG8:
        return  func(mach float64) float64 {
            return calculateByCurve(g8Table, g8Curve, mach)
        }
    case DragTableGI:
        return  func(mach float64) float64 {
            return calculateByCurve(gITable, gICurve, mach)
        }
    case DragTableGS:
        return  func(mach float64) float64 {
            return calculateByCurve(gSTable, gSCurve, mach)
        }
    default:
        panic(fmt.Errorf("Unknown drag table type"))
    }
}

//CreateBallisticCoefficient creates ballistic coefficient object using the
//ballistic coefficient value and ballistic table.
func CreateBallisticCoefficient(value float64, dragTable byte) (BallisticCoefficient, error) {
    if dragTable < DragTableG1 || DragTableG1 > DragTableGI {
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

//Value returns the ballistic coefficient value
func (v BallisticCoefficient) Value() float64 {
    return v.value
}

//Table return the name of the ballistic table
func (v BallisticCoefficient) Table() byte {
    return v.table
}

//Drag calculates the aerodynamic drag (deceleration factor) calculated for the speed
//expressed in mach (speed of sound)
func (v BallisticCoefficient) Drag(mach float64) float64 {
    return v.drag(mach) * 2.08551e-04 / v.value
}

//DataPoint is one value of the ballistic table used in
//table-based calculations below
//
//The calculation is based on original JavaScript code
//by Alexandre Trofimov
type DataPoint struct {
    A, B float64
}

//CurvePoint is an approximation of drag to speed function curve made on the
//base of the ballistic
type CurvePoint struct {
    A, B, C float64
}

var g1Table = []DataPoint{
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

var g1Curve = calculateCurve(g1Table)

var g7Table = []DataPoint{
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

var g7Curve = calculateCurve(g7Table)

var g2Table = []DataPoint{
    DataPoint{A: 0.00, B: 0.2303},
    DataPoint{A: 0.05, B: 0.2298},
    DataPoint{A: 0.10, B: 0.2287},
    DataPoint{A: 0.15, B: 0.2271},
    DataPoint{A: 0.20, B: 0.2251},
    DataPoint{A: 0.25, B: 0.2227},
    DataPoint{A: 0.30, B: 0.2196},
    DataPoint{A: 0.35, B: 0.2156},
    DataPoint{A: 0.40, B: 0.2107},
    DataPoint{A: 0.45, B: 0.2048},
    DataPoint{A: 0.50, B: 0.1980},
    DataPoint{A: 0.55, B: 0.1905},
    DataPoint{A: 0.60, B: 0.1828},
    DataPoint{A: 0.65, B: 0.1758},
    DataPoint{A: 0.70, B: 0.1702},
    DataPoint{A: 0.75, B: 0.1669},
    DataPoint{A: 0.775, B: 0.1664},
    DataPoint{A: 0.80, B: 0.1667},
    DataPoint{A: 0.825, B: 0.1682},
    DataPoint{A: 0.85, B: 0.1711},
    DataPoint{A: 0.875, B: 0.1761},
    DataPoint{A: 0.90, B: 0.1831},
    DataPoint{A: 0.925, B: 0.2004},
    DataPoint{A: 0.95, B: 0.2589},
    DataPoint{A: 0.975, B: 0.3492},
    DataPoint{A: 1.0, B: 0.3983},
    DataPoint{A: 1.025, B: 0.4075},
    DataPoint{A: 1.05, B: 0.4103},
    DataPoint{A: 1.075, B: 0.4114},
    DataPoint{A: 1.10, B: 0.4106},
    DataPoint{A: 1.125, B: 0.4089},
    DataPoint{A: 1.15, B: 0.4068},
    DataPoint{A: 1.175, B: 0.4046},
    DataPoint{A: 1.20, B: 0.4021},
    DataPoint{A: 1.25, B: 0.3966},
    DataPoint{A: 1.30, B: 0.3904},
    DataPoint{A: 1.35, B: 0.3835},
    DataPoint{A: 1.40, B: 0.3759},
    DataPoint{A: 1.45, B: 0.3678},
    DataPoint{A: 1.50, B: 0.3594},
    DataPoint{A: 1.55, B: 0.3512},
    DataPoint{A: 1.60, B: 0.3432},
    DataPoint{A: 1.65, B: 0.3356},
    DataPoint{A: 1.70, B: 0.3282},
    DataPoint{A: 1.75, B: 0.3213},
    DataPoint{A: 1.80, B: 0.3149},
    DataPoint{A: 1.85, B: 0.3089},
    DataPoint{A: 1.90, B: 0.3033},
    DataPoint{A: 1.95, B: 0.2982},
    DataPoint{A: 2.00, B: 0.2933},
    DataPoint{A: 2.05, B: 0.2889},
    DataPoint{A: 2.10, B: 0.2846},
    DataPoint{A: 2.15, B: 0.2806},
    DataPoint{A: 2.20, B: 0.2768},
    DataPoint{A: 2.25, B: 0.2731},
    DataPoint{A: 2.30, B: 0.2696},
    DataPoint{A: 2.35, B: 0.2663},
    DataPoint{A: 2.40, B: 0.2632},
    DataPoint{A: 2.45, B: 0.2602},
    DataPoint{A: 2.50, B: 0.2572},
    DataPoint{A: 2.55, B: 0.2543},
    DataPoint{A: 2.60, B: 0.2515},
    DataPoint{A: 2.65, B: 0.2487},
    DataPoint{A: 2.70, B: 0.2460},
    DataPoint{A: 2.75, B: 0.2433},
    DataPoint{A: 2.80, B: 0.2408},
    DataPoint{A: 2.85, B: 0.2382},
    DataPoint{A: 2.90, B: 0.2357},
    DataPoint{A: 2.95, B: 0.2333},
    DataPoint{A: 3.00, B: 0.2309},
    DataPoint{A: 3.10, B: 0.2262},
    DataPoint{A: 3.20, B: 0.2217},
    DataPoint{A: 3.30, B: 0.2173},
    DataPoint{A: 3.40, B: 0.2132},
    DataPoint{A: 3.50, B: 0.2091},
    DataPoint{A: 3.60, B: 0.2052},
    DataPoint{A: 3.70, B: 0.2014},
    DataPoint{A: 3.80, B: 0.1978},
    DataPoint{A: 3.90, B: 0.1944},
    DataPoint{A: 4.00, B: 0.1912},
    DataPoint{A: 4.20, B: 0.1851},
    DataPoint{A: 4.40, B: 0.1794},
    DataPoint{A: 4.60, B: 0.1741},
    DataPoint{A: 4.80, B: 0.1693},
    DataPoint{A: 5.00, B: 0.1648},
}

var g2Curve = calculateCurve(g2Table)

var g5Table = []DataPoint{
    DataPoint{A: 0.00, B: 0.1710},
    DataPoint{A: 0.05, B: 0.1719},
    DataPoint{A: 0.10, B: 0.1727},
    DataPoint{A: 0.15, B: 0.1732},
    DataPoint{A: 0.20, B: 0.1734},
    DataPoint{A: 0.25, B: 0.1730},
    DataPoint{A: 0.30, B: 0.1718},
    DataPoint{A: 0.35, B: 0.1696},
    DataPoint{A: 0.40, B: 0.1668},
    DataPoint{A: 0.45, B: 0.1637},
    DataPoint{A: 0.50, B: 0.1603},
    DataPoint{A: 0.55, B: 0.1566},
    DataPoint{A: 0.60, B: 0.1529},
    DataPoint{A: 0.65, B: 0.1497},
    DataPoint{A: 0.70, B: 0.1473},
    DataPoint{A: 0.75, B: 0.1463},
    DataPoint{A: 0.80, B: 0.1489},
    DataPoint{A: 0.85, B: 0.1583},
    DataPoint{A: 0.875, B: 0.1672},
    DataPoint{A: 0.90, B: 0.1815},
    DataPoint{A: 0.925, B: 0.2051},
    DataPoint{A: 0.95, B: 0.2413},
    DataPoint{A: 0.975, B: 0.2884},
    DataPoint{A: 1.0, B: 0.3379},
    DataPoint{A: 1.025, B: 0.3785},
    DataPoint{A: 1.05, B: 0.4032},
    DataPoint{A: 1.075, B: 0.4147},
    DataPoint{A: 1.10, B: 0.4201},
    DataPoint{A: 1.15, B: 0.4278},
    DataPoint{A: 1.20, B: 0.4338},
    DataPoint{A: 1.25, B: 0.4373},
    DataPoint{A: 1.30, B: 0.4392},
    DataPoint{A: 1.35, B: 0.4403},
    DataPoint{A: 1.40, B: 0.4406},
    DataPoint{A: 1.45, B: 0.4401},
    DataPoint{A: 1.50, B: 0.4386},
    DataPoint{A: 1.55, B: 0.4362},
    DataPoint{A: 1.60, B: 0.4328},
    DataPoint{A: 1.65, B: 0.4286},
    DataPoint{A: 1.70, B: 0.4237},
    DataPoint{A: 1.75, B: 0.4182},
    DataPoint{A: 1.80, B: 0.4121},
    DataPoint{A: 1.85, B: 0.4057},
    DataPoint{A: 1.90, B: 0.3991},
    DataPoint{A: 1.95, B: 0.3926},
    DataPoint{A: 2.00, B: 0.3861},
    DataPoint{A: 2.05, B: 0.3800},
    DataPoint{A: 2.10, B: 0.3741},
    DataPoint{A: 2.15, B: 0.3684},
    DataPoint{A: 2.20, B: 0.3630},
    DataPoint{A: 2.25, B: 0.3578},
    DataPoint{A: 2.30, B: 0.3529},
    DataPoint{A: 2.35, B: 0.3481},
    DataPoint{A: 2.40, B: 0.3435},
    DataPoint{A: 2.45, B: 0.3391},
    DataPoint{A: 2.50, B: 0.3349},
    DataPoint{A: 2.60, B: 0.3269},
    DataPoint{A: 2.70, B: 0.3194},
    DataPoint{A: 2.80, B: 0.3125},
    DataPoint{A: 2.90, B: 0.3060},
    DataPoint{A: 3.00, B: 0.2999},
    DataPoint{A: 3.10, B: 0.2942},
    DataPoint{A: 3.20, B: 0.2889},
    DataPoint{A: 3.30, B: 0.2838},
    DataPoint{A: 3.40, B: 0.2790},
    DataPoint{A: 3.50, B: 0.2745},
    DataPoint{A: 3.60, B: 0.2703},
    DataPoint{A: 3.70, B: 0.2662},
    DataPoint{A: 3.80, B: 0.2624},
    DataPoint{A: 3.90, B: 0.2588},
    DataPoint{A: 4.00, B: 0.2553},
    DataPoint{A: 4.20, B: 0.2488},
    DataPoint{A: 4.40, B: 0.2429},
    DataPoint{A: 4.60, B: 0.2376},
    DataPoint{A: 4.80, B: 0.2326},
    DataPoint{A: 5.00, B: 0.2280},
}

var g5Curve = calculateCurve(g5Table)

var g6Table = []DataPoint{
    DataPoint{A: 0.00, B: 0.2617},
    DataPoint{A: 0.05, B: 0.2553},
    DataPoint{A: 0.10, B: 0.2491},
    DataPoint{A: 0.15, B: 0.2432},
    DataPoint{A: 0.20, B: 0.2376},
    DataPoint{A: 0.25, B: 0.2324},
    DataPoint{A: 0.30, B: 0.2278},
    DataPoint{A: 0.35, B: 0.2238},
    DataPoint{A: 0.40, B: 0.2205},
    DataPoint{A: 0.45, B: 0.2177},
    DataPoint{A: 0.50, B: 0.2155},
    DataPoint{A: 0.55, B: 0.2138},
    DataPoint{A: 0.60, B: 0.2126},
    DataPoint{A: 0.65, B: 0.2121},
    DataPoint{A: 0.70, B: 0.2122},
    DataPoint{A: 0.75, B: 0.2132},
    DataPoint{A: 0.80, B: 0.2154},
    DataPoint{A: 0.85, B: 0.2194},
    DataPoint{A: 0.875, B: 0.2229},
    DataPoint{A: 0.90, B: 0.2297},
    DataPoint{A: 0.925, B: 0.2449},
    DataPoint{A: 0.95, B: 0.2732},
    DataPoint{A: 0.975, B: 0.3141},
    DataPoint{A: 1.0, B: 0.3597},
    DataPoint{A: 1.025, B: 0.3994},
    DataPoint{A: 1.05, B: 0.4261},
    DataPoint{A: 1.075, B: 0.4402},
    DataPoint{A: 1.10, B: 0.4465},
    DataPoint{A: 1.125, B: 0.4490},
    DataPoint{A: 1.15, B: 0.4497},
    DataPoint{A: 1.175, B: 0.4494},
    DataPoint{A: 1.20, B: 0.4482},
    DataPoint{A: 1.225, B: 0.4464},
    DataPoint{A: 1.25, B: 0.4441},
    DataPoint{A: 1.30, B: 0.4390},
    DataPoint{A: 1.35, B: 0.4336},
    DataPoint{A: 1.40, B: 0.4279},
    DataPoint{A: 1.45, B: 0.4221},
    DataPoint{A: 1.50, B: 0.4162},
    DataPoint{A: 1.55, B: 0.4102},
    DataPoint{A: 1.60, B: 0.4042},
    DataPoint{A: 1.65, B: 0.3981},
    DataPoint{A: 1.70, B: 0.3919},
    DataPoint{A: 1.75, B: 0.3855},
    DataPoint{A: 1.80, B: 0.3788},
    DataPoint{A: 1.85, B: 0.3721},
    DataPoint{A: 1.90, B: 0.3652},
    DataPoint{A: 1.95, B: 0.3583},
    DataPoint{A: 2.00, B: 0.3515},
    DataPoint{A: 2.05, B: 0.3447},
    DataPoint{A: 2.10, B: 0.3381},
    DataPoint{A: 2.15, B: 0.3314},
    DataPoint{A: 2.20, B: 0.3249},
    DataPoint{A: 2.25, B: 0.3185},
    DataPoint{A: 2.30, B: 0.3122},
    DataPoint{A: 2.35, B: 0.3060},
    DataPoint{A: 2.40, B: 0.3000},
    DataPoint{A: 2.45, B: 0.2941},
    DataPoint{A: 2.50, B: 0.2883},
    DataPoint{A: 2.60, B: 0.2772},
    DataPoint{A: 2.70, B: 0.2668},
    DataPoint{A: 2.80, B: 0.2574},
    DataPoint{A: 2.90, B: 0.2487},
    DataPoint{A: 3.00, B: 0.2407},
    DataPoint{A: 3.10, B: 0.2333},
    DataPoint{A: 3.20, B: 0.2265},
    DataPoint{A: 3.30, B: 0.2202},
    DataPoint{A: 3.40, B: 0.2144},
    DataPoint{A: 3.50, B: 0.2089},
    DataPoint{A: 3.60, B: 0.2039},
    DataPoint{A: 3.70, B: 0.1991},
    DataPoint{A: 3.80, B: 0.1947},
    DataPoint{A: 3.90, B: 0.1905},
    DataPoint{A: 4.00, B: 0.1866},
    DataPoint{A: 4.20, B: 0.1794},
    DataPoint{A: 4.40, B: 0.1730},
    DataPoint{A: 4.60, B: 0.1673},
    DataPoint{A: 4.80, B: 0.1621},
    DataPoint{A: 5.00, B: 0.1574},
}

var g6Curve = calculateCurve(g6Table)

var g8Table = []DataPoint{
    DataPoint{A: 0.00, B: 0.2105},
    DataPoint{A: 0.05, B: 0.2105},
    DataPoint{A: 0.10, B: 0.2104},
    DataPoint{A: 0.15, B: 0.2104},
    DataPoint{A: 0.20, B: 0.2103},
    DataPoint{A: 0.25, B: 0.2103},
    DataPoint{A: 0.30, B: 0.2103},
    DataPoint{A: 0.35, B: 0.2103},
    DataPoint{A: 0.40, B: 0.2103},
    DataPoint{A: 0.45, B: 0.2102},
    DataPoint{A: 0.50, B: 0.2102},
    DataPoint{A: 0.55, B: 0.2102},
    DataPoint{A: 0.60, B: 0.2102},
    DataPoint{A: 0.65, B: 0.2102},
    DataPoint{A: 0.70, B: 0.2103},
    DataPoint{A: 0.75, B: 0.2103},
    DataPoint{A: 0.80, B: 0.2104},
    DataPoint{A: 0.825, B: 0.2104},
    DataPoint{A: 0.85, B: 0.2105},
    DataPoint{A: 0.875, B: 0.2106},
    DataPoint{A: 0.90, B: 0.2109},
    DataPoint{A: 0.925, B: 0.2183},
    DataPoint{A: 0.95, B: 0.2571},
    DataPoint{A: 0.975, B: 0.3358},
    DataPoint{A: 1.0, B: 0.4068},
    DataPoint{A: 1.025, B: 0.4378},
    DataPoint{A: 1.05, B: 0.4476},
    DataPoint{A: 1.075, B: 0.4493},
    DataPoint{A: 1.10, B: 0.4477},
    DataPoint{A: 1.125, B: 0.4450},
    DataPoint{A: 1.15, B: 0.4419},
    DataPoint{A: 1.20, B: 0.4353},
    DataPoint{A: 1.25, B: 0.4283},
    DataPoint{A: 1.30, B: 0.4208},
    DataPoint{A: 1.35, B: 0.4133},
    DataPoint{A: 1.40, B: 0.4059},
    DataPoint{A: 1.45, B: 0.3986},
    DataPoint{A: 1.50, B: 0.3915},
    DataPoint{A: 1.55, B: 0.3845},
    DataPoint{A: 1.60, B: 0.3777},
    DataPoint{A: 1.65, B: 0.3710},
    DataPoint{A: 1.70, B: 0.3645},
    DataPoint{A: 1.75, B: 0.3581},
    DataPoint{A: 1.80, B: 0.3519},
    DataPoint{A: 1.85, B: 0.3458},
    DataPoint{A: 1.90, B: 0.3400},
    DataPoint{A: 1.95, B: 0.3343},
    DataPoint{A: 2.00, B: 0.3288},
    DataPoint{A: 2.05, B: 0.3234},
    DataPoint{A: 2.10, B: 0.3182},
    DataPoint{A: 2.15, B: 0.3131},
    DataPoint{A: 2.20, B: 0.3081},
    DataPoint{A: 2.25, B: 0.3032},
    DataPoint{A: 2.30, B: 0.2983},
    DataPoint{A: 2.35, B: 0.2937},
    DataPoint{A: 2.40, B: 0.2891},
    DataPoint{A: 2.45, B: 0.2845},
    DataPoint{A: 2.50, B: 0.2802},
    DataPoint{A: 2.60, B: 0.2720},
    DataPoint{A: 2.70, B: 0.2642},
    DataPoint{A: 2.80, B: 0.2569},
    DataPoint{A: 2.90, B: 0.2499},
    DataPoint{A: 3.00, B: 0.2432},
    DataPoint{A: 3.10, B: 0.2368},
    DataPoint{A: 3.20, B: 0.2308},
    DataPoint{A: 3.30, B: 0.2251},
    DataPoint{A: 3.40, B: 0.2197},
    DataPoint{A: 3.50, B: 0.2147},
    DataPoint{A: 3.60, B: 0.2101},
    DataPoint{A: 3.70, B: 0.2058},
    DataPoint{A: 3.80, B: 0.2019},
    DataPoint{A: 3.90, B: 0.1983},
    DataPoint{A: 4.00, B: 0.1950},
    DataPoint{A: 4.20, B: 0.1890},
    DataPoint{A: 4.40, B: 0.1837},
    DataPoint{A: 4.60, B: 0.1791},
    DataPoint{A: 4.80, B: 0.1750},
    DataPoint{A: 5.00, B: 0.1713},
}

var g8Curve = calculateCurve(g8Table)

var gITable = []DataPoint{
    DataPoint{A: 0.00, B: 0.2282},
    DataPoint{A: 0.05, B: 0.2282},
    DataPoint{A: 0.10, B: 0.2282},
    DataPoint{A: 0.15, B: 0.2282},
    DataPoint{A: 0.20, B: 0.2282},
    DataPoint{A: 0.25, B: 0.2282},
    DataPoint{A: 0.30, B: 0.2282},
    DataPoint{A: 0.35, B: 0.2282},
    DataPoint{A: 0.40, B: 0.2282},
    DataPoint{A: 0.45, B: 0.2282},
    DataPoint{A: 0.50, B: 0.2282},
    DataPoint{A: 0.55, B: 0.2282},
    DataPoint{A: 0.60, B: 0.2282},
    DataPoint{A: 0.65, B: 0.2282},
    DataPoint{A: 0.70, B: 0.2282},
    DataPoint{A: 0.725, B: 0.2353},
    DataPoint{A: 0.75, B: 0.2434},
    DataPoint{A: 0.775, B: 0.2515},
    DataPoint{A: 0.80, B: 0.2596},
    DataPoint{A: 0.825, B: 0.2677},
    DataPoint{A: 0.85, B: 0.2759},
    DataPoint{A: 0.875, B: 0.2913},
    DataPoint{A: 0.90, B: 0.3170},
    DataPoint{A: 0.925, B: 0.3442},
    DataPoint{A: 0.95, B: 0.3728},
    DataPoint{A: 1.0, B: 0.4349},
    DataPoint{A: 1.05, B: 0.5034},
    DataPoint{A: 1.075, B: 0.5402},
    DataPoint{A: 1.10, B: 0.5756},
    DataPoint{A: 1.125, B: 0.5887},
    DataPoint{A: 1.15, B: 0.6018},
    DataPoint{A: 1.175, B: 0.6149},
    DataPoint{A: 1.20, B: 0.6279},
    DataPoint{A: 1.225, B: 0.6418},
    DataPoint{A: 1.25, B: 0.6423},
    DataPoint{A: 1.30, B: 0.6423},
    DataPoint{A: 1.35, B: 0.6423},
    DataPoint{A: 1.40, B: 0.6423},
    DataPoint{A: 1.45, B: 0.6423},
    DataPoint{A: 1.50, B: 0.6423},
    DataPoint{A: 1.55, B: 0.6423},
    DataPoint{A: 1.60, B: 0.6423},
    DataPoint{A: 1.625, B: 0.6407},
    DataPoint{A: 1.65, B: 0.6378},
    DataPoint{A: 1.70, B: 0.6321},
    DataPoint{A: 1.75, B: 0.6266},
    DataPoint{A: 1.80, B: 0.6213},
    DataPoint{A: 1.85, B: 0.6163},
    DataPoint{A: 1.90, B: 0.6113},
    DataPoint{A: 1.95, B: 0.6066},
    DataPoint{A: 2.00, B: 0.6020},
    DataPoint{A: 2.05, B: 0.5976},
    DataPoint{A: 2.10, B: 0.5933},
    DataPoint{A: 2.15, B: 0.5891},
    DataPoint{A: 2.20, B: 0.5850},
    DataPoint{A: 2.25, B: 0.5811},
    DataPoint{A: 2.30, B: 0.5773},
    DataPoint{A: 2.35, B: 0.5733},
    DataPoint{A: 2.40, B: 0.5679},
    DataPoint{A: 2.45, B: 0.5626},
    DataPoint{A: 2.50, B: 0.5576},
    DataPoint{A: 2.60, B: 0.5478},
    DataPoint{A: 2.70, B: 0.5386},
    DataPoint{A: 2.80, B: 0.5298},
    DataPoint{A: 2.90, B: 0.5215},
    DataPoint{A: 3.00, B: 0.5136},
    DataPoint{A: 3.10, B: 0.5061},
    DataPoint{A: 3.20, B: 0.4989},
    DataPoint{A: 3.30, B: 0.4921},
    DataPoint{A: 3.40, B: 0.4855},
    DataPoint{A: 3.50, B: 0.4792},
    DataPoint{A: 3.60, B: 0.4732},
    DataPoint{A: 3.70, B: 0.4674},
    DataPoint{A: 3.80, B: 0.4618},
    DataPoint{A: 3.90, B: 0.4564},
    DataPoint{A: 4.00, B: 0.4513},
    DataPoint{A: 4.20, B: 0.4415},
    DataPoint{A: 4.40, B: 0.4323},
    DataPoint{A: 4.60, B: 0.4238},
    DataPoint{A: 4.80, B: 0.4157},
    DataPoint{A: 5.00, B: 0.4082},
}

var gICurve = calculateCurve(gITable)

var gSTable = []DataPoint{
    DataPoint{A: 0.00, B: 0.4662},
    DataPoint{A: 0.05, B: 0.4689},
    DataPoint{A: 0.10, B: 0.4717},
    DataPoint{A: 0.15, B: 0.4745},
    DataPoint{A: 0.20, B: 0.4772},
    DataPoint{A: 0.25, B: 0.4800},
    DataPoint{A: 0.30, B: 0.4827},
    DataPoint{A: 0.35, B: 0.4852},
    DataPoint{A: 0.40, B: 0.4882},
    DataPoint{A: 0.45, B: 0.4920},
    DataPoint{A: 0.50, B: 0.4970},
    DataPoint{A: 0.55, B: 0.5080},
    DataPoint{A: 0.60, B: 0.5260},
    DataPoint{A: 0.65, B: 0.5590},
    DataPoint{A: 0.70, B: 0.5920},
    DataPoint{A: 0.75, B: 0.6258},
    DataPoint{A: 0.80, B: 0.6610},
    DataPoint{A: 0.85, B: 0.6985},
    DataPoint{A: 0.90, B: 0.7370},
    DataPoint{A: 0.95, B: 0.7757},
    DataPoint{A: 1.0, B: 0.8140},
    DataPoint{A: 1.05, B: 0.8512},
    DataPoint{A: 1.10, B: 0.8870},
    DataPoint{A: 1.15, B: 0.9210},
    DataPoint{A: 1.20, B: 0.9510},
    DataPoint{A: 1.25, B: 0.9740},
    DataPoint{A: 1.30, B: 0.9910},
    DataPoint{A: 1.35, B: 0.9990},
    DataPoint{A: 1.40, B: 1.0030},
    DataPoint{A: 1.45, B: 1.0060},
    DataPoint{A: 1.50, B: 1.0080},
    DataPoint{A: 1.55, B: 1.0090},
    DataPoint{A: 1.60, B: 1.0090},
    DataPoint{A: 1.65, B: 1.0090},
    DataPoint{A: 1.70, B: 1.0090},
    DataPoint{A: 1.75, B: 1.0080},
    DataPoint{A: 1.80, B: 1.0070},
    DataPoint{A: 1.85, B: 1.0060},
    DataPoint{A: 1.90, B: 1.0040},
    DataPoint{A: 1.95, B: 1.0025},
    DataPoint{A: 2.00, B: 1.0010},
    DataPoint{A: 2.05, B: 0.9990},
    DataPoint{A: 2.10, B: 0.9970},
    DataPoint{A: 2.15, B: 0.9956},
    DataPoint{A: 2.20, B: 0.9940},
    DataPoint{A: 2.25, B: 0.9916},
    DataPoint{A: 2.30, B: 0.9890},
    DataPoint{A: 2.35, B: 0.9869},
    DataPoint{A: 2.40, B: 0.9850},
    DataPoint{A: 2.45, B: 0.9830},
    DataPoint{A: 2.50, B: 0.9810},
    DataPoint{A: 2.55, B: 0.9790},
    DataPoint{A: 2.60, B: 0.9770},
    DataPoint{A: 2.65, B: 0.9750},
    DataPoint{A: 2.70, B: 0.9730},
    DataPoint{A: 2.75, B: 0.9710},
    DataPoint{A: 2.80, B: 0.9690},
    DataPoint{A: 2.85, B: 0.9670},
    DataPoint{A: 2.90, B: 0.9650},
    DataPoint{A: 2.95, B: 0.9630},
    DataPoint{A: 3.00, B: 0.9610},
    DataPoint{A: 3.05, B: 0.9589},
    DataPoint{A: 3.10, B: 0.9570},
    DataPoint{A: 3.15, B: 0.9555},
    DataPoint{A: 3.20, B: 0.9540},
    DataPoint{A: 3.25, B: 0.9520},
    DataPoint{A: 3.30, B: 0.9500},
    DataPoint{A: 3.35, B: 0.9485},
    DataPoint{A: 3.40, B: 0.9470},
    DataPoint{A: 3.45, B: 0.9450},
    DataPoint{A: 3.50, B: 0.9430},
    DataPoint{A: 3.55, B: 0.9414},
    DataPoint{A: 3.60, B: 0.9400},
    DataPoint{A: 3.65, B: 0.9385},
    DataPoint{A: 3.70, B: 0.9370},
    DataPoint{A: 3.75, B: 0.9355},
    DataPoint{A: 3.80, B: 0.9340},
    DataPoint{A: 3.85, B: 0.9325},
    DataPoint{A: 3.90, B: 0.9310},
    DataPoint{A: 3.95, B: 0.9295},
    DataPoint{A: 4.00, B: 0.9280},
}

var gSCurve = calculateCurve(gSTable)


func calculateCurve(dataPoints []DataPoint) []CurvePoint {
    var curve []CurvePoint
    var numPoints = len(dataPoints)
    var i int
    var x1, x2, x3, y1, y2, y3, a, b, c float64

    curve = make([]CurvePoint, numPoints)
    var rate = (dataPoints[1].B - dataPoints[0].B) / (dataPoints[1].A - dataPoints[0].A)
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
