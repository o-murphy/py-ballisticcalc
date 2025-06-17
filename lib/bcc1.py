# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
from abc import ABC, abstractmethod
import ctypes
import os

from typing_extensions import Optional, NamedTuple, Union, List, Tuple, Final, TypedDict

from py_ballisticcalc.conditions import Atmo, Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger, get_debug
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import (Distance, Angular, Velocity, Weight,
                                   Energy, Pressure, Temperature, Unit)
from py_ballisticcalc.vector import Vector
from py_ballisticcalc import *

__all__ = (
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'BaseIntegrationEngine',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'create_trajectory_row',
    '_TrajectoryDataFilter',
    '_WindSock',
    'CurvePoint',
    'CTypesIntegrationEngine' # Added new engine
)

# --- CTYPES INTERFACE START ---
# This section is copied directly from the user's provided ctypes interface script.

# --- 1. Load the shared library ---
# Adjust the library name and path as necessary for your system
try:
    if os.name == 'posix':  # Linux or macOS
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.so')
    elif os.name == 'nt':  # Windows
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.dll')
    else:
        raise OSError("Unsupported operating system")

    _engine_lib = ctypes.CDLL(_lib_path)
except OSError as e:
    print(f"Error loading shared library: {e}")
    print("Please ensure your C code is compiled into a shared library (e.g., bcc.so or bcc.dll)")
    _engine_lib = None # Set to None to prevent further errors if library isn't loaded

# --- 2. Define C Structures using ctypes.Structure ---

# V3dT from v3d.h
class V3dT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
    ]

# ConfigT from config.h
class ConfigT(ctypes.Structure):
    _fields_ = [
        ("cMaxCalcStepSizeFeet", ctypes.c_double),
        ("cZeroFindingAccuracy", ctypes.c_double),
        ("cMinimumVelocity", ctypes.c_double),
        ("cMaximumDrop", ctypes.c_double),
        ("cMaxIterations", ctypes.c_int),
        ("cGravityConstant", ctypes.c_double),
        ("cMinimumAltitude", ctypes.c_double),
    ]

# AtmosphereT from atmo.h
class AtmosphereT(ctypes.Structure):
    _fields_ = [
        ("t0", ctypes.c_double),
        ("a0", ctypes.c_double),
        ("p0", ctypes.c_double),
        ("mach", ctypes.c_double),
        ("densityFactor", ctypes.c_double),
        ("cLowestTempC", ctypes.c_double),
    ]

# DragTablePointT from drag.h
class DragTablePointT(ctypes.Structure):
    _fields_ = [
        ("CD", ctypes.c_double),
        ("Mach", ctypes.c_double),
    ]

# DragTableT from drag.h
class DragTableT(ctypes.Structure):
    _fields_ = [
        ("table", ctypes.POINTER(DragTablePointT)),
        ("length", ctypes.c_size_t),
    ]

# CurvePointT from drag.h
class CurvePointT(ctypes.Structure):
    _fields_ = [
        ("a", ctypes.c_double),
        ("b", ctypes.c_double),
        ("c", ctypes.c_double),
    ]

# CurveT from drag.h
class CurveT(ctypes.Structure):
    _fields_ = [
        ("points", ctypes.POINTER(CurvePointT)),
        ("length", ctypes.c_size_t),
    ]

# MachListT from drag.h
class MachListT(ctypes.Structure):
    _fields_ = [
        ("values", ctypes.POINTER(ctypes.c_double)),
        ("length", ctypes.c_size_t),
    ]

# WindT from wind.h
class WindT(ctypes.Structure):
    _fields_ = [
        ("velocity", ctypes.c_double),
        ("directionFrom", ctypes.c_double),
        ("untilDistance", ctypes.c_double),
        ("MAX_DISTANCE_FEET", ctypes.c_double),
    ]

# WindsT from wind.h
class WindsT(ctypes.Structure):
    _fields_ = [
        ("winds", ctypes.POINTER(WindT)),
        ("length", ctypes.c_size_t),
    ]

