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


class DragTablePointT(ctypes.Structure):
    _fields_ = [("Mach", ctypes.c_double),
                ("CD", ctypes.c_double)]

class DragTableT(ctypes.Structure):
    _fields_ = [("table", ctypes.POINTER(DragTablePointT)),
                ("length", ctypes.c_size_t)]

class ShotDataT(ctypes.Structure):
    _fields_ = [
        ("bc", ctypes.c_double),
        ("dragTable", ctypes.POINTER(DragTableT)),  # замість c_void_p
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

    # Заповнюємо gravityVector
    engine.gravityVector.x = 0.0
    engine.gravityVector.y = 0.0
    engine.gravityVector.z = -9.81

    # Створюємо drag table
    drag_points_array = (DragTablePointT * 3)(
        DragTablePointT(0.0, 0.5),
        DragTablePointT(0.5, 0.4),
        DragTablePointT(0.8, 0.3),
    )
    drag_table = DragTableT()
    drag_table.table = drag_points_array
    drag_table.length = 3

    # Прив’язуємо drag table до shot
    shot.dragTable = ctypes.pointer(drag_table)

    # Інші поля shot (мінімально)
    shot.bc = 0.3
    shot.muzzleVelocity = 2600.0
    shot.sightHeight = 1.5
    shot.twist = 1.0
    shot.length = 2.0
    shot.diameter = 0.308
    shot.weight = 150.0
    shot.alt0 = 0.0
    shot.calcStep = 0.01

    # Вказуємо null для atmo і winds для простоти, якщо це прийнятно
    shot.atmo = None
    shot.winds = None

    ret = lib.trajectory(ctypes.byref(engine), ctypes.byref(shot),
                         1000.0, 10.0, 0, 0.01, ctypes.byref(table))
    print("Return code:", ret)

test_call()