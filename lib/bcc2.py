import ctypes
import os

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
    print("Please ensure your C code is compiled into a shared library (e.g., libengine.so or engine.dll)")
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
        ("winds", ctypes.POINTER(WindsT)), # Pointer to WindsT
        ("current", ctypes.c_int),
        ("nextRange", ctypes.c_double),
        ("lastVectorCache", V3dT),
    ]

# TrajectoryDataT from tData.h
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
        ("flag", ctypes.c_int),
    ]

# TrajectoryTableT from tData.h
class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(TrajectoryDataT)),
        ("length", ctypes.c_size_t),
        ("capacity", ctypes.c_size_t),
    ]

    def get_data(self):
        # Convert C array to a Python list of dictionaries for easier access
        return [{field[0]: getattr(self.data[i], field[0]) for field in TrajectoryDataT._fields_}
                for i in range(self.length)]

    def get_length(self):
        return self.length

# ShotDataT from bc.h - MODIFIED TO INCLUDE _atmo_ref
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
        # Add a strong reference to the Python Atmo object
        # This prevents the Python Atmo object (and its underlying C struct)
        # from being garbage collected while ShotDataT is in use.
        ("_atmo_ref", ctypes.py_object),
        ("_wind_ref", ctypes.py_object), # Strong reference for wind
        ("_drag_table_ref", ctypes.py_object), # Strong reference for dragTable
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store a strong reference to the Python Atmo object
        # The 'atmo' field is a pointer to the C struct, but we need
        # to hold onto the Python object that manages that C struct's lifetime.
        if 'atmo' in kwargs and kwargs['atmo'] is not None:
            self._atmo_ref = kwargs['atmo']
            self.atmo = ctypes.pointer(kwargs['atmo']._as_c_type())
        else:
            self._atmo_ref = None
            self.atmo = None

        if 'wind' in kwargs and kwargs['wind'] is not None:
            self._wind_ref = kwargs['wind']
            self.wind = ctypes.pointer(kwargs['wind']._as_c_type())
        else:
            self._wind_ref = None
            self.wind = None

        if 'dragTable' in kwargs and kwargs['dragTable'] is not None:
            self._drag_table_ref = kwargs['dragTable']
            self.dragTable = ctypes.pointer(kwargs['dragTable']._as_c_type())
        else:
            self._drag_table_ref = None
            self.dragTable = None


# CalculationStatus enum from bc.h
class CalculationStatus(ctypes.c_int):
    SUCCESS = 0
    ERROR_NULL_ENGINE = -1
    ERROR_NULL_SHOTDATA = -2
    ERROR_NULL_ZEROANGLE = -3
    ERROR_INVALID_SHOTDATA = -4
    ERROR_MALLOC_FAILED = -5
    ERROR_REALLOC_FAILED = -6
    ERROR_INTEGRATE_FAILED = -5 # This seems like a duplicate value in original C enum
    ERROR_NULL_ZEROANGLE_OUT = -6 # This seems like a duplicate value in original C enum
    MIN_VELOCITY_REACHED = 1
    MAX_DROP_REACHED = 2
    MIN_ALTITUDE_REACHED = 3
    MAX_ITERATIONS_REACHED = 4

# EngineT from bc.h
class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.POINTER(ConfigT)),
        ("gravityVector", V3dT),
        ("tProps", ctypes.c_void_p), # Placeholder, as TrajectoryPropsT is complex
    ]


# --- 3. Wrapper Class for C Functions ---
class EngineWrapper:
    def __init__(self):
        if _engine_lib is None:
            raise RuntimeError("C library failed to load, cannot initialize EngineWrapper.")
        self._lib = _engine_lib
        self._engine = EngineT() # Allocate the EngineT structure

        # Store a strong reference to the ConfigT object
        # This prevents the ConfigT object (and its underlying C struct)
        # from being garbage collected while EngineT is in use.
        self._config_ref = None
        self._shot_data_ref = None # To hold a strong reference to ShotDataT

        self._setup_function_prototypes()

    def _setup_function_prototypes(self):
        # initEngine
        self._lib.initEngine.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ConfigT)]
        self._lib.initEngine.restype = ctypes.c_int

        # initTrajectory
        self._lib.initTrajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT)]
        self._lib.initTrajectory.restype = ctypes.c_int

        # freeTrajectory
        self._lib.freeTrajectory.argtypes = [ctypes.POINTER(EngineT)]
        self._lib.freeTrajectory.restype = None

        # zeroAngle
        self._lib.zeroAngle.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT), ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
        self._lib.zeroAngle.restype = ctypes.c_int

        # trajectory
        self._lib.trajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT), ctypes.c_double, ctypes.c_double, ctypes.c_bool, ctypes.c_double, ctypes.POINTER(TrajectoryTableT)]
        self._lib.trajectory.restype = ctypes.c_int

        # integrate
        self._lib.integrate.argtypes = [ctypes.POINTER(EngineT), ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.POINTER(TrajectoryTableT)]
        self._lib.integrate.restype = ctypes.c_int

        # updateStabilityCoefficient
        self._lib.updateStabilityCoefficient.argtypes = [ctypes.POINTER(ShotDataT)]
        self._lib.updateStabilityCoefficient.restype = None

    def init_engine(self, config: ConfigT) -> int:
        self._config_ref = config # Keep a strong reference to the Python ConfigT object
        return self._lib.initEngine(ctypes.byref(self._engine), ctypes.byref(config))

    def init_trajectory(self, shot_data: ShotDataT) -> int:
        self._shot_data_ref = shot_data # Keep a strong reference to the ShotDataT object
        return self._lib.initTrajectory(ctypes.byref(self._engine), ctypes.byref(shot_data))

    def free_trajectory(self):
        # The C function frees internal allocations within the engine's tProps
        self._lib.freeTrajectory(ctypes.byref(self._engine))
        # After freeing C resources, clear the strong Python reference
        # This allows Python's GC to collect shot_data_ref when no longer needed elsewhere
        self._shot_data_ref = None

    def zero_angle(self, shot_data: ShotDataT, distance: float) -> tuple[int, float]:
        zero_angle_out = ctypes.c_double()
        status = self._lib.zeroAngle(ctypes.byref(self._engine), ctypes.byref(shot_data), distance, ctypes.byref(zero_angle_out))
        return status, zero_angle_out.value

    def trajectory(self, shot_data: ShotDataT, max_range: float, dist_step: float, extra_data: bool, time_step: float) -> tuple[int, TrajectoryTableT]:
        trajectory_table = TrajectoryTableT()
        status = self._lib.trajectory(ctypes.byref(self._engine), ctypes.byref(shot_data), max_range, dist_step, extra_data, time_step, ctypes.byref(trajectory_table))
        return status, trajectory_table

    def integrate(self, maximum_range: float, record_step: float, filter_flags: int, time_step: float) -> tuple[int, TrajectoryTableT]:
        # Assume initTrajectory has already been called with the relevant shot_data
        trajectory_table = TrajectoryTableT()
        status = self._lib.integrate(ctypes.byref(self._engine), maximum_range, record_step, filter_flags, time_step, ctypes.byref(trajectory_table))
        return status, trajectory_table

    def update_stability_coefficient(self, shot_data: ShotDataT):
        self._lib.updateStabilityCoefficient(ctypes.byref(shot_data))