# WindSockT from wind.h
class WindSockT(ctypes.Structure):
    _fields_ = [
        ("winds", ctypes.POINTER(WindsT)), # Note: This might be WindsT * or just WindsT, check your .h
        ("current", ctypes.c_int),
        ("nextRange", ctypes.c_double),
        ("lastVectorCache", V3dT),
    ]

# TrajectoryDataT (assuming from tData.h)
class TrajectoryDataT(ctypes.Structure):
    _fields_ = [
        ("time", ctypes.c_double),
        ("rangeVector", V3dT),
        ("velocityVector", V3dT),
        ("velocity", ctypes.c_double),
        ("mach", ctypes.c_double),
        ("spinDrift", ctypes.c_double),
        ("lookAngle", ctypes.c_double),
        ("densityFactor", ctypes.c_double),
        ("drag", ctypes.c_double),
        ("weight", ctypes.c_double),
        ("flag", ctypes.c_int), # Assuming int for enum
    ]

# TrajectoryTableT (assuming from tData.h)
class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("table", ctypes.POINTER(TrajectoryDataT)),
        ("length", ctypes.c_size_t),
        # ("capacity", ctypes.c_size_t), # Assuming this field exists
    ]

# TrajectoryDataFilterT (assuming from tDataFilter.h or bc.h)
class TrajectoryDataFilterT(ctypes.Structure):
    _fields_ = [] # Define members if it has any, otherwise it's just a placeholder

# ShotDataT from bc.h
class ShotDataT(ctypes.Structure):
    _fields_ = [
        ("bc", ctypes.c_double),
        ("dragTable", ctypes.POINTER(DragTableT)),
        ("lookAngle", ctypes.c_double),
        ("twist", ctypes.c_double),
        ("length", ctypes.c_double),
        ("diameter", ctypes.c_double),
        ("weight", ctypes.c_double),
        ("barrelElevation", ctypes.c_double),
        ("barrelAzimuth", ctypes.c_double),
        ("sightHeight", ctypes.c_double),
        ("cantCosine", ctypes.c_double),
        ("cantSine", ctypes.c_double),
        ("alt0", ctypes.c_double),
        ("calcStep", ctypes.c_double),
        ("muzzleVelocity", ctypes.c_double),
        ("stabilityCoefficient", ctypes.c_double),
        ("atmo", ctypes.POINTER(AtmosphereT)),
        ("wind", ctypes.POINTER(WindT)), # Assuming WindT *wind in ShotDataT
        # Add any other members from ShotDataT
    ]

# TrajectoryPropsT from bc.h
class TrajectoryPropsT(ctypes.Structure):
    _fields_ = [
        ("shotData", ctypes.POINTER(ShotDataT)),
        ("curve", CurveT),
        ("machList", MachListT),
        ("dataFilter", TrajectoryDataFilterT),
        ("windSock", WindSockT),
    ]

# EngineT from bc.h - The main structure
class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.POINTER(ConfigT)),
        ("gravityVector", V3dT),
        ("tProps", TrajectoryPropsT),
    ]

# --- 3. Define C Enumerations ---
class CalculationStatus(ctypes.c_int):
    SUCCESS = 0
    ERROR_NULL_ENGINE = -1
    ERROR_NULL_SHOTDATA = -2
    ERROR_NULL_ZEROANGLE = -3
    ERROR_INVALID_SHOTDATA = -4
    ERROR_MALLOC_FAILED = -5
    ERROR_REALLOC_FAILED = -6
    ERROR_INTEGRATE_FAILED = -5 # Appears twice, assuming one for trajectory, one for integrate
    ERROR_NULL_ZEROANGLE_OUT = -6 # Appears twice
    MIN_VELOCITY_REACHED = 1
    MAX_DROP_REACHED = 2
    MIN_ALTITUDE_REACHED = 3
    MAX_ITERATIONS_REACHED = 4

