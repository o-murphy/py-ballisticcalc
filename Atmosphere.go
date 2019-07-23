package go_ballisticcalc

import (
	"fmt"
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

const cICAO_STANDARD_TEMPERATURE_R float64 = 518.67
const cICAO_FREEZING_POINT_TEMPERATURE_R float64 = 459.67
const cTEMPERATURE_GRADIENT float64 = -3.56616e-03
const cICAO_STANDARD_HUMIDITY float64 = 0.0
const cPRESSURE_EXPONENT float64 = -5.255876
const cSOUND_SPEED float64 = 49.0223
const c_A0 float64 = 1.24871
const c_A1 float64 = 0.0988438
const c_A2 float64 = 0.00152907
const c_A3 float64 = -3.07031e-06
const c_A4 float64 = 4.21329e-07
const c_A5 float64 = 3.342e-04
const cSTANDARD_TEMPERATURE float64 = 59.0
const cSTANDARD_PRESSURE float64 = 29.92
const cSTANDARD_DENSITY float64 = 0.076474

//The type describes the atmosphere conditions
type Atmosphere struct {
	altitude    unit.Distance
	pressure    unit.Pressure
	temperature unit.Temperature
	humidity    float64
	density     float64
	mach        unit.Velocity
}

//Creates a default atmosphere used in ballistic calculations
func CreateDefaultAtmosphere() Atmosphere {
	a := Atmosphere{altitude: unit.MustCreateDistance(0, unit.Distance_Foot),
		pressure:    unit.MustCreatePressure(cSTANDARD_PRESSURE, unit.Pressure_InHg),
		temperature: unit.MustCreateTemperature(cSTANDARD_TEMPERATURE, unit.Temperature_Fahrenheit),
		humidity:    0.78}
	a.calculate()
	return a
}

//Creates the exact atmosphere
func CreateAtmosphere(altitude unit.Distance, pressure unit.Pressure, temperature unit.Temperature, humidity float64) (Atmosphere, error) {
	if humidity < 0 || humidity > 100 {
		return CreateDefaultAtmosphere(), fmt.Errorf("Atmosphere : humidity must be in 0..1 or 0..100 range")
	}

	if humidity > 1 {
		humidity = humidity / 100
	}

	a := Atmosphere{altitude: altitude,
		pressure:    pressure,
		temperature: temperature,
		humidity:    humidity}

	a.calculate()
	return a, nil

}

//create default ICAO atmosphere for the specified altitude
func CreateICAOAtmosphere(altitude unit.Distance) Atmosphere {
	temperature := unit.MustCreateTemperature(
		cICAO_STANDARD_TEMPERATURE_R+
			altitude.In(unit.Distance_Foot)*cTEMPERATURE_GRADIENT-cICAO_FREEZING_POINT_TEMPERATURE_R,
		unit.Temperature_Fahrenheit)

	pressure := unit.MustCreatePressure(
		cSTANDARD_PRESSURE*
			math.Pow(cICAO_STANDARD_TEMPERATURE_R/(temperature.In(unit.Temperature_Fahrenheit)+
				cICAO_FREEZING_POINT_TEMPERATURE_R),
				cPRESSURE_EXPONENT), unit.Pressure_InHg)

	a := Atmosphere{
		altitude:    altitude,
		temperature: temperature,
		pressure:    pressure,
		humidity:    cICAO_STANDARD_HUMIDITY,
	}

	a.calculate()

	return a

}

func (a Atmosphere) Altitude() unit.Distance {
	return a.altitude
}

func (a Atmosphere) Temperature() unit.Temperature {
	return a.temperature
}

func (a Atmosphere) Pressure() unit.Pressure {
	return a.pressure
}

func (a Atmosphere) Humidity() float64 {
	return a.humidity
}

func (a Atmosphere) HumidityInPercents() float64 {
	return a.humidity * 100
}

func (a Atmosphere) String() string {
	return fmt.Sprintf("Altitude:%s,Pressure:%s,Temperature:%s,Humidity:%.2f%%",
		a.altitude, a.pressure, a.temperature, a.humidity*100)
}

func (a Atmosphere) Density() float64 {
	return a.density
}

func (a Atmosphere) DensityFactor() float64 {
	return a.density / cSTANDARD_DENSITY
}

func (a Atmosphere) Mach() unit.Velocity {
	return a.mach
}

func (a *Atmosphere) calculate() {
	var t, p, hc, et, et0 float64

	t = a.temperature.In(unit.Temperature_Fahrenheit)
	p = a.pressure.In(unit.Pressure_InHg)

	if t > 0.0 {
		et0 = c_A0 + t*(c_A1+t*(c_A2+t*(c_A3+t*c_A4)))
		et = c_A5 * a.humidity * et0
		hc = (p - 0.3783*et) / cSTANDARD_PRESSURE
	} else {
		hc = 1.0
	}
	a.density = cSTANDARD_DENSITY * (cICAO_STANDARD_TEMPERATURE_R / (t + cICAO_FREEZING_POINT_TEMPERATURE_R)) * hc
	a.mach = unit.MustCreateVelocity(math.Sqrt(t+cICAO_FREEZING_POINT_TEMPERATURE_R)*cSOUND_SPEED, unit.Velocity_FPS)
}
