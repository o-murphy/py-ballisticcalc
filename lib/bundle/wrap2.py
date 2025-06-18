import ctypes
import os

# Визначте шлях до вашої бібліотеки
# У Linux це зазвичай 'libbccbundle.so'
# У macOS це 'libbccbundle.dylib'
# У Windows це 'bccbundle.dll'
# Переконайтеся, що файл бібліотеки знаходиться у тому ж каталозі, що й ваш Python скрипт,
# або в каталозі, що є у вашому PATH.
LIBRARY_NAME = './bcc.so' # Змініть відповідно до вашої ОС
# Якщо бібліотека знаходиться не в поточному каталозі, вкажіть повний шлях:
# LIBRARY_PATH = os.path.join(os.path.dirname(__file__), LIBRARY_NAME)
# lib = ctypes.CDLL(LIBRARY_PATH)
lib = ctypes.CDLL(LIBRARY_NAME)

# --- Визначення C структур у Python за допомогою ctypes ---

# V3dT (з v3d.h)
class V3dT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
    ]

# ConfigT (з bccbundle.h)
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

# AtmosphereT (з bccbundle.h)
class AtmosphereT(ctypes.Structure):
    _fields_ = [
        ("t0", ctypes.c_double),
        ("a0", ctypes.c_double),
        ("p0", ctypes.c_double),
        ("mach", ctypes.c_double),
        ("densityFactor", ctypes.c_double),
        ("cLowestTempC", ctypes.c_double),
    ]

# WindT (з bccbundle.h)
class WindT(ctypes.Structure):
    _fields_ = [
        ("velocity", V3dT), # V3dT - це структура, не покажчик
        ("angle", ctypes.c_double),
        ("yaw", ctypes.c_double),
        ("speed", ctypes.c_double),
    ]

# WindsT (з bccbundle.h)
class WindsT(ctypes.Structure):
    _fields_ = [
        ("winds", ctypes.POINTER(WindT)),
        ("length", ctypes.c_size_t),
    ]

# ShotDataT (з bccbundle.h - З УРАХУВАННЯМ 'stabilityCoefficient' з bccbundle.c)
class ShotDataT(ctypes.Structure):
    _fields_ = [
        ("caliber", ctypes.c_double),
        ("bulletLength", ctypes.c_double),
        ("bulletWeight", ctypes.c_double),
        ("bc", ctypes.c_double),
        ("formFactor", ctypes.c_double),
        ("muzzleVelocity", ctypes.c_double),
        ("sightHeight", ctypes.c_double),
        ("twist", ctypes.c_double),
        ("zeroRange", ctypes.c_double),
        ("dragCoefficient", ctypes.c_double),
        ("diameter", ctypes.c_double),
        ("length", ctypes.c_double),
        ("weight", ctypes.c_double),
        ("spinRPM", ctypes.c_double),
        ("spinDirection", ctypes.c_double),
        ("lineOfSightAngle", ctypes.c_double),
        ("currentAltitude", ctypes.c_double),
        ("sightCorrection", ctypes.c_double),
        ("stabilityCoefficient", ctypes.c_double), # Додано на основі bccbundle.c
        ("atmo", ctypes.POINTER(AtmosphereT)),
        ("winds", ctypes.POINTER(WindsT)),
    ]

# TrajectoryDataT (з bccbundle.h - виведено з createTrajectoryData)
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
        ("drop", ctypes.c_double),
        ("windage", ctypes.c_double),
        ("energy", ctypes.c_double),
        ("pow_val", ctypes.c_double), # Використовуємо pow_val
        ("stability", ctypes.c_double),
        ("g1", ctypes.c_double),
        ("g7", ctypes.c_double),
        ("verticalSpeed", ctypes.c_double),
        ("horizontalSpeed", ctypes.c_double),
        ("verticalAngle", ctypes.c_double),
        ("horizontalAngle", ctypes.c_double),
        ("ballisticCoefficient", ctypes.c_double),
        ("currentAltitude", ctypes.c_double),
    ]

# TrajectoryTableT (з bccbundle.h)
class TrajectoryTableT(ctypes.Structure):
    _fields_ = [
        ("table", ctypes.POINTER(TrajectoryDataT)),
        ("length", ctypes.c_size_t),
    ]