class TrajFlag(ctypes.c_int):
    TRAJ_NONE = 0
    TRAJ_ZERO_UP = 1
    TRAJ_ZERO_DOWN = 2
    TRAJ_ZERO = TRAJ_ZERO_UP | TRAJ_ZERO_DOWN
    TRAJ_MACH = 4
    TRAJ_RANGE = 8
    TRAJ_APEX = 16
    TRAJ_ALL = TRAJ_RANGE | TRAJ_ZERO_UP | TRAJ_ZERO_DOWN | TRAJ_MACH | TRAJ_APEX

# --- 4. Set argtypes and restype for C functions ---
if _engine_lib:
    # int initEngine(EngineT *engine, ConfigT *config)
    _engine_lib.initEngine.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ConfigT)]
    _engine_lib.initEngine.restype = ctypes.c_int

    # int initTrajectory(EngineT *engine, ShotDataT *initialShotData)
    _engine_lib.initTrajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT)]
    _engine_lib.initTrajectory.restype = ctypes.c_int

    # void freeTrajectory(EngineT *engine)
    _engine_lib.freeTrajectory.argtypes = [ctypes.POINTER(EngineT)]
    _engine_lib.freeTrajectory.restype = None

    # int zeroAngle(EngineT *engine, ShotDataT *shotData, double distance, double *zeroAngle)
    _engine_lib.zeroAngle.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT), ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    _engine_lib.zeroAngle.restype = ctypes.c_int

    # int trajectory(EngineT *engine, ShotDataT *ShotData, double maxRange, double distStep, bool extraData, double timeStep, TrajectoryTableT *trajectory)
    _engine_lib.trajectory.argtypes = [
        ctypes.POINTER(EngineT),
        ctypes.POINTER(ShotDataT),
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_bool, # bool in C is typically _Bool, ctypes.c_bool works for this
        ctypes.c_double,
        ctypes.POINTER(TrajectoryTableT)
    ]
    _engine_lib.trajectory.restype = ctypes.c_int

    # int integrate(EngineT *engine, double maximumRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryTableT * trajectory)
    _engine_lib.integrate.argtypes = [
        ctypes.POINTER(EngineT),
        ctypes.c_double,
        ctypes.c_double,
        TrajFlag, # Use the ctypes enum type
        ctypes.c_double,
        ctypes.POINTER(TrajectoryTableT)
    ]
    _engine_lib.integrate.restype = ctypes.c_int

    # void updateStabilityCoefficient(ShotDataT *shotData)
    _engine_lib.updateStabilityCoefficient.argtypes = [ctypes.POINTER(ShotDataT)]
    _engine_lib.updateStabilityCoefficient.restype = None

    # void updateDensityFactorAndMatchForAltitude(AtmosphereT *atmo, double altitude, double *densityRatio, double *mach)
    _engine_lib.updateDensityFactorAndMatchForAltitude.argtypes = [
        ctypes.POINTER(AtmosphereT), ctypes.c_double,
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)
    ]
    _engine_lib.updateDensityFactorAndMatchForAltitude.restype = None

    # MachListT tableToMach(DragTableT *table)
    _engine_lib.tableToMach.argtypes = [ctypes.POINTER(DragTableT)]
    _engine_lib.tableToMach.restype = MachListT # Returns the struct directly

    # CurveT calculateCurve(DragTableT *table)
    _engine_lib.calculateCurve.argtypes = [ctypes.POINTER(DragTableT)]
    _engine_lib.calculateCurve.restype = CurveT # Returns the struct directly

    # double calculateByCurveAndMachList(MachListT *machList, CurveT *curve, double mach)
    _engine_lib.calculateByCurveAndMachList.argtypes = [ctypes.POINTER(MachListT), ctypes.POINTER(CurveT), ctypes.c_double]
    _engine_lib.calculateByCurveAndMachList.restype = ctypes.c_double

    # void freeDragTable(DragTableT *table)
    _engine_lib.freeDragTable.argtypes = [ctypes.POINTER(DragTableT)]
    _engine_lib.freeDragTable.restype = None

    # void freeCurve(CurveT *curve)
    _engine_lib.freeCurve.argtypes = [ctypes.POINTER(CurveT)]
    _engine_lib.freeCurve.restype = None

    # void freeMachList(MachListT *machList)
    _engine_lib.freeMachList.argtypes = [ctypes.POINTER(MachListT)]
    _engine_lib.freeMachList.restype = None

    # int initWindSock(WindSockT *ws, WindsT *winds)
    _engine_lib.initWindSock.argtypes = [ctypes.POINTER(WindSockT), ctypes.POINTER(WindsT)]
    _engine_lib.initWindSock.restype = ctypes.c_int

    # V3dT windToVector(const WindT *w)
    _engine_lib.windToVector.argtypes = [ctypes.POINTER(WindT)]
    _engine_lib.windToVector.restype = V3dT

    # V3dT currentWindVector(WindSockT *ws)
    _engine_lib.currentWindVector.argtypes = [ctypes.POINTER(WindSockT)]
    _engine_lib.currentWindVector.restype = V3dT

    # void updateWindCache(WindSockT *ws)
    _engine_lib.updateWindCache.argtypes = [ctypes.POINTER(WindSockT)]
    _engine_lib.updateWindCache.restype = None

    # V3dT windVectorForRange(WindSockT *ws, double nextRange)
    _engine_lib.windVectorForRange.argtypes = [ctypes.POINTER(WindSockT), ctypes.c_double]
    _engine_lib.windVectorForRange.restype = V3dT

    # int addTrajectoryDataPoint(TrajectoryTableT *TrajectoryTableTable, TrajectoryDataT newData)
    _engine_lib.addTrajectoryDataPoint.argtypes = [ctypes.POINTER(TrajectoryTableT), TrajectoryDataT]
    _engine_lib.addTrajectoryDataPoint.restype = ctypes.c_int

    # TrajectoryDataT createTrajectoryData(...)
    _engine_lib.createTrajectoryData.argtypes = [
        ctypes.c_double, V3dT, V3dT, ctypes.c_double, ctypes.c_double,
        ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
        ctypes.c_double, ctypes.c_int
    ]
    _engine_lib.createTrajectoryData.restype = TrajectoryDataT

