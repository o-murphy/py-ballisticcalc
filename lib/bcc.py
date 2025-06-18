import ctypes
import os

BoolT = ctypes.c_int  # aka ctypes.c_bool

# --- 1. Load the shared library ---
try:
    if os.name == 'posix':
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.so')
    elif os.name == 'nt':
        _lib_path = os.path.join(os.path.dirname(__file__), 'bcc.dll')
    else:
        raise OSError("Unsupported operating system")

    _engine_lib = ctypes.CDLL(_lib_path)
    print("Engine library loaded successfully.")
except OSError as e:
    print(f"Error loading shared library: {e}")
    _engine_lib = None

# --- 2. Define ctypes structures ---

class V3dT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("z", ctypes.c_double)]

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

class AtmosphereT(ctypes.Structure):
    _fields_ = [
        ("t0", ctypes.c_double), ("a0", ctypes.c_double), ("p0", ctypes.c_double),
        ("mach", ctypes.c_double), ("densityFactor", ctypes.c_double), ("cLowestTempC", ctypes.c_double),
    ]

class DragTablePointT(ctypes.Structure):
    _fields_ = [("Mach", ctypes.c_double), ("CD", ctypes.c_double)]

class DragTableT(ctypes.Structure):
    _fields_ = [
        ("table", ctypes.POINTER(DragTablePointT)),
        ("length", ctypes.c_size_t),
    ]

class WindT(ctypes.Structure):
    _fields_ = [
        ("velocity", ctypes.c_double),
        ("directionFrom", ctypes.c_double),
        ("untilDistance", ctypes.c_double),
        ("MAX_DISTANCE_FEET", ctypes.c_double),
    ]

class WindsT(ctypes.Structure):
    _fields_ = [
        ("winds", ctypes.POINTER(WindT)),
        ("length", ctypes.c_size_t),
    ]

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
        ("winds", ctypes.POINTER(WindsT)),  # Fixed: renamed from 'wind'
        ("MAX_DISTANCE_FEET", ctypes.c_double),
    ]

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

class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("ranges", ctypes.POINTER(TrajectoryDataT)),
        ("length", ctypes.c_size_t),
        ("capacity", ctypes.c_size_t),
    ]

    def get_data(self):
        if not self.ranges or self.length == 0:
            return []
        return [self.ranges[i] for i in range(self.length)]

    def get_length(self):
        return self.length

# TrajectoryPropsT is internal and opaque from Python's side
class TrajectoryPropsT(ctypes.Structure):
    _fields_ = [("_opaque", ctypes.c_byte * 256)]  # Reserve space safely

class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.POINTER(ConfigT)),
        ("gravityVector", V3dT),
        ("tProps", TrajectoryPropsT),
    ]

# --- 3. Wrapper class ---

class TrajectoryTableWrapper:
    def __init__(self, table, lib):
        self._table = table
        self._lib = lib
        self._freed = False

    def get_data(self):
        if not self._table.ranges or self._table.length == 0:
            return []
        return [self._table.ranges[i] for i in range(self._table.length)]

    def get_length(self):
        return self._table.length

    def free(self):
        if not self._freed:
            self._lib.freeTrajectoryTable(ctypes.byref(self._table))
            self._freed = True

    def __del__(self):
        self.free()