# Placeholder-структури, оскільки їхні повні визначення відсутні у ваших фрагментах .h
# Якщо ці структури мають поля у вашому реальному bccbundle.h,
# вам потрібно буде додати їх повні визначення тут.
# Для простоти, якщо вони ніде не використовуються окрім як покажчики/члени інших структур,
# і їх вміст не потрібен для Python, ми можемо залишити їх порожніми.
class CurveT(ctypes.Structure):
    _fields_ = [] # Пуста, якщо не має полів
class MachListT(ctypes.Structure):
    _fields_ = [] # Пуста, якщо не має полів
class TrajectoryDataFilterT(ctypes.Structure):
    _fields_ = [] # Пуста, якщо не має полів
class WindSockT(ctypes.Structure):
    _fields_ = [] # Пуста, якщо не має полів

# TrajectoryPropsT (з bccbundle.h)
class TrajectoryPropsT(ctypes.Structure):
    _fields_ = [
        ("shotData", ctypes.POINTER(ShotDataT)),
        ("curve", CurveT),
        ("machList", MachListT),
        ("dataFilter", TrajectoryDataFilterT),
        ("windSock", WindSockT),
    ]

# EngineT (з bccbundle.h)
class EngineT(ctypes.Structure):
    _fields_ = [
        ("config", ctypes.POINTER(ConfigT)),
        ("gravityVector", V3dT),
        ("tProps", TrajectoryPropsT),
    ]

# TrajFlag - припустимо, це int
TrajFlag = ctypes.c_int

# --- Прототипи функцій ---

# initDefaultConfig
lib.initDefaultConfig.argtypes = [ctypes.POINTER(ConfigT)]
lib.initDefaultConfig.restype = None

# updateStabilityCoefficient
lib.updateStabilityCoefficient.argtypes = [ctypes.POINTER(ShotDataT)]
lib.updateStabilityCoefficient.restype = None

# initEngine
lib.initEngine.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ConfigT)]
lib.initEngine.restype = ctypes.c_int

# initTrajectory
lib.initTrajectory.argtypes = [ctypes.POINTER(EngineT), ctypes.POINTER(ShotDataT)]
lib.initTrajectory.restype = ctypes.c_int

# freeTrajectory
lib.freeTrajectory.argtypes = [ctypes.POINTER(EngineT)]
lib.freeTrajectory.restype = None

# zeroAngle
lib.zeroAngle.argtypes = [
    ctypes.POINTER(EngineT),
    ctypes.POINTER(ShotDataT),
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double) # zeroAngle
]
lib.zeroAngle.restype = ctypes.c_int

# trajectory
lib.trajectory.argtypes = [
    ctypes.POINTER(EngineT),
    ctypes.POINTER(ShotDataT),
    ctypes.c_double, # maxRange
    ctypes.c_double, # distStep
    ctypes.c_int,    # extraData
    ctypes.c_double, # timeStep
    ctypes.POINTER(TrajectoryTableT)
]
lib.trajectory.restype = ctypes.c_int

# integrate - фокус вашого запиту
lib.integrate.argtypes = [
    ctypes.POINTER(EngineT),
    ctypes.c_double, # maxRange
    ctypes.c_double, # recordStep
    TrajFlag,        # filterFlags
    ctypes.c_double, # timeStep
    ctypes.POINTER(TrajectoryTableT)
]
lib.integrate.restype = ctypes.c_int

# V3dT functions (example from v3d.h)
lib.set.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
lib.set.restype = V3dT

