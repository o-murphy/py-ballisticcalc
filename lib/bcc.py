import ctypes
import os

# --- 1. Load the shared library ---
try:
    if os.name == 'posix':  # Linux or macOS
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.so')
    elif os.name == 'nt':  # Windows
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.dll')
    else:
        raise OSError("Unsupported operating system")

    _engine_lib = ctypes.CDLL(_lib_path)
    print("Engine initialized successfully.")
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

    def __init__(self, *args, **kwargs):
        table_list = kwargs.pop('table', None)
        super().__init__(*args, **kwargs)
        if table_list is not None:
            # Create a C array from the Python list
            c_drag_array = (DragTablePointT * len(table_list))(*table_list)
            self._table_ref = c_drag_array # Keep a strong reference to the C array
            self.table = ctypes.cast(c_drag_array, ctypes.POINTER(DragTablePointT))
            self.length = len(table_list)
        else:
            self._table_ref = None
            self.table = None
            self.length = 0

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

    def __init__(self, *args, **kwargs):
        winds_list = kwargs.pop('winds', None)
        super().__init__(*args, **kwargs)
        if winds_list is not None:
            c_winds_array = (WindT * len(winds_list))(*winds_list)
            self._winds_ref = c_winds_array # Strong reference
            self.winds = ctypes.cast(c_winds_array, ctypes.POINTER(WindT))
            self.length = len(winds_list)
        else:
            self._winds_ref = None
            self.winds = None
            self.length = 0

# WindSockT from wind.h
class WindSockT(ctypes.Structure):
    _fields_ = [
        ("winds", ctypes.POINTER(WindsT)), # Pointer to WindsT
        ("current", ctypes.c_int),
        ("nextRange", ctypes.c_double),
        ("lastVectorCache", V3dT), # V3dT struct directly embedded
    ]

# TrajectoryDataT from tData.h
class TrajectoryDataT(ctypes.Structure):
    _fields_ = [
        ("time", ctypes.c_double),
        ("distance", ctypes.c_double),
        ("velocity", ctypes.c_double),
        ("mach", ctypes.c_double),
        ("height", ctypes.c_double),
        ("targetDrop", ctypes.c_double),
        ("dropAdj", ctypes.c_double),
        ("windage", ctypes.c_double),
        ("windageAdj", ctypes.c_double),
        ("lookDistance", ctypes.c_double),
        ("angle", ctypes.c_double),
        ("densityFactor", ctypes.c_double),
        ("drag", ctypes.c_double),
        ("energy", ctypes.c_double),
        ("ogw", ctypes.c_double),
        ("flag", ctypes.c_int),
    ]

# TrajectoryTableT from tData.h
class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("ranges", ctypes.POINTER(TrajectoryDataT)), # Corrected to 'ranges'
        ("length", ctypes.c_size_t),
        # Removed capacity as it's not in user's tData.h. Add if needed:
        # ("capacity", ctypes.c_size_t),
    ]

    def get_data(self):
        """Returns the trajectory data as a list of dictionaries for easier Python access."""
        # This makes a copy of the data, so it's safe to free the C memory afterward.
        return [{field[0]: getattr(self.ranges[i], field[0]) for field in TrajectoryDataT._fields_}
                for i in range(self.length)]

    def get_length(self):
        return self.length

# TrajectoryDataFilterT from tDataFilter.h
class TrajectoryDataFilterT(ctypes.Structure):
    _fields_ = [
        ("filter", ctypes.c_int),
        ("currentFlag", ctypes.c_int),
        ("seenZero", ctypes.c_int),
        ("timeStep", ctypes.c_double),
        ("rangeStep", ctypes.c_double),
        ("timeOfLastRecord", ctypes.c_double),
        ("nextRecordDistance", ctypes.c_double),
        ("previousMach", ctypes.c_double),
        ("previousTime", ctypes.c_double),
        ("previousPosition", V3dT),
        ("previousVelocity", V3dT),
        ("previousVMach", ctypes.c_double),
        ("lookAngle", ctypes.c_double),
    ]

# TrajectoryPropsT from bc.h
class TrajectoryPropsT(ctypes.Structure):
    _fields_ = [
        ("shotData", ctypes.POINTER(
            ctypes.c_void_p)), # Use c_void_p as the actual ShotDataT is held by EngineWrapper
        ("curve", CurveT),
        ("machList", MachListT),
        ("dataFilter", TrajectoryDataFilterT),
        ("windSock", WindSockT),
    ]

# EngineT from bc.h
class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.POINTER(ConfigT)),
        ("gravityVector", V3dT),
        ("tProps", TrajectoryPropsT),
    ]