# --- 5. Python Wrapper Classes (from user's input, with minor adjustments) ---

class PyConfig:
    def __init__(self):
        self._c_config = ConfigT() # Allocate C struct

    @property
    def cMaxCalcStepSizeFeet(self): return self._c_config.cMaxCalcStepSizeFeet
    @cMaxCalcStepSizeFeet.setter
    def cMaxCalcStepSizeFeet(self, value): self._c_config.cMaxCalcStepSizeFeet = value

    @property
    def cZeroFindingAccuracy(self): return self._c_config.cZeroFindingAccuracy
    @cZeroFindingAccuracy.setter
    def cZeroFindingAccuracy(self, value): self._c_config.cZeroFindingAccuracy = value

    @property
    def cMinimumVelocity(self): return self._c_config.cMinimumVelocity
    @cMinimumVelocity.setter
    def cMinimumVelocity(self, value): self._c_config.cMinimumVelocity = value

    @property
    def cMaximumDrop(self): return self._c_config.cMaximumDrop
    @cMaximumDrop.setter
    def cMaximumDrop(self, value): self._c_config.cMaximumDrop = value

    @property
    def cMaxIterations(self): return self._c_config.cMaxIterations
    @cMaxIterations.setter
    def cMaxIterations(self, value): self._c_config.cMaxIterations = value

    @property
    def cGravityConstant(self): return self._c_config.cGravityConstant
    @cGravityConstant.setter
    def cGravityConstant(self, value): self._c_config.cGravityConstant = value

    @property
    def cMinimumAltitude(self): return self._c_config.cMinimumAltitude
    @cMinimumAltitude.setter
    def cMinimumAltitude(self, value): self._c_config.cMinimumAltitude = value

