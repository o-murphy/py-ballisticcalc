import ctypes

# Підтипи для вкладених структур

class V3dT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double),
                ("y", ctypes.c_double),
                ("z", ctypes.c_double)]

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
        ("flag", ctypes.c_int)
    ]

class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("ranges", ctypes.POINTER(TrajectoryDataT)),
        ("length", ctypes.c_size_t),
        ("capacity", ctypes.c_size_t)
    ]

class ShotDataT(ctypes.Structure):
    _fields_ = [
        ("bc", ctypes.c_double),
        ("dragTable", ctypes.c_void_p),  # DragTableT* - складно описати, тому як void*
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
        ("atmo", ctypes.c_void_p),  # AtmosphereT*
        ("winds", ctypes.c_void_p), # WindsT*
    ]

class TrajectoryPropsT(ctypes.Structure):
    _fields_ = [
        ("shotData", ctypes.POINTER(ShotDataT)),
        ("curve", ctypes.c_void_p),       # CurveT* - без детального опису void*
        ("machList", ctypes.c_void_p),    # MachListT*
        ("dataFilter", ctypes.c_void_p),  # TrajectoryDataFilterT*
        ("windSock", ctypes.c_void_p)     # WindSockT*
    ]

class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.c_void_p),  # ConfigT*
        ("gravityVector", V3dT),
        ("tProps", TrajectoryPropsT)
    ]



lib = ctypes.CDLL("./bcc.so")

lib.trajectory.argtypes = [
    ctypes.POINTER(EngineT),
    ctypes.POINTER(ShotDataT),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_int,
    ctypes.c_double,
    ctypes.POINTER(TrajectoryTableT)
]
lib.trajectory.restype = ctypes.c_int

lib.integrate.argtypes = [
    ctypes.POINTER(EngineT),
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_int,
    ctypes.c_double,
    ctypes.POINTER(TrajectoryTableT)
]
lib.integrate.restype = ctypes.c_int


def test_call():
    engine = EngineT()
    shot = ShotDataT()
    table = TrajectoryTableT()

    # Ініціалізація полів, якщо треба
    # Приміром заповнимо gravityVector
    engine.gravityVector.x = 0.0
    engine.gravityVector.y = 0.0
    engine.gravityVector.z = -9.81

    # Виклик функції
    ret = lib.trajectory(ctypes.byref(engine), ctypes.byref(shot),
                         1000.0, 10.0, 0, 0.01, ctypes.byref(table))
    print("Return code:", ret)