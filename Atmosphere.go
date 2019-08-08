package go_ballisticcalc

import (
	"fmt"
	"math"

	"github.com/gehtsoft-usa/go_ballisticcalc/bmath/unit"
)

const cIcaoStandardTemperatureR float64 = 518.67
const cIcaoFreezingPointTemperatureR float64 = 459.67
const cTemperatureGradient float64 = -3.56616e-03
const cIcaoStandardHumidity float64 = 0.0
const cPressureExponent float64 = -5.255876
const cSpeedOfSound float64 = 49.0223
const cA0 float64 = 1.24871
const cA1 float64 = 0.0988438
const cA2 float64 = 0.00152907
const cA3 float64 = -3.07031e-06
const cA4 float64 = 4.21329e-07
const cA5 float64 = 3.342e-04
const cStandardTemperature float64 = 59.0
const cStandardPressure float64 = 29.92
const cStandardDensity float64 = 0.076474

//Atmosphere describes the atmosphere conditions
type Atmosphere struct {
	altitude    unit.Distance
	pressure    unit.Pressure
	temperature unit.Temperature
	humidity    float64
	density     float64
	mach        unit.Velocity
	mach1       float64
}

//CreateDefaultAtmosphere creates a default atmosphere used in ballistic calculations
func CreateDefaultAtmosphere() Atmosphere {
	a := Atmosphere{altitude: unit.MustCreateDistance(0, unit.DistanceFoot),
		pressure:    unit.MustCreatePressure(cStandardPressure, unit.PressureInHg),
		temperature: unit.MustCreateTemperature(cStandardTemperature, unit.TemperatureFahrenheit),
		humidity:    0.78}
	a.calculate()
	return a
}

//CreateAtmosphere creates the atmosphere with the specified parameter
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

//CreateICAOAtmosphere creates default ICAO atmosphere for the specified altitude
func CreateICAOAtmosphere(altitude unit.Distance) Atmosphere {
	temperature := unit.MustCreateTemperature(
		cIcaoStandardTemperatureR+
			altitude.In(unit.DistanceFoot)*cTemperatureGradient-cIcaoFreezingPointTemperatureR,
		unit.TemperatureFahrenheit)

	pressure := unit.MustCreatePressure(
		cStandardPressure*
			math.Pow(cIcaoStandardTemperatureR/(temperature.In(unit.TemperatureFahrenheit)+
				cIcaoFreezingPointTemperatureR),
				cPressureExponent), unit.PressureInHg)

	a := Atmosphere{
		altitude:    altitude,
		temperature: temperature,
		pressure:    pressure,
		humidity:    cIcaoStandardHumidity,
	}

	a.calculate()

	return a

}

//Altitude returns the ground level altitude over the sea level
func (a Atmosphere) Altitude() unit.Distance {
	return a.altitude
}

//Temperature returns the temperature at the ground level
func (a Atmosphere) Temperature() unit.Temperature {
	return a.temperature
}

//Pressure returns the pressure at the ground level
func (a Atmosphere) Pressure() unit.Pressure {
	return a.pressure
}

//Humidity returns the relative humidity set in 0 to 1 coefficient
//
//multiply this value by 100 to get percents
func (a Atmosphere) Humidity() float64 {
	return a.humidity
}

//HumidityInPercents returns relative humidity in percents (0..100)
func (a Atmosphere) HumidityInPercents() float64 {
	return a.humidity * 100
}

func (a Atmosphere) String() string {
	return fmt.Sprintf("Altitude:%s,Pressure:%s,Temperature:%s,Humidity:%.2f%%",
		a.altitude, a.pressure, a.temperature, a.humidity*100)
}

func (a Atmosphere) getDensity() float64 {
	return a.density
}

func (a Atmosphere) getDensityFactor() float64 {
	return a.density / cStandardDensity
}

//Mach returns the speed of sound at the atmosphere with such parameters
func (a Atmosphere) Mach() unit.Velocity {
	return a.mach
}

func (a *Atmosphere) calculate0(t, p float64) (float64, float64) {
	var hc, et, et0, density, mach float64

	if t > 0.0 {
		et0 = cA0 + t*(cA1+t*(cA2+t*(cA3+t*cA4)))
		et = cA5 * a.humidity * et0
		hc = (p - 0.3783*et) / cStandardPressure
	} else {
		hc = 1.0
	}
	density = cStandardDensity * (cIcaoStandardTemperatureR / (t + cIcaoFreezingPointTemperatureR)) * hc
	mach = math.Sqrt(t+cIcaoFreezingPointTemperatureR) * cSpeedOfSound
	return density, mach

}

func (a *Atmosphere) calculate() {
	var t, p, density, mach float64
	t = a.temperature.In(unit.TemperatureFahrenheit)
	p = a.pressure.In(unit.PressureInHg)

	density, mach = a.calculate0(t, p)

	a.density = density
	a.mach1 = mach
	a.mach = unit.MustCreateVelocity(mach, unit.VelocityFPS)
}

func (a *Atmosphere) getDensityFactorAndMachForAltitude(altitude float64) (float64, float64) {
	var t, t0, p, ta, tb, orgAltitude, density, mach float64

	orgAltitude = a.altitude.In(unit.DistanceFoot)

	if math.Abs(orgAltitude-altitude) < 30 {
		density = a.density / cStandardDensity
		mach = a.mach1
		return density, mach
	}

	t0 = a.temperature.In(unit.TemperatureFahrenheit)
	p = a.pressure.In(unit.PressureInHg)

	ta = cIcaoStandardTemperatureR + orgAltitude*cTemperatureGradient - cIcaoFreezingPointTemperatureR
	tb = cIcaoStandardTemperatureR + altitude*cTemperatureGradient - cIcaoFreezingPointTemperatureR
	t = t0 + ta - tb
	p = p * math.Pow(t0/t, cPressureExponent)

	density, mach = a.calculate0(t, p)
	return density / cStandardDensity, mach
}