class PyAtmosphere:
    def __init__(self):
        self._c_atmo = AtmosphereT()

    @property
    def t0(self): return self._c_atmo.t0
    @t0.setter
    def t0(self, value): self._c_atmo.t0 = value

    @property
    def p0(self): return self._c_atmo.p0
    @p0.setter
    def p0(self, value): self._c_atmo.p0 = value

    @property
    def a0(self): return self._c_atmo.a0
    @a0.setter
    def a0(self, value): self._c_atmo.a0 = value

    @property
    def mach(self): return self._c_atmo.mach
    @mach.setter
    def mach(self, value): self._c_atmo.mach = value

    @property
    def densityFactor(self): return self._c_atmo.densityFactor
    @densityFactor.setter
    def densityFactor(self, value): self._c_atmo.densityFactor = value

    @property
    def cLowestTempC(self): return self._c_atmo.cLowestTempC
    @cLowestTempC.setter
    def cLowestTempC(self, value): self._c_atmo.cLowestTempC = value

    def update_density_factor_and_match(self, altitude: float):
        density_ratio_out = ctypes.c_double()
        mach_out = ctypes.c_double()
        if _engine_lib:
            _engine_lib.updateDensityFactorAndMatchForAltitude(ctypes.byref(self._c_atmo), altitude,
                                                               ctypes.byref(density_ratio_out), ctypes.byref(mach_out))
            self._c_atmo.densityFactor = density_ratio_out.value
            self._c_atmo.mach = mach_out.value
        return density_ratio_out.value, mach_out.value

class PyDragTable:
    def __init__(self):
        self._c_drag_table = DragTableT()
        self._points_buffer = None # To keep ctypes array alive

    def set_data(self, points: List[Tuple[float, float]]):
        # points should be a list of tuples (CD, Mach)
        num_points = len(points)
        # Create a ctypes array of DragTablePointT
        self._points_buffer = (DragTablePointT * num_points)()
        for i, (cd, mach) in enumerate(points):
            self._points_buffer[i].CD = cd
            self._points_buffer[i].Mach = mach
        self._c_drag_table.table = ctypes.cast(self._points_buffer, ctypes.POINTER(DragTablePointT))
        self._c_drag_table.length = num_points

    def __del__(self):
        pass # Leaving empty, assuming set_data manages buffer lifespan

class PyShotData:
    def __init__(self):
        self._c_shot_data = ShotDataT()
        self._atmo_obj = None # Keep reference to Python objects
        self._drag_table_obj = None
        self._wind_obj = None # Keep reference to Python objects

    @property
    def bc(self): return self._c_shot_data.bc
    @bc.setter
    def bc(self, value): self._c_shot_data.bc = value

    @property
    def muzzleVelocity(self): return self._c_shot_data.muzzleVelocity
    @muzzleVelocity.setter
    def muzzleVelocity(self, value): self._c_shot_data.muzzleVelocity = value

    @property
    def twist(self): return self._c_shot_data.twist
    @twist.setter
    def twist(self, value): self._c_shot_data.twist = value

    @property
    def length(self): return self._c_shot_data.length
    @length.setter
    def length(self, value): self._c_shot_data.length = value

    @property
    def diameter(self): return self._c_shot_data.diameter
    @diameter.setter
    def diameter(self, value): self._c_shot_data.diameter = value

    @property
    def weight(self): return self._c_shot_data.weight
    @weight.setter
    def weight(self, value): self._c_shot_data.weight = value

    @property
    def barrelElevation(self): return self._c_shot_data.barrelElevation
    @barrelElevation.setter
    def barrelElevation(self, value): self._c_shot_data.barrelElevation = value

    @property
    def barrelAzimuth(self): return self._c_shot_data.barrelAzimuth
    @barrelAzimuth.setter
    def barrelAzimuth(self, value): self._c_shot_data.barrelAzimuth = value

    @property
    def sightHeight(self): return self._c_shot_data.sightHeight
    @sightHeight.setter
    def sightHeight(self, value): self._c_shot_data.sightHeight = value

    @property
    def cantCosine(self): return self._c_shot_data.cantCosine
    @cantCosine.setter
    def cantCosine(self, value): self._c_shot_data.cantCosine = value

    @property
    def cantSine(self): return self._c_shot_data.cantSine
    @cantSine.setter
    def cantSine(self, value): self._c_shot_data.cantSine = value

    @property
    def alt0(self): return self._c_shot_data.alt0
    @alt0.setter
    def alt0(self, value): self._c_shot_data.alt0 = value

    @property
    def calcStep(self): return self._c_shot_data.calcStep
    @calcStep.setter
    def calcStep(self, value): self._c_shot_data.calcStep = value

    @property
    def stabilityCoefficient(self): return self._c_shot_data.stabilityCoefficient
    @stabilityCoefficient.setter
    def stabilityCoefficient(self, value): self._c_shot_data.stabilityCoefficient = value

    def set_atmosphere(self, atmo_obj: PyAtmosphere):
        self._atmo_obj = atmo_obj # Keep Python object alive
        self._c_shot_data.atmo = ctypes.pointer(atmo_obj._c_atmo)

    def set_drag_table(self, drag_table_obj: PyDragTable):
        self._drag_table_obj = drag_table_obj # Keep Python object alive
        self._c_shot_data.dragTable = ctypes.pointer(drag_table_obj._c_drag_table)

    def set_wind(self, wind_obj: 'PyWind'): # Forward reference for PyWind
        self._wind_obj = wind_obj
        self._c_shot_data.wind = ctypes.pointer(wind_obj._c_wind)

    def update_stability_coefficient(self):
        if _engine_lib:
            _engine_lib.updateStabilityCoefficient(ctypes.byref(self._c_shot_data))