class EngineWrapper:
    def __init__(self, lib):
        self.lib = lib
        if lib:
            lib.initEngine.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ConfigT)]
            lib.initEngine.restype = ctypes.c_int

            lib.initTrajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT)]
            lib.initTrajectory.restype = ctypes.c_int

            lib.updateStabilityCoefficient.argtypes = [ctypes.POINTER(ShotDataT)]
            lib.updateStabilityCoefficient.restype = None

            lib.trajectory.argtypes = [
                ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT),
                ctypes.c_double, ctypes.c_double, BoolT,
                ctypes.c_double, ctypes.POINTER(TrajectoryTableT),
            ]
            lib.trajectory.restype = ctypes.c_int

            lib.freeTrajectoryTable.argtypes = [ctypes.POINTER(TrajectoryTableT)]
            lib.freeTrajectoryTable.restype = None

    def init_engine(self, config):
        engine = EngineT()
        if self.lib.initEngine(ctypes.byref(engine), ctypes.byref(config)) != 0:
            raise RuntimeError("initEngine failed")
        return engine

    def init_trajectory(self, engine, shot_data):
        return self.lib.initTrajectory(ctypes.byref(engine), ctypes.byref(shot_data))

    def update_stability(self, shot_data):
        self.lib.updateStabilityCoefficient(ctypes.byref(shot_data))

    def run_trajectory(self, engine, shot_data, max_range, step, extra_data, dt):
        traj = TrajectoryTableT()

        # Утримати в _refs, щоб уникнути збору GC
        if not hasattr(self, "_refs"):
            self._refs = {}

        self._refs["last_traj"] = traj  # тримаємо об'єкт живим

        status = self.lib.trajectory(
            ctypes.byref(engine),
            ctypes.byref(shot_data),
            max_range,
            step,
            extra_data,
            dt,
            ctypes.byref(traj)
        )

        return status, TrajectoryTableWrapper(traj, self.lib)

    def free_table(self, table):
        self.lib.freeTrajectoryTable(ctypes.byref(table))

# --- 4. Example test run (only run if library loaded) ---

if _engine_lib:
    ew = EngineWrapper(_engine_lib)

    # Store alive references inside the wrapper to prevent GC
    ew._refs = {}

    # Allocate arrays
    drag_points = (DragTablePointT * 6)(
        DragTablePointT(0.0, 0.5),
        DragTablePointT(0.5, 0.4),
        DragTablePointT(0.8, 0.3),
        DragTablePointT(1.0, 0.6),
        DragTablePointT(1.2, 0.45),
        DragTablePointT(2.0, 0.3),
    )
    wind_data = (WindT * 2)(
        WindT(10.0, 90.0 * 3.1415926535 / 180.0, 500.0, 999999.0),
        WindT(5.0, 0.0, 1000.0, 999999.0),
    )

    # Create parent structs
    drag_table = DragTableT(table=drag_points, length=6)
    winds = WindsT(winds=wind_data, length=2)

    atmo = AtmosphereT(293.15, 1116.4, 1013.25, 1.0, 1.0, -70.0)
    config = ConfigT(1.0, 0.001, 500.0, -100.0, 1000, 32.174, 0.0)

    shot = ShotDataT(
        bc=0.3,
        dragTable=ctypes.pointer(drag_table),
        lookAngle=0.0,
        twist=1.0,
        length=2.0,
        diameter=0.308,
        weight=175.0,
        barrelElevation=0.0,
        barrelAzimuth=0.0,
        sightHeight=1.5,
        cantCosine=1.0,
        cantSine=0.0,
        alt0=0.0,
        calcStep=0.01,
        muzzleVelocity=2600.0,
        stabilityCoefficient=0.0,
        atmo=ctypes.pointer(atmo),
        winds=ctypes.pointer(winds),
        MAX_DISTANCE_FEET=3000.0,
    )

    # ⛑️ Retain everything that must stay alive
    ew._refs["drag_points"] = drag_points
    ew._refs["wind_data"] = wind_data
    ew._refs["drag_table"] = drag_table
    ew._refs["winds"] = winds
    ew._refs["atmo"] = atmo
    ew._refs["shot"] = shot
    ew._refs["config"] = config

    engine = ew.init_engine(config)
    ew.update_stability(shot)
    print(f"Stability Coefficient: {shot.stabilityCoefficient}")

    assert ew.init_trajectory(engine, shot) == 0

    status, traj = ew.run_trajectory(engine, shot, max_range=3000.0, step=10.0, extra_data=True, dt=0.01)
    print(f"Trajectory status: {status}, points: {traj.get_length()}")

    def get_data(self):
        if not self._table.ranges or self._table.length == 0:
            return []
        return [self._table.ranges[i] for i in range(self._table.length)]

    ew.free_table(traj)