# ShotDataT from bc.h - MODIFIED TO INCLUDE _atmo_ref and _drag_table_ref
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
        ("wind", ctypes.POINTER(WindsT)),
    ]

    def __init__(self, *args, **kwargs):
        # Extract custom arguments before calling super().__init__
        atmo_arg = kwargs.pop('atmo', None)
        wind_arg = kwargs.pop('wind', None)
        drag_table_arg = kwargs.pop('dragTable', None)

        # Initialize the base ctypes.Structure with the remaining arguments
        super().__init__(*args, **kwargs)

        # Handle 'atmo' argument
        if atmo_arg is not None:
            self._atmo_ref = atmo_arg
            self.atmo = ctypes.pointer(atmo_arg)
        else:
            self._atmo_ref = None
            self.atmo = None

        # Handle 'wind' argument
        if wind_arg is not None:
            self._wind_ref = wind_arg
            self.wind = ctypes.pointer(wind_arg)
        else:
            self._wind_ref = None
            self.wind = None

        # Handle 'dragTable' argument
        if drag_table_arg is not None:
            self._drag_table_ref = drag_table_arg
            self.dragTable = ctypes.pointer(drag_table_arg)
        else:
            self._drag_table_ref = None
            self.dragTable = None

# CalculationStatus enum (Python equivalent)
class CalculationStatus:
    SUCCESS = 0
    ERROR_NULL_ENGINE = -1
    ERROR_NULL_SHOTDATA = -2
    ERROR_NULL_ZEROANGLE = -3
    ERROR_INVALID_SHOTDATA = -4
    ERROR_MALLOC_FAILED = -5
    ERROR_REALLOC_FAILED = -6
    ERROR_INTEGRATE_FAILED = -5 # Duplicate value, check C enum
    ERROR_NULL_ZEROANGLE_OUT = -6 # Duplicate value, check C enum
    MIN_VELOCITY_REACHED = 1
    MAX_DROP_REACHED = 2
    MIN_ALTITUDE_REACHED = 3
    MAX_ITERATIONS_REACHED = 4

class EngineWrapper:
    def __init__(self, config_obj):
        if not _engine_lib:
            raise RuntimeError("C library not loaded. Cannot initialize EngineWrapper.")

        self._c_engine = EngineT()
        self._config_ref = config_obj # Keep a strong reference to the Python config object
        status = _engine_lib.initEngine(ctypes.byref(self._c_engine), ctypes.byref(config_obj))
        if status != 0:
            raise RuntimeError(f"Failed to initialize C engine: {status}")


        # Register function signatures for _engine_lib functions
        _engine_lib.initEngine.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ConfigT)]
        _engine_lib.initEngine.restype = ctypes.c_int

        _engine_lib.initTrajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT)]
        _engine_lib.initTrajectory.restype = ctypes.c_int

        _engine_lib.trajectory.argtypes = [
            ctypes.POINTER(EngineT),
            ctypes.POINTER(ShotDataT),
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_bool,
            ctypes.c_double,
            ctypes.POINTER(TrajectoryTableT) # TrajectoryTableT is passed by pointer
        ]
        _engine_lib.trajectory.restype = ctypes.c_int # Returns status

        _engine_lib.freeTrajectory.argtypes = [ctypes.POINTER(EngineT)]
        _engine_lib.freeTrajectory.restype = None

        # NEW: Register freeTrajectoryTable
        _engine_lib.freeTrajectoryTable.argtypes = [ctypes.POINTER(TrajectoryTableT)]
        _engine_lib.freeTrajectoryTable.restype = None

        # Other functions (add as needed with correct argtypes/restype)
        _engine_lib.updateStabilityCoefficient.argtypes = [ctypes.POINTER(ShotDataT)]
        _engine_lib.updateStabilityCoefficient.restype = None

    def init_trajectory(self, shot_data_obj):
        if not _engine_lib: return -1 # Error status
        return _engine_lib.initTrajectory(ctypes.byref(self._c_engine), ctypes.byref(shot_data_obj))

    def trajectory(self, shot_data_obj, max_range, dist_step, extra_data, time_step):
        if not _engine_lib: return CalculationStatus.ERROR_NULL_ENGINE, TrajectoryTableT()

        # Create a new TrajectoryTableT object. C function will fill its 'ranges' pointer.
        traj_table_c = TrajectoryTableT()
        status = _engine_lib.trajectory(
            ctypes.byref(self._c_engine),
            ctypes.byref(shot_data_obj),
            max_range,
            dist_step,
            extra_data,
            time_step,
            ctypes.byref(traj_table_c) # Pass by reference to be filled by C
        )
        return status, traj_table_c

    # NEW: Method to free the trajectory table's C memory
    def free_trajectory_table_c_memory(self, traj_table_obj):
        """Frees the dynamically allocated C memory within a TrajectoryTableT object."""
        if not _engine_lib: return
        # Check if the 'ranges' pointer is not NULL before attempting to free
        if traj_table_obj.ranges:
            _engine_lib.freeTrajectoryTable(ctypes.byref(traj_table_obj))
            # After freeing, it's good practice to invalidate the Python object's pointer
            # so it doesn't accidentally try to access freed memory again.
            traj_table_obj.ranges = None
            traj_table_obj.length = 0 # Also reset length

    def __del__(self):
        if hasattr(self, '_c_engine') and _engine_lib:
            _engine_lib.freeTrajectory(ctypes.byref(self._c_engine))