class PyWind:
    def __init__(self, velocity: float, direction_from: float, until_distance: float):
        self._c_wind = WindT()
        self._c_wind.velocity = velocity
        self._c_wind.directionFrom = direction_from
        self._c_wind.untilDistance = until_distance
        # MAX_DISTANCE_FEET is extern const, set in C, not directly settable here usually.
        # Assuming C_MAX_WIND_DISTANCE_FEET is available globally if needed, or initialized in C.

class PyTrajectoryTable:
    def __init__(self):
        self._c_table = TrajectoryTableT()
        self._c_table.table = None
        self._c_table.length = 0
        # self._c_table.capacity = 0

    def get_data(self) -> list:
        data = []
        if not self._c_table.table:
            return data
        for i in range(self._c_table.length):
            td = self._c_table.table[i]
            data.append(TrajectoryData(
                time=td.time,
                range_vector=Vector(td.rangeVector.x, td.rangeVector.y, td.rangeVector.z),
                velocity_vector=Vector(td.velocityVector.x, td.velocityVector.y, td.velocityVector.z),
                velocity=td.velocity,
                mach=td.mach,
                spin_drift=td.spinDrift,
                look_angle=td.lookAngle,
                density_factor=td.densityFactor,
                drag=td.drag,
                weight=td.weight,
                flag=TrajFlag(td.flag)
            ))
        return data

    def get_length(self) -> int:
        return self._c_table.length

    def __del__(self):
        pass # Assuming freeTrajectory or integrate handles freeing _c_table.table


class EngineWrapper:
    def __init__(self):
        if not _engine_lib:
            raise RuntimeError("C shared library not loaded. Cannot create EngineWrapper.")
        self._c_engine = EngineT()
        self._config_ref = None  # Keep reference to Python Config object
        self._shot_data_ref = None  # Keep reference to PyShotData for initTrajectory
        self._atmo_ref = None  # NEW: To explicitly hold reference to the underlying ctypes.AtmosphereT object

    def init_engine(self, config_obj: PyConfig) -> int:
        self._config_ref = config_obj
        if _engine_lib:
            return _engine_lib.initEngine(ctypes.byref(self._c_engine), ctypes.byref(config_obj._c_config))
        return -1  # Indicate failure if lib not loaded

    def init_trajectory(self, initial_shot_data_obj: PyShotData) -> int:
        self._shot_data_ref = initial_shot_data_obj  # Keep reference to the Python PyShotData object

        if _engine_lib:
            # Crucially, if ShotDataT.atmo is a pointer, its target must be kept alive.
            # We assume initial_shot_data_obj._c_shot_data.atmo is a ctypes.POINTER(AtmosphereT)
            # and that it points to a valid AtmosphereT instance.
            if initial_shot_data_obj._c_shot_data.atmo:
                # Dereference the pointer to get the actual AtmosphereT instance
                # and store a strong reference to it in the wrapper.
                self._atmo_ref = initial_shot_data_obj._c_shot_data.atmo.contents
            else:
                self._atmo_ref = None # If no atmosphere data is set

            return _engine_lib.initTrajectory(ctypes.byref(self._c_engine), ctypes.byref(initial_shot_data_obj._c_shot_data))
        return -1

    def free_trajectory(self):
        if _engine_lib:
            _engine_lib.freeTrajectory(ctypes.byref(self._c_engine))
        self._shot_data_ref = None  # Clear reference to Python ShotData wrapper
        self._atmo_ref = None      # NEW: Clear reference to ctypes.AtmosphereT object

    def zero_angle(self, shot_data_obj: PyShotData, distance: float) -> tuple:
        c_zero_angle_out = ctypes.c_double()
        if _engine_lib:
            status = _engine_lib.zeroAngle(ctypes.byref(self._c_engine), ctypes.byref(shot_data_obj._c_shot_data),
                                            distance, ctypes.byref(c_zero_angle_out))
            return status, c_zero_angle_out.value
        return -1, 0.0

    def trajectory(self, shot_data_obj: PyShotData, max_range: float, dist_step: float,
                    extra_data: bool, time_step: float) -> tuple:
        py_traj_table = PyTrajectoryTable()
        if _engine_lib:
            status = _engine_lib.trajectory(ctypes.byref(self._c_engine), ctypes.byref(shot_data_obj._c_shot_data),
                                            max_range, dist_step, extra_data, time_step,
                                            ctypes.byref(py_traj_table._c_table))
            return status, py_traj_table
        return -1, py_traj_table

    def integrate(self, maximum_range: float, record_step: float, filter_flags: int,
                    time_step: float) -> tuple:
        py_traj_table = PyTrajectoryTable()
        if _engine_lib:
            status = _engine_lib.integrate(ctypes.byref(self._c_engine), maximum_range, record_step,
                                            TrajFlag(filter_flags), time_step, ctypes.byref(py_traj_table._c_table))
            return status, py_traj_table
        return -1, py_traj_table

    def __del__(self):
        # Ensure freeTrajectory is called when EngineWrapper is garbage collected if it wasn't explicitly.
        # This is a best effort, as __del__ is not guaranteed to run.
        # Check if _c_engine has been initialized (i.e., config pointer is not NULL)
        if _engine_lib and hasattr(self, '_c_engine') and self._c_engine.config:
            self.free_trajectory()

# --- CTYPES INTERFACE END ---


# New CTypes Integration Engine
class CTypesIntegrationEngine(BaseIntegrationEngine):
    """
    Integration engine that uses the C shared library via ctypes for trajectory calculations.
    """
    def __init__(self, config: Optional[BaseEngineConfig] = None):
        super().__init__(config)
        self._c_engine_wrapper = EngineWrapper()
        
        # Initialize the C engine with the config
        c_config = PyConfig()
        c_config.cMaxCalcStepSizeFeet = self._config.cMaxCalcStepSizeFeet
        c_config.cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        c_config.cMinimumVelocity = self._config.cMinimumVelocity
        c_config.cMaximumDrop = self._config.cMaximumDrop
        c_config.cMaxIterations = self._config.cMaxIterations
        c_config.cGravityConstant = self._config.cGravityConstant
        c_config.cMinimumAltitude = self._config.cMinimumAltitude
        
        status = self._c_engine_wrapper.init_engine(c_config)
        if status != CalculationStatus.SUCCESS:
            logger.error(f"Failed to initialize C engine with status: {status}")
            raise RuntimeError(f"Failed to initialize C engine with status: {status}")
        
        self._c_config_wrapper = c_config # Keep reference to prevent garbage collection

    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
        
        # Convert Python Shot object to C ShotDataT structure
        c_shot_data = PyShotData()
        c_shot_data.bc = shot_info.bc
        c_shot_data.lookAngle = shot_info.look_angle
        c_shot_data.twist = shot_info.twist
        c_shot_data.length = shot_info.length
        c_shot_data.diameter = shot_info.diameter
        c_shot_data.weight = shot_info.weight
        c_shot_data.barrelElevation = shot_info.barrel_elevation
        c_shot_data.barrelAzimuth = shot_info.barrel_azimuth
        c_shot_data.sightHeight = shot_info.sight_height
        c_shot_data.cantCosine = shot_info.cant_cosine
        c_shot_data.cantSine = shot_info.cant_sine
        c_shot_data.alt0 = shot_info.alt0
        c_shot_data.calcStep = shot_info.calc_step
        c_shot_data.muzzleVelocity = shot_info.muzzle_velocity

        # Convert Atmosphere
        if shot_info.atmo:
            c_atmo = PyAtmosphere()
            c_atmo.t0 = shot_info.atmo.temperature
            c_atmo.p0 = shot_info.atmo.pressure
            c_atmo.a0 = shot_info.atmo.altitude # Assuming a0 is initial altitude
            # Mach and densityFactor are updated by updateDensityFactorAndMatchForAltitude in C
            c_shot_data.set_atmosphere(c_atmo)
            c_atmo.update_density_factor_and_match(shot_info.alt0) # Update based on initial altitude

        # Convert Drag Table
        if shot_info.drag_table:
            c_drag_table = PyDragTable()
            drag_points = [(dp.CD, dp.Mach) for dp in shot_info.drag_table]
            c_drag_table.set_data(drag_points)
            c_shot_data.set_drag_table(c_drag_table)

        # Convert Wind (assuming only single wind layer for simplicity initially)
        if shot_info.wind:
            # The C ShotDataT has WindT *wind, implying a single wind or first layer.
            # If multiple winds need to be passed, WindsT and WindSockT would be involved.
            # For now, let's assume shot_info.wind maps directly to a single WindT
            # if the C function expects it this way for ShotDataT.
            # Based on the user's ctypes interface, ShotDataT has a POINTER(WindT) wind.
            c_wind = PyWind(shot_info.wind.velocity, shot_info.wind.direction_from, shot_info.wind.until_distance)
            c_shot_data.set_wind(c_wind)


        # Initialize C trajectory with converted shot data
        status = self._c_engine_wrapper.init_trajectory(c_shot_data)
        if status != CalculationStatus.SUCCESS:
            # Handle error, maybe raise an exception or return empty list
            logger.error(f"Failed to initialize C trajectory with status: {status}")
            self._c_engine_wrapper.free_trajectory()
            return []

        # Call the C integrate function
        status, py_traj_table = self._c_engine_wrapper.integrate(maximum_range, record_step, filter_flags, time_step)
        
        # Convert C TrajectoryTableT back to Python List[TrajectoryData]
        trajectory_data_list = []
        if status == CalculationStatus.SUCCESS:
            trajectory_data_list = py_traj_table.get_data()
        elif status == CalculationStatus.MIN_VELOCITY_REACHED:
            # The C function indicates a reason for stopping, treat as success with info
            trajectory_data_list = py_traj_table.get_data()
            logger.info("Trajectory calculation stopped: Minimum velocity reached.")
        elif status == CalculationStatus.MAX_DROP_REACHED:
            trajectory_data_list = py_traj_table.get_data()
            logger.info("Trajectory calculation stopped: Maximum drop reached.")
        elif status == CalculationStatus.MIN_ALTITUDE_REACHED:
            trajectory_data_list = py_traj_table.get_data()
            logger.info("Trajectory calculation stopped: Minimum altitude reached.")
        elif status == CalculationStatus.MAX_ITERATIONS_REACHED:
            trajectory_data_list = py_traj_table.get_data()
            logger.warning("Trajectory calculation stopped: Maximum iterations reached.")
        else:
            logger.error(f"C integration failed with status: {status}")

        # Free C resources associated with the trajectory calculation
        self._c_engine_wrapper.free_trajectory()
        
        return trajectory_data_list