# Example Usage (if needed for testing, typically this would be in a separate script)
if __name__ == "__main__":
    if _engine_lib is None:
        print("Library not loaded, exiting example.")
        exit(1)

    engine_wrapper = EngineWrapper()

    # 1. Create a ConfigT instance
    config = ConfigT(
        cMaxCalcStepSizeFeet=1.0,
        cZeroFindingAccuracy=0.000005,
        cMinimumVelocity=50.0,
        cMaximumDrop=-15000.0,
        cMaxIterations=60,
        cGravityConstant=32.174, # ft/s^2
        cMinimumAltitude=-1000.0
    )

    # 2. Initialize the Engine
    status = engine_wrapper.init_engine(config)
    if status != 0:
        print(f"Error initializing engine: {status}")
        exit(1)
    else:
        print("Engine initialized successfully.")

    # 3. Create a DragTableT instance (example)
    # In a real scenario, this would come from your drag model
    drag_points = [
        DragTablePointT(CD=0.2, Mach=0.5),
        DragTablePointT(CD=0.3, Mach=1.0),
        DragTablePointT(CD=0.4, Mach=1.2),
    ]
    # Allocate C array for drag points
    DragTablePointArray = DragTablePointT * len(drag_points)
    c_drag_array = DragTablePointArray(*drag_points)

    drag_table = DragTableT(table=c_drag_array, length=len(drag_points))

    # 4. Create an AtmosphereT instance (example)
    atmo = AtmosphereT(
        t0=288.15, # K (15 C)
        a0=340.29, # m/s (speed of sound at sea level)
        p0=1013.25, # hPa
        mach=0.0, # Placeholder, updated by C code
        densityFactor=1.225, # kg/m^3 at sea level
        cLowestTempC=-90.0 # Example value
    )

    # 5. Create a WindsT instance (example)
    wind_points = [
        WindT(velocity=10.0, directionFrom=270.0, untilDistance=500.0, MAX_DISTANCE_FEET=999999.0),
        WindT(velocity=5.0, directionFrom=90.0, untilDistance=1000.0, MAX_DISTANCE_FEET=999999.0),
    ]
    WindArray = WindT * len(wind_points)
    c_wind_array = WindArray(*wind_points)
    winds = WindsT(winds=c_wind_array, length=len(wind_points))


    # 6. Create a ShotDataT instance
    shot_data = ShotDataT(
        bc=0.3,
        dragTable=drag_table, # Pass the Python object, ShotDataT's __init__ will handle the pointer and ref
        lookAngle=0.0,
        twist=1.0,
        length=2.0,
        diameter=0.308,
        weight=0.01089, # kg
        barrelElevation=0.0,
        barrelAzimuth=0.0,
        sightHeight=1.5/12.0, # 1.5 inches to feet
        cantCosine=1.0,
        cantSine=0.0,
        alt0=0.0,
        calcStep=1.0,
        muzzleVelocity=2800.0, # fps
        atmo=atmo, # Pass the Python Atmo object
        wind=winds # Pass the Python WindsT object
    )

    # Update stability coefficient
    engine_wrapper.update_stability_coefficient(shot_data)
    print(f"Stability Coefficient: {shot_data.stabilityCoefficient}")

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
            # Access trajectory data
            if traj_table.get_length() > 0:
                first_point = traj_table.get_data()[0]
                print(f"First point time: {first_point['time']}, Range: {first_point['rangeVector']}")
        else:
            print(f"Trajectory calculation failed with status: {status}")

    # Free C resources explicitly if your C library has such functions,
    # or rely on Python's garbage collection for `ctypes` objects that don't
    # explicitly manage C-allocated memory. For `EngineT`, `freeTrajectory` is
    # called by the wrapper to clean up its internal `tProps`.
    engine_wrapper.free_trajectory()