# --- 3. Example Usage ---
if __name__ == "__main__":
    if not _engine_lib:
        print("Exiting due to C library loading error.")
        exit(1)

    # 1. Create a ConfigT instance
    config = ConfigT(
        cMaxCalcStepSizeFeet=1.0,
        cZeroFindingAccuracy=0.001,
        cMinimumVelocity=500.0,
        cMaximumDrop=100.0,
        cMaxIterations=1000,
        cGravityConstant=32.174, # ft/s^2
        cMinimumAltitude=0.0
    )

    # 2. Create an EngineWrapper
    engine_wrapper = EngineWrapper(config)

    # 3. Create an AtmosphereT instance
    atmo = AtmosphereT(
        t0=293.15, # 20 C in Kelvin
        a0=1116.4, # Speed of sound in ft/s at sea level standard
        p0=1013.25, # hPa (hectopascals)
        mach=1.0, # Will be updated by C code
        densityFactor=1.0, # Will be updated by C code
        cLowestTempC=-70.0
    )

    # 4. Create a DragTableT instance (example G1 drag table data)
    # The actual G1 table is much larger. This is a minimal example.
    drag_points = [
        DragTablePointT(Mach=0.0, CD=0.5),
        DragTablePointT(Mach=0.5, CD=0.4),
        DragTablePointT(Mach=0.8, CD=0.3),
        DragTablePointT(Mach=1.0, CD=0.6), # Transonic spike
        DragTablePointT(Mach=1.2, CD=0.45),
        DragTablePointT(Mach=2.0, CD=0.3)
    ]
    drag_table = DragTableT(table=drag_points)

    # 5. Create a WindsT instance (example winds data)
    winds_data = [
        WindT(velocity=10.0, directionFrom=90.0 * 3.14159 / 180.0, untilDistance=500.0, MAX_DISTANCE_FEET=999999.0),
        WindT(velocity=5.0, directionFrom=0.0, untilDistance=1000.0, MAX_DISTANCE_FEET=999999.0)
    ]
    winds = WindsT(winds=winds_data)

    # 6. Create ShotDataT instance
    shot_data = ShotDataT(
        bc=0.3,
        dragTable=drag_table, # Pass the Python object, ShotDataT will get its pointer
        lookAngle=0.0,
        twist=1.0,
        length=2.0, # inches
        diameter=0.308, # inches
        weight=175.0, # grains
        barrelElevation=0.0,
        barrelAzimuth=0.0,
        sightHeight=1.5, # inches
        cantCosine=1.0,
        cantSine=0.0,
        alt0=0.0,
        calcStep=0.01,
        muzzleVelocity=2600.0, # ft/s
        stabilityCoefficient=0.0, # Will be updated by C code
        atmo=atmo, # Pass the Python object
        wind=winds, # Pass the Python object
    )

    # 6.1 Update Stability Coefficient (example C function call)
    # CORRECTED LINE: Call directly on the global _engine_lib
    _engine_lib.updateStabilityCoefficient(ctypes.byref(shot_data))
    print(f"Updated stability coefficient: {shot_data.stabilityCoefficient}")

    # 7. Initialize the Trajectory
    status = engine_wrapper.init_trajectory(shot_data)
    if status != 0:
        print(f"Error initializing trajectory: {status}")
    else:
        print("Trajectory initialized successfully.")

        # 8. Call trajectory calculation
        max_range = 1000.0 # yards
        dist_step = 10.0 # yards
        extra_data = True
        time_step = 0.01 # seconds

        # Convert yards to feet if your C functions expect feet
        max_range_feet = max_range * 3.0
        dist_step_feet = dist_step * 3.0

        status, traj_table = engine_wrapper.trajectory(shot_data, max_range_feet, dist_step_feet, extra_data, time_step)

        if status == CalculationStatus.SUCCESS:
            print(f"Trajectory calculated successfully. Points: {traj_table.get_length()}")
            # Access trajectory data (get_data() makes a Python copy, so it's safe)
            if traj_table.get_length() > 0:
                first_point = traj_table.get_data()[0]
                print(f"First point time: {first_point['time']}, Range: {first_point['distance']}") # 'distance' is the range field in TrajectoryDataT
            
            # IMPORTANT: Free the C-allocated memory for the trajectory table's data
            # This must be called when you are done with the C data pointed to by traj_table.ranges
            engine_wrapper.free_trajectory_table_c_memory(traj_table)
            print("Trajectory table C memory freed successfully.")
        else:
            print(f"Trajectory calculation failed with status: {status}")

    print("Script finished.")