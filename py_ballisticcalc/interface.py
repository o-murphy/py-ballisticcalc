from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
from typing import List
import math
import pandas as pd
import pyximport
pyximport.install()  # Will compile .pyx if necessary
from .trajectory_calculator import *
from .trajectory_data import *
from .shot_parameters import *
from .atmosphere import *
from .drag import *
from .projectile import *
from .weapon import *
from .wind import *
from .bmath import unit

@dataclass
class Display:
    units: str = '' # String to display
    digits: int = 0 # Decimal points to display
    def asDictEntry(self, s: str='', addSpace: bool=True):
        display = self.units
        if s:
            display = s + (' ' if (addSpace and self.units) else '') + display
        return (s, [display, self.digits])

UNIT_DISPLAY = {
    unit.AngularRadian         : Display('rad', 6),
    unit.AngularDegree         : Display('°', 4),
    unit.AngularMOA            : Display('MOA', 2),
    unit.AngularMil            : Display('mil', 2),
    unit.AngularMRad           : Display('mrad', 2),
    unit.AngularThousand       : Display('ths', 2),
    unit.AngularInchesPer100Yd : Display('iph', 2),
    unit.AngularCmPer100M      : Display('cm/100m', 2),
    unit.VelocityFPS : Display('fps', 0),
    unit.VelocityMPH : Display('mph', 0),
    unit.VelocityMPS : Display('m/s', 1),
    unit.VelocityKMH : Display('km/h', 0),
    unit.VelocityKT  : Display('kt', 0),
    unit.DistanceInch : Display('in.', 1),
    unit.DistanceFoot : Display('ft', 2),
    unit.DistanceYard : Display('yd', 0),
    unit.DistanceMile : Display('mi', 3),
    unit.DistanceNauticalMile : Display('nm', 3),
    unit.DistanceMillimeter : Display('mm', 0),
    unit.DistanceCentimeter : Display('cm', 1),
    unit.DistanceMeter      : Display('m', 2),
    unit.DistanceKilometer  : Display('km', 3),
    unit.DistanceLine       : Display('ln', 1),  # No idea what this is
    unit.PressureMmHg : Display('mmHg', 2),
    unit.PressureInHg : Display('inHg', 2),
    unit.PressureBar  : Display('bar', 2),
    unit.PressureHP   : Display('hPa', 4),
    unit.PressurePSI  : Display('psi', 4),
    unit.TemperatureFahrenheit : Display('°F', 0),
    unit.TemperatureCelsius    : Display('°C', 0),
    unit.TemperatureKelvin     : Display('°K', 0),
    unit.TemperatureRankin     : Display('°R', 0),
    unit.WeightGrain    : Display('gr', 1),
    unit.WeightOunce    : Display('oz', 2),
    unit.WeightGram     : Display('g', 2),
    unit.WeightPound    : Display('lb', 3),
    unit.WeightKilogram : Display('kg', 4),
    unit.WeightNewton   : Display('N', 3)
}

class ROW_TYPE(Enum):
    TRAJECTORY = 1
    ZERO = 2
    MACH1 = 3

@dataclass
class Bullet:
    BC: float       # G7 Ballistic Coefficient
    caliber: float
    grains: float   # Weight
    length: float
    muzzleVelocity: float
    velocityUnits: unit.Velocity = unit.VelocityFPS

@dataclass
class Gun:
    barrelTwist: float = 12 # Twist rate
    sightHeight: float = 0
    heightUnits: unit.Distance = unit.DistanceInch

@dataclass
class Air:
    """Defaults to standard atmosphere at sea level"""
    altitude: float = 0         # Elevation above sea level
    altUnits: unit.Distance = unit.DistanceFoot
    pressure: float = 29.92
    pressureUnits: int = PressureInHg
    temperature: float = 59
    tempUnits: int = TemperatureFahrenheit
    humidity: float = 0         # Relative Humidity
    windSpeed: float = 0
    windUnits: unit.Velocity = unit.VelocityMPH
    windDirection: float = 0    # Degrees; head-on = 0 degrees

@dataclass
class Calculator:
    bullet: Bullet
    gun: Gun = Gun()
    air: Air = Air()
    elevation: float = 0    # Barrel angle to sight line
    zeroDistance: float = 0
    distanceUnits: unit.Distance = unit.DistanceYard
    heightUnits: unit.Distance = unit.DistanceInch
    angleUnits: unit.Angular = unit.AngularMOA

    _bc: BallisticCoefficient = field(init=False, repr=False, compare=False)
    _ammo: Ammunition = field(init=False, repr=False, compare=False)
    _atmosphere: Atmosphere = field(init=False, repr=False, compare=False)
    _projectile: ProjectileWithDimensions = field(init=False, repr=False, compare=False)
    _weapon: Weapon = field(init=False, repr=False, compare=False)
    _wind: list[WindInfo] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self._updateObjects()

    def _updateObjects(self):
        """Create objects used by calculator based on current class datafields"""
        self._bc = BallisticCoefficient(self.bullet.BC, DragTableG7,
                                        unit.Weight(self.bullet.grains, unit.WeightGrain),
                                        unit.Distance(self.bullet.caliber, unit.DistanceInch), TableG7)
        self._projectile = ProjectileWithDimensions(self._bc,
                                                    unit.Distance(self.bullet.caliber, unit.DistanceInch),
                                                    unit.Distance(self.bullet.length, unit.DistanceInch),
                                                    unit.Weight(self.bullet.grains, unit.WeightGrain))
        self._ammo = Ammunition(self._projectile, unit.Velocity(self.bullet.muzzleVelocity, self.bullet.velocityUnits))
        self._atmosphere = Atmosphere(unit.Distance(self.air.altitude, self.air.altUnits),
                                      Pressure(self.air.pressure, self.air.pressureUnits),
                                      Temperature(self.air.temperature, self.air.tempUnits),
                                      self.air.humidity)
        self._wind = create_only_wind_info(unit.Velocity(self.air.windSpeed, self.air.windUnits),
                                           unit.Angular(self.air.windDirection, unit.AngularDegree))
        self._weapon = WeaponWithTwist(unit.Distance(self.gun.sightHeight, self.gun.heightUnits),
                                       ZeroInfo(unit.Distance(self.zeroDistance, self.distanceUnits)),
                                       TwistInfo(TwistRight, unit.Distance(self.gun.barrelTwist, unit.DistanceInch)))

    def elevationForZeroDistance(self, distance: float = None) -> float:
        """Calculates barrel elevation to hit zero at given distance"""
        calc = TrajectoryCalculator()

        if (distance is not None) and (distance != self.zeroDistance):
            self.zeroDistance = distance
            self._updateObjects()

        self.elevation = calc.sight_angle(self._ammo, self._weapon, self._atmosphere).get_in(self.angleUnits)
        return self.elevation
    
    def zeroGivenElevation(self, elevation: float = None, targetHeight: float = None) -> TrajectoryData:
        """Find the zero distance for a given barrel elevation"""
        if elevation is None:
            elevation = self.elevationForZeroDistance()
        calc = TrajectoryCalculator()
        shot = ShotParameters(unit.Angular(elevation, self.angleUnits),
                              unit.Distance(1e5, DistanceMile), unit.Distance(1e5, DistanceMile))
        data = calc.trajectory(self._ammo, self._weapon, self._atmosphere, shot, self._wind, stopAtZero=True)
        if len(data) > 1:
            return data[1]
        else:
            return data[0]  # No downrange zero found, so just return starting row

    def dangerSpace(self, trajectory: TrajectoryData, targetHeight: float) -> float:
        """Given a TrajectoryData row, we have the angle of travel of bullet at that point in its trajectory, which is at distance *d*.
            "Danger Space" is defined for *d* and for a target of height `targetHeight` as the error range for the target, meaning
            if the trajectory hits the center of the target when the target is exactly at *d*, then "Danger Space" is the distance
            before or after *d* across which the bullet would still hit somewhere on the target.  (This ignores windage; vertical only.)"""
        return -unit.Distance(targetHeight / math.tan(trajectory.angle().get_in(AngularRadian)), self.heightUnits).get_in(self.distanceUnits)

    def trajectory(self, range: float, step: float, elevation: float = None,
                   stopAtZero: bool = False, stopAtMach1: bool = False) -> pd.DataFrame:
        if elevation is None:
            elevation = self.elevationForZeroDistance()
        calc = TrajectoryCalculator()
        shot = ShotParameters(unit.Angular(elevation, self.angleUnits),
                              unit.Distance(range, self.distanceUnits),
                              unit.Distance(step, self.distanceUnits))
        data = calc.trajectory(self._ammo, self._weapon, self._atmosphere, shot, self._wind,
                               stopAtZero=stopAtZero, stopAtMach1=stopAtMach1)
        return self.trajectoryRowsToDataFrame(data)

    def trajectoryRowsToDataFrame(self, rows: List[TrajectoryData]) -> pd.DataFrame:
        # Dictionary of column header names and display precision
        self.tableCols = OrderedDict([UNIT_DISPLAY[self.distanceUnits].asDictEntry('Distance'),
                                      UNIT_DISPLAY[self.bullet.velocityUnits].asDictEntry('Velocity'),
                                      UNIT_DISPLAY[self.angleUnits].asDictEntry('Angle'),
                                      Display(digits=2).asDictEntry('Mach'),
                                      Display(digits=3).asDictEntry('Time'),
                                      UNIT_DISPLAY[self.heightUnits].asDictEntry('Drop'),
                                      UNIT_DISPLAY[self.angleUnits].asDictEntry('DropAngle'),
                                      UNIT_DISPLAY[self.heightUnits].asDictEntry('Windage'),
                                      UNIT_DISPLAY[self.angleUnits].asDictEntry('WindageAngle')
                                    ])

        r = []  # List of trajectory table rows
        for d in rows:
            distance = d.travelled_distance().get_in(self.distanceUnits)
            velocity = d.velocity().get_in(self.bullet.velocityUnits)
            angle = d.angle().get_in(self.angleUnits)
            mach = d.mach_velocity()
            time = d.time().total_seconds()
            drop = d.drop().get_in(self.heightUnits)
            dropMOA = d.drop_adjustment().get_in(self.angleUnits) if distance > 0 else 0
            wind = d.windage().get_in(self.heightUnits)
            windMOA = d.windage_adjustment().get_in(self.angleUnits) if distance > 0 else 0
            note = ''
            if d.row_type() == ROW_TYPE.MACH1.value: note = 'Mach1'
            elif d.row_type() == ROW_TYPE.ZERO.value: note = 'Zero'
            r.append([distance, velocity, angle, mach, time, drop, dropMOA, wind, windMOA, note])
    
        colNames = list(zip(*self.tableCols.values()))[0] + ('Note',)
        self.trajectoryTable = pd.DataFrame(r, columns=colNames)
        return self.trajectoryTable.round(dict(self.tableCols.values())).set_index(colNames[0])