# --- Приклад використання ---
if __name__ == "__main__":
    # 1. Ініціалізація ConfigT
    config = ConfigT()
    lib.initDefaultConfig(ctypes.byref(config))
    print(f"Config - Gravity Constant: {config.cGravityConstant}")

    # 2. Ініціалізація AtmosphereT
    atmo = AtmosphereT(
        t0=20.0,
        a0=0.0,
        p0=1013.25,
        mach=0.0,
        densityFactor=1.0,
        cLowestTempC=-130.0
    )

    # 3. Ініціалізація WindsT (припустимо, що вітру немає або він нульовий)
    winds = WindsT(winds=None, length=0) # Без виділення пам'яті для вітрів, оскільки їх немає

    # 4. Ініціалізація ShotDataT
    shot_data = ShotDataT(
        caliber=0.308,
        bulletLength=1.25,
        bulletWeight=175.0,
        bc=0.500,
        formFactor=1.0,
        muzzleVelocity=2600.0,
        sightHeight=1.5,
        twist=10.0,
        zeroRange=100.0,
        dragCoefficient=0.0, # Буде розраховано
        diameter=0.308,
        length=1.25,
        weight=175.0,
        spinRPM=0.0,
        spinDirection=0.0,
        lineOfSightAngle=0.0,
        currentAltitude=0.0,
        sightCorrection=0.0,
        stabilityCoefficient=0.0, # Заповниться updateStabilityCoefficient
        atmo=ctypes.POINTER(AtmosphereT)(atmo),  # Змінено: використовуємо ctypes.POINTER(Type)(instance)
        winds=ctypes.POINTER(WindsT)(winds) # Змінено: використовуємо ctypes.POINTER(Type)(instance)
    )

    # Виклик updateStabilityCoefficient для заповнення поля stabilityCoefficient
    lib.updateStabilityCoefficient(ctypes.byref(shot_data))
    print(f"ShotData - Stability Coefficient: {shot_data.stabilityCoefficient}")

    # 5. Ініціалізація EngineT
    engine = EngineT()

    # 6. Ініціалізація Engine
    engine.gravityVector = lib.set(0.0, 0.0, -config.cGravityConstant) # Використовуємо константу з config

    result_init_engine = lib.initEngine(ctypes.byref(engine), ctypes.byref(config))
    if result_init_engine != 0:
        print("Error initializing engine!")
    else:
        print("Engine initialized successfully.")

        # 7. Ініціалізація траєкторії (заповнює tProps всередині Engine)
        result_init_trajectory = lib.initTrajectory(ctypes.byref(engine), ctypes.byref(shot_data))
        if result_init_trajectory != 0:
            print("Error initializing trajectory!")
        else:
            print("Trajectory initialized successfully.")

            # 8. Виклик integrate
            max_range = 1000.0 # feet
            record_step = 10.0 # feet
            filter_flags = 0   # Або інше значення TrajFlag
            time_step = 0.01   # seconds

            result_trajectory_table = TrajectoryTableT() # Створюємо об'єкт Python

            # Важливо: функція integrate в C, ймовірно, виділяє пам'ять для
            # result_trajectory_table->table. Цю пам'ять потрібно звільнити!
            # Перевірте bccbundle.c, як саме allocate/free пам'ять для таблиці.

            result_integrate = lib.integrate(
                ctypes.byref(engine),
                max_range,
                record_step,
                filter_flags,
                time_step,
                ctypes.byref(result_trajectory_table)
            )

            if result_integrate != 0:
                print(f"Error calculating trajectory with integrate: {result_integrate}")
            else:
                print(f"Trajectory calculated successfully with integrate. Table length: {result_trajectory_table.length}")
                if result_trajectory_table.length > 0 and result_trajectory_table.table:
                    print("\nSample Trajectory Data (first 5 points from integrate):")
                    for i in range(min(5, result_trajectory_table.length)):
                        point = result_trajectory_table.table[i]
                        print(f"  Time: {point.time:.3f}s, Range: ({point.rangeVector.x:.1f}, {point.rangeVector.y:.1f}, {point.rangeVector.z:.1f})ft, "
                              f"Velocity: {point.velocity:.1f} ft/s, Drop: {point.drop:.2f}ft")

                    # Звільнення пам'яті, виділеної C-функцією для таблиці
                    # ЦЕ ДУЖЕ ВАЖЛИВО, щоб уникнути витоків пам'яті.
                    # Якщо `integrate` виділяє `result_trajectory_table->table`,
                    # тоді повинна бути відповідна `free` функція в C, або вам доведеться
                    # викликати `libc.free(result_trajectory_table.table)` якщо це було `malloc`.
                    # Наразі, я припускаю, що вам потрібно буде додати функцію звільнення.
                    # Якщо у bccbundle.c є функція freeTrajectoryTable(TrajectoryTableT*),
                    # її слід викликати тут. Інакше, якщо це malloc, то:
                    # from ctypes import CDLL, c_void_p
                    # libc = CDLL("libc.so.6") # Для Linux
                    # libc.free.argtypes = [c_void_p]
                    # libc.free(result_trajectory_table.table)
                else:
                    print("Trajectory table is empty or invalid after integrate.")

            # 9. Звільнення Engine
            lib.freeTrajectory(ctypes.byref(engine))
            print("Engine freed successfully.")