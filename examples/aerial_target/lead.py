# /// script
# dependencies = [
#   "matplotlib",
#   "numpy",
#   "py_ballisticcalc[exts]"
# ]
# ///

import math
import copy
from typing import Literal
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Polygon
import numpy as np
from py_ballisticcalc import *


PreferredUnits.drop = Unit.Centimeter
PreferredUnits.distance = Unit.Meter
PreferredUnits.velocity = Unit.MPS

class SightFOV:
    """
    Поле зору прицілу (в градусах), з центром у LEAD POINT (ми цілимось ЦЕНТРОМ
    прицілу саме туди). windage/elevation виміряні відносно похилої (slant)
    дальності D до LEAD POINT, а не X, як Z_screen/Y_screen (K*z/x) - тому й
    масштаб тут K*(D/x), а не просто K, інакше кут занижений (K*tan(fov/2)
    дає МЕНШИЙ кутовий розкид на екрані, ніж насправді бачив би стрілець).
    """

    def __init__(self, fov_x_deg: float, fov_y_deg: float):
        self.fov_x_deg = fov_x_deg
        self.fov_y_deg = fov_y_deg

    def rectangle_corners(self, K: float, x: float, slant_distance: float, center_z: float, center_y: float):
        """
        Кути прямокутника поля зору з центром у LEAD POINT (center_z, center_y).
        x, slant_distance - реальні (не екранні) X і похила дальність ДО LEAD POINT,
        ті самі, що використовуються для обчислення windage/elevation.
        """
        scale = K * (slant_distance / x)
        half_w = scale * math.tan(math.radians(self.fov_x_deg / 2))
        half_h = scale * math.tan(math.radians(self.fov_y_deg / 2))
        top_left = (center_z - half_w, center_y + half_h)
        top_right = (center_z + half_w, center_y + half_h)
        bottom_right = (center_z + half_w, center_y - half_h)
        bottom_left = (center_z - half_w, center_y - half_h)
        return [top_left, top_right, bottom_right, bottom_left]

    def extreme_rays(self, K: float, x: float, slant_distance: float, center_z: float, center_y: float):
        """
        Два кути прямокутника поля зору, що дають МАКСИМАЛЬНИЙ кутовий розкид
        як видно від спостерігача (0, 0) - саме вони обмежують промені.
        """
        corners = self.rectangle_corners(K, x, slant_distance, center_z, center_y)
        angles = [math.atan2(cy, cz) for cz, cy in corners]
        return corners[angles.index(min(angles))], corners[angles.index(max(angles))]


PLOT_XLIM = (-1000, 1000)
PLOT_YLIM = (-200, 1200)


def extend_ray_to_bounds(cz: float, cy: float, xlim=PLOT_XLIM, ylim=PLOT_YLIM, margin: float = 1.2):
    """
    Продовжує промінь з (0,0) через (cz,cy) ЗА межі області графіка (з запасом
    margin), щоб заливка не обрізалась видимими краями через похибки округлення.
    """
    ts = []
    if cz > 0:
        ts.append(xlim[1] / cz)
    elif cz < 0:
        ts.append(xlim[0] / cz)
    if cy > 0:
        ts.append(ylim[1] / cy)
    elif cy < 0:
        ts.append(ylim[0] / cy)
    t = min(t for t in ts if t > 0) * margin
    return cz * t, cy * t

# --- Реалістична оцінка руху цілі ---
class TargetTracker:
    """
    Відстежує ціль і оцінює її рух БЕЗ знання майбутньої траєкторії
    (так, як працює реальна система наведення)
    """

    def __init__(self, history_length=10, dt=0.1):
        self.history = []  # [(t, x, y, z), ...]
        self.history_length = history_length
        self.dt = dt

    def update(self, t, x, y, z):
        """Додає нове вимірювання позиції"""
        self.history.append((t, x, y, z))
        if len(self.history) > self.history_length:
            self.history.pop(0)

    def estimate_velocity(self):
        """Оцінює швидкість на основі останніх вимірювань"""
        if len(self.history) < 2:
            return (0, 0, 0)

        # Лінійна регресія по останніх точках
        t1, x1, y1, z1 = self.history[0]
        t2, x2, y2, z2 = self.history[-1]
        dt = t2 - t1

        if dt == 0:
            return (0, 0, 0)

        return ((x2 - x1) / dt, (y2 - y1) / dt, (z2 - z1) / dt)

    def estimate_acceleration(self):
        """Оцінює прискорення (другу похідну)"""
        if len(self.history) < 3:
            return (0, 0, 0)

        # Чисельна друга похідна
        n = len(self.history)
        t1, x1, y1, z1 = self.history[n - 3]
        t2, x2, y2, z2 = self.history[n - 2]
        t3, x3, y3, z3 = self.history[n - 1]

        dt1 = t2 - t1
        dt2 = t3 - t2

        if dt1 == 0 or dt2 == 0:
            return (0, 0, 0)

        vx1 = (x2 - x1) / dt1
        vx2 = (x3 - x2) / dt2
        ax = (vx2 - vx1) / ((dt1 + dt2) / 2)

        vy1 = (y2 - y1) / dt1
        vy2 = (y3 - y2) / dt2
        ay = (vy2 - vy1) / ((dt1 + dt2) / 2)

        vz1 = (z2 - z1) / dt1
        vz2 = (z3 - z2) / dt2
        az = (vz2 - vz1) / ((dt1 + dt2) / 2)

        return (ax, ay, az)

    def predict_position(self, t_future, use_acceleration=True):
        """
        Прогнозує позицію на основі ТІЛЬКИ історії вимірювань
        (без знання справжньої траєкторії)
        """
        if len(self.history) < 2:
            return None

        t_current, x, y, z = self.history[-1]
        dt = t_future - t_current

        vx, vy, vz = self.estimate_velocity()

        if not use_acceleration or len(self.history) < 3:
            # Лінійна екстраполяція
            return (x + vx * dt, y + vy * dt, z + vz * dt)
        else:
            # Квадратична екстраполяція
            ax, ay, az = self.estimate_acceleration()
            return (x + vx * dt + 0.5 * ax * dt**2, y + vy * dt + 0.5 * ay * dt**2, z + vz * dt + 0.5 * az * dt**2)


# --- Базовий клас цілі ---
class Target:
    def __init__(self, angle_deg):
        self.angle_deg = angle_deg
        self.K = 750  # проекційний масштаб

    def position(self, t):
        raise NotImplementedError

    def velocity(self, t):
        raise NotImplementedError

    def acceleration(self, t):
        """Прискорення цілі (для поліноміальної екстраполяції)"""
        dt = 0.01
        vx1, vy1, vz1 = self.velocity(t)
        vx2, vy2, vz2 = self.velocity(t + dt)
        return ((vx2 - vx1) / dt, (vy2 - vy1) / dt, (vz2 - vz1) / dt)

    def projected_position(self, t):
        x, y, z = self.position(t)
        if x <= 0:
            return None
        return (self.K * z / x, self.K * y / x)

    def project_3d_point(self, x, y, z):
        """Проектує довільну 3D точку на екран"""
        if x <= 0:
            return None
        return (self.K * z / x, self.K * y / x)

    def projected_velocity(self, t):
        x, y, z = self.position(t)
        vx, vy, vz = self.velocity(t)
        if x <= 0:
            return 0, 0, vx, vy, vz, 0
        dz_screen = self.K * (vz * x - z * vx) / x**2
        dy_screen = self.K * (vy * x - y * vx) / x**2
        V_scalar = math.sqrt(vx**2 + vy**2 + vz**2)
        return dz_screen, dy_screen, vx, vy, vz, V_scalar

    def projected_velocity_3d(self, t):
        """
        Повертає:
        - dx_screen, dy_screen, dz_screen: проєктовані зміщення на "екрані"
        - vx, vy, vz: реальні компоненти швидкості
        - V_scalar: модуль швидкості
        """
        x, y, z = self.position(t)
        vx, vy, vz = self.velocity(t)
        if x <= 0:  # ціль позаду спостерігача
            return 0, 0, 0, vx, vy, vz, 0

        # Для спостереження з (0,0,0) уздовж X:
        # "екран" = площина YZ, тобто:
        dx_screen = 0  # ми не зміщуємося по X на екрані
        dy_screen = (vy * x - y * vx) / x**2 * self.K
        dz_screen = (vz * x - z * vx) / x**2 * self.K

        V_scalar = math.sqrt(vx**2 + vy**2 + vz**2)
        return dx_screen, dy_screen, dz_screen, vx, vy, vz, V_scalar


# --- Кругова траєкторія ---
class CircularTarget(Target):
    def __init__(self, radius=100, distance=500, angle_deg=10, speed=50):
        super().__init__(angle_deg)
        self.R = radius
        self.speed = speed
        self.omega = speed / radius
        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0

    def position(self, t):
        return (
            self.center_x + self.R * math.cos(self.omega * t),
            self.center_y,
            self.center_z + self.R * math.sin(self.omega * t),
        )

    def velocity(self, t):
        return (-self.R * self.omega * math.sin(self.omega * t), 0.0, self.R * self.omega * math.cos(self.omega * t))


# --- Еліптична траєкторія ---
class EllipticalTarget(Target):
    def __init__(self, semi_major_axis=250, semi_minor_axis=100, distance=600, angle_deg=10, speed=40):
        super().__init__(angle_deg)
        self.a = semi_major_axis  # Велика піввісь (впливає на X)
        self.b = semi_minor_axis  # Мала піввісь (впливає на Z)
        self.speed = speed

        # Обчислення кутової швидкості (omega) на основі середньої швидкості
        # Приблизна довжина еліпса (за Рамануджаном):
        # L ≈ π * [3(a+b) - sqrt((3a+b)(a+3b))]
        approx_perimeter = math.pi * (3 * (self.a + self.b) - math.sqrt((3 * self.a + self.b) * (self.a + 3 * self.b)))
        self.omega = (self.speed * 2 * math.pi) / approx_perimeter

        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0

    def position(self, t):
        angle = self.omega * t

        # X: Косинус впливає на зміну дальності від центру
        x_offset = self.a * math.cos(angle)

        # Z: Синус впливає на бічний зсув
        z_offset = self.b * math.sin(angle)

        return (
            self.center_x + x_offset,
            self.center_y,
            self.center_z + z_offset,
        )

    def velocity(self, t):
        angle = self.omega * t

        # Похідна X: d(a*cos(ωt))/dt = -a*ω*sin(ωt)
        vx = -self.a * self.omega * math.sin(angle)

        # Y: 0
        vy = 0.0

        # Похідна Z: d(b*sin(ωt))/dt = b*ω*cos(ωt)
        vz = self.b * self.omega * math.cos(angle)

        return (vx, vy, vz)


# --- Прямолінійний рух через центр ---
class CrossingZigzagTarget(Target):
    def __init__(self, amplitude=200, distance=700, angle_deg=15, speed=50, period=4, crossing_angle_deg=0):
        super().__init__(angle_deg)
        self.amplitude = amplitude
        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0
        self.speed = speed
        self.period = period

        # # напрямок осі zigzag у горизонтальній площині
        # ca = math.radians(crossing_angle_deg)
        # self.dx = math.sin(ca)
        # self.dz = math.cos(ca)

        # напрям осі zigzag у горизонтальній площині
        ca = math.radians(crossing_angle_deg)
        # ЗМІНА: 0° -> рух на нас (x зменшується), 90° -> зліва->направо (z зростає)
        self.dx = -math.cos(ca)
        self.dz = math.sin(ca)

    def position(self, t):
        # оригінальний zigzag
        cycle = (t * self.speed / self.amplitude) % self.period

        if cycle < self.period / 2:
            z_offset = -self.amplitude + (2 * self.amplitude * cycle / (self.period / 2))
        else:
            z_offset = self.amplitude - (2 * self.amplitude * (cycle - self.period / 2) / (self.period / 2))

        # Повертаємо zigzag у горизонтальній площині
        x = self.center_x + self.dx * z_offset
        y = self.center_y
        z = self.center_z + self.dz * z_offset

        return (x, y, z)

    def velocity(self, t):
        dt = 0.001
        x1, y1, z1 = self.position(t)
        x2, y2, z2 = self.position(t + dt)
        return ((x2 - x1) / dt, (y2 - y1) / dt, (z2 - z1) / dt)


# --- Вісімка (figure-8) ---
class FigureEightTarget(Target):
    def __init__(self, width=200, height=150, distance=700, angle_deg=15, speed=30):
        super().__init__(angle_deg)
        self.width = width
        self.height = height
        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0
        self.omega = speed / max(width, height)

    def position(self, t):
        scale = 1 / (1 + math.sin(self.omega * t) ** 2)
        return (
            self.center_x + self.width * math.cos(self.omega * t) * scale,
            self.center_y + self.height * math.sin(self.omega * t) * math.cos(self.omega * t) * scale,
            self.center_z + self.width * math.sin(self.omega * t) * scale,
        )

    def velocity(self, t):
        dt = 0.001
        x1, y1, z1 = self.position(t)
        x2, y2, z2 = self.position(t + dt)
        return ((x2 - x1) / dt, (y2 - y1) / dt, (z2 - z1) / dt)


# --- Зигзаг ---
class ZigzagTarget(Target):
    def __init__(self, amplitude=200, distance=700, angle_deg=15, speed=50, period=4):
        super().__init__(angle_deg)
        self.amplitude = amplitude
        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0
        self.speed = speed
        self.period = period

    def position(self, t):
        cycle = (t * self.speed / self.amplitude) % self.period
        if cycle < self.period / 2:
            z_offset = -self.amplitude + (2 * self.amplitude * cycle / (self.period / 2))
        else:
            z_offset = self.amplitude - (2 * self.amplitude * (cycle - self.period / 2) / (self.period / 2))

        return (self.center_x, self.center_y, self.center_z + z_offset)

    def velocity(self, t):
        dt = 0.001
        x1, y1, z1 = self.position(t)
        x2, y2, z2 = self.position(t + dt)
        return ((x2 - x1) / dt, (y2 - y1) / dt, (z2 - z1) / dt)


# --- Спіраль ---
class SpiralTarget(Target):
    def __init__(self, radius_start=100, radius_end=300, distance=700, angle_deg=15, speed=40, cycles=2):
        super().__init__(angle_deg)
        self.radius_start = radius_start
        self.radius_end = radius_end
        self.center_x = distance
        self.center_y = distance * math.tan(math.radians(angle_deg))
        self.center_z = 0
        self.speed = speed
        self.cycles = cycles
        self.total_angle = cycles * 2 * math.pi

    def position(self, t):
        angle = (t * self.speed / self.radius_end) % self.total_angle
        radius = self.radius_start + (self.radius_end - self.radius_start) * (angle / self.total_angle)

        return (self.center_x + radius * math.cos(angle), self.center_y, self.center_z + radius * math.sin(angle))

    def velocity(self, t):
        dt = 0.001
        x1, y1, z1 = self.position(t)
        x2, y2, z2 = self.position(t + dt)
        return ((x2 - x1) / dt, (y2 - y1) / dt, (z2 - z1) / dt)


# --- Прямий перпендикулярний переліт (стала швидкість, без zigzag) ---
class StraightCrossingTarget(Target):
    """
    Ціль рухається зі сталою швидкістю СТРОГО перпендикулярно до лінії
    візування (без зигзагу) - той самий сценарій, що й у crossing_lead.py:
    задана висота цілі (не дальність), кут візування і швидкість.
    """

    def __init__(self, height=500, angle_deg=45, speed=50, start_z=0):
        super().__init__(angle_deg)
        self.center_x = height / math.tan(math.radians(angle_deg))
        self.center_y = height
        self.center_z = start_z
        self.speed = speed

    def position(self, t):
        return (self.center_x, self.center_y, self.center_z + self.speed * t)

    def velocity(self, t):
        return (0.0, 0.0, self.speed)


# --- Ініціалізація калькулятора ---
calc = Calculator(engine="cythonized_rk4_engine")


def get_zero_shot():
    dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
    ammo = Ammo(dm, 850, Temperature.Celsius(15), use_powder_sensitivity=True)
    ammo.calc_powder_sens(820, Temperature.Celsius(0))
    weapon = Weapon(sight_height=9, twist=15)
    atmo = Atmo(altitude=Distance.Meter(1000), temperature=Unit.Celsius(5), humidity=0.5)
    return Shot(weapon=weapon, ammo=ammo, atmo=atmo)


zero = get_zero_shot()


def get_zero_elev(zero: Shot, distance):
    zero_distance = Distance.Meter(distance)
    zero_elevation = calc.set_weapon_zero(zero, zero_distance)
    print(f"Barrel elevation for {zero_distance} zero: {zero_elevation << PreferredUnits.adjustment}")
    print(f"Muzzle velocity: {zero.ammo.get_velocity_for_temp(zero.atmo.temperature) << PreferredUnits.velocity}")


get_zero_elev(zero, 500)


def get_trajectory_at_distance(zero: Shot, slant_distance, look_angle):
    """
    Отримати балістичні дані для заданої похилої (slant) відстані та кута візування.

    barrel_elevation_for_target() очікує похилу (slant) дальність, а calc.fire()
    очікує горизонтальну (по осі X) дальність - тому їх не можна плутати.
    """
    new_shot: Shot = copy.copy(zero)
    new_shot.look_angle = Angular.Degree(look_angle)
    new_slant_distance = Distance.Meter(slant_distance)
    new_elevation = calc.barrel_elevation_for_target(shot=new_shot, target_distance=new_slant_distance)
    hold = Angular.Mil((new_elevation >> Angular.Mil) - (zero.weapon.zero_elevation >> Angular.Mil))
    new_shot.relative_angle = hold

    horizontal_distance = Distance.Meter(slant_distance * math.cos(math.radians(look_angle)))
    return calc.fire(
        new_shot,
        trajectory_range=horizontal_distance,
        trajectory_step=horizontal_distance,
        flags=TrajFlag.NONE,
        raise_range_error=False,
    )[-1]


def predict_target_position(target: Target, t: float, dt: float, use_acceleration=True):
    """Прогнозує позицію цілі через dt секунд з урахуванням прискорення"""
    x, y, z = target.position(t)
    vx, vy, vz = target.velocity(t)

    if not use_acceleration:
        return (x + vx * dt, y + vy * dt, z + vz * dt)
    else:
        ax, ay, az = target.acceleration(t)
        return (x + vx * dt + 0.5 * ax * dt**2, y + vy * dt + 0.5 * ay * dt**2, z + vz * dt + 0.5 * az * dt**2)


def calculate_angular_lead_realistic(
    zero: Shot,
    tracker: TargetTracker,
    t: float = 0.0,
    max_iterations: int = 10,
    convergence_threshold: float = 0.001,
    use_acceleration: bool = True,
    reaction_time: float = 0.0,
):
    """РЕАЛІСТИЧНИЙ алгоритм - використовує ТІЛЬКИ історію вимірювань"""
    if len(tracker.history) < 2:
        return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

    t_current, x, y, z = tracker.history[-1]
    distance = math.sqrt(x**2 + y**2 + z**2)
    look_angle = math.degrees(math.atan2(y, x))

    try:
        hit = get_trajectory_at_distance(zero, distance, look_angle)
        TOF = hit.time + reaction_time
    except Exception as e:
        return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

    converged = False
    for iteration in range(max_iterations):
        future_pos = tracker.predict_position(t_current + TOF, use_acceleration)

        if future_pos is None:
            break

        future_x, future_y, future_z = future_pos
        future_distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
        future_look_angle = math.degrees(math.atan2(future_y, future_x))

        try:
            hit_future = get_trajectory_at_distance(zero, future_distance, future_look_angle)
            TOF_new = hit_future.time + reaction_time
        except Exception as e:
            break

        if abs(TOF_new - TOF) < convergence_threshold:
            converged = True
            TOF = TOF_new
            break

        TOF = TOF_new

    future_pos = tracker.predict_position(t_current + TOF, use_acceleration)
    if future_pos is None:
        return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

    future_x, future_y, future_z = future_pos
    future_distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)

    lateral_offset_m = future_z
    D_ft = Distance.Meter(future_distance).get_in(Distance.Foot)
    Z_ft = Distance.Meter(lateral_offset_m).get_in(Distance.Foot)
    windage_rad = TrajectoryData.get_correction(D_ft, Z_ft)

    center_y_at_future = future_x * math.tan(math.radians(look_angle))
    vertical_offset_m = future_y - center_y_at_future
    Y_ft = Distance.Meter(vertical_offset_m).get_in(Distance.Foot)
    elevation_rad = TrajectoryData.get_correction(D_ft, Y_ft)

    return (
        Angular.Radian(windage_rad),
        Angular.Radian(elevation_rad),
        TOF,
        (future_x, future_y, future_z),
        iteration + 1,
        converged,
    )


# def calculate_angular_lead_realistic_measured(zero: Shot, tracker: TargetTracker, reaction_time: float = 0.0):
#     """
#     Реалістичний алгоритм з упередженням.
#     Використовує лише історію вимірювань та коротке прогнозування на час реакції.
#     """
#     if len(tracker.history) == 0:
#         # Немає даних
#         return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

#     # Останнє відоме положення
#     t_current, x, y, z = tracker.history[-1]

#     # Оцінка швидкості з історії (лінійна)
#     vx, vy, vz = tracker.estimate_velocity()

#     # Прогнозування на час реакції
#     future_x = x + vx * reaction_time
#     future_y = y + vy * reaction_time
#     future_z = z + vz * reaction_time

#     # Розрахунок балістики для майбутньої позиції
#     distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
#     look_angle = math.degrees(math.atan2(future_y, future_x))

#     try:
#         hit = get_trajectory_at_distance(zero, distance, look_angle)
#         TOF = hit.time + reaction_time
#     except Exception:
#         # Якщо балістика не обчислилась, беремо останнє положення
#         TOF = 0.0

#     # Обчислення корекцій для прицілу
#     lateral_offset_m = future_z
#     D_ft = Distance.Meter(distance).get_in(Distance.Foot)
#     Z_ft = Distance.Meter(lateral_offset_m).get_in(Distance.Foot)
#     windage_rad = TrajectoryData.get_correction(D_ft, Z_ft)

#     center_y_at_future = future_x * math.tan(math.radians(look_angle))
#     vertical_offset_m = future_y - center_y_at_future
#     Y_ft = Distance.Meter(vertical_offset_m).get_in(Distance.Foot)
#     elevation_rad = TrajectoryData.get_correction(D_ft, Y_ft)

#     return (
#         Angular.Radian(windage_rad),
#         Angular.Radian(elevation_rad),
#         TOF,
#         (future_x, future_y, future_z),
#         1,  # одна "реалістична" ітерація
#         True,  # вважаємо, що конверговано
#     )


# def calculate_angular_lead_realistic_measured(
#     zero: Shot,
#     tracker: TargetTracker,
#     reaction_time: float = 0.0,
#     use_acceleration: bool = True,
#     max_iterations: int = 8,
#     convergence_threshold: float = 0.0005,
# ):
#     """
#     Реалістичне упередження.
#     Використовує тільки виміряні швидкості/прискорення.
#     НЕ є передбаченням – це саме корекція прицілу.
#     """

#     if len(tracker.history) < 2:
#         return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

#     # Поточний стан
#     t_cur, x, y, z = tracker.history[-1]
#     vx, vy, vz = tracker.estimate_velocity()
#     ax, ay, az = tracker.estimate_acceleration() if use_acceleration else (0, 0, 0)

#     # Початкове наближення майбутньої позиції (дуже грубе)
#     future_x = x
#     future_y = y
#     future_z = z

#     # Початковий TOF
#     TOF = 0.0
#     converged = False

#     for iteration in range(max_iterations):
#         # 1) Відстань до прогнозованої точки зустрічі
#         distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)

#         # Look angle В ТОЧКУ ПОТЕНЦІЙНОГО ПОПАДАННЯ!
#         look_angle = math.degrees(math.atan2(future_y, future_x))

#         # 2) Скільки летітиме куля до цієї точки
#         try:
#             hit: TrajectoryData = get_trajectory_at_distance(zero, distance, look_angle)
#             TOF_new = hit.time + reaction_time
#         except Exception:
#             break

#         # 3) Обчислюємо НОВУ точку, де ціль буде через TOF_new
#         future_x_new = x + vx * TOF_new + 0.5 * ax * TOF_new**2
#         future_y_new = y + vy * TOF_new + 0.5 * ay * TOF_new**2
#         future_z_new = z + vz * TOF_new + 0.5 * az * TOF_new**2

#         # 4) Перевірка збіжності
#         if abs(TOF_new - TOF) < convergence_threshold:
#             converged = True
#             future_x, future_y, future_z = future_x_new, future_y_new, future_z_new
#             TOF = TOF_new
#             break

#         # Оновлюємо TOF і прогноз
#         future_x, future_y, future_z = future_x_new, future_y_new, future_z_new
#         TOF = TOF_new

#     # --- ФІНАЛЬНИЙ РОЗРАХУНОК КОРЕКЦІЙ ---
#     distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
#     look_angle = math.degrees(math.atan2(future_y, future_x))

#     # «Поперечна» складова (вбік)
#     lateral_offset_m = future_z
#     D_ft = Distance.Meter(distance).get_in(Distance.Foot)
#     Z_ft = Distance.Meter(lateral_offset_m).get_in(Distance.Foot)
#     windage_rad = TrajectoryData.get_correction(D_ft, Z_ft)

#     # «Вертикальна» складова
#     center_y_at_future = future_x * math.tan(math.radians(look_angle))
#     vertical_offset_m = future_y - center_y_at_future
#     Y_ft = Distance.Meter(vertical_offset_m).get_in(Distance.Foot)
#     elevation_rad = TrajectoryData.get_correction(D_ft, Y_ft)

#     return (
#         Angular.Radian(windage_rad),
#         Angular.Radian(elevation_rad),
#         TOF,
#         (future_x, future_y, future_z),
#         iteration + 1,
#         converged,
#     )


def calculate_angular_lead_realistic_measured(
    zero: Shot,
    tracker: TargetTracker,
    reaction_time: float = 0.0,
    use_acceleration: bool = True,
    max_iterations: int = 8,
    convergence_threshold: float = 0.0005,
):
    # ... (Весь код ітеративного обчислення TOF залишається без змін) ...

    if len(tracker.history) < 2:
        return Angular.Radian(0), Angular.Radian(0), 0.0, None, 0, False

    t_cur, x, y, z = tracker.history[-1]
    vx, vy, vz = tracker.estimate_velocity()
    ax, ay, az = tracker.estimate_acceleration() if use_acceleration else (0, 0, 0)

    future_x, future_y, future_z = x, y, z
    TOF = 0.0
    converged = False
    hit = None  # Додаємо ініціалізацію змінної hit

    for iteration in range(max_iterations):
        distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
        look_angle = math.degrees(math.atan2(future_y, future_x))

        try:
            # Отримуємо об'єкт hit для останнього TOF
            hit: TrajectoryData = get_trajectory_at_distance(zero, distance, look_angle)
            TOF_new = hit.time + reaction_time
        except Exception:
            break

        if abs(TOF_new - TOF) < convergence_threshold:
            converged = True
            future_x, future_y, future_z = future_x_new, future_y_new, future_z_new
            TOF = TOF_new
            break

        future_x_new = x + vx * TOF_new + 0.5 * ax * TOF_new**2
        future_y_new = y + vy * TOF_new + 0.5 * ay * TOF_new**2
        future_z_new = z + vz * TOF_new + 0.5 * az * TOF_new**2

        future_x, future_y, future_z = future_x_new, future_y_new, future_z_new
        TOF = TOF_new

    # Перевірка на випадок, якщо hit не був обчислений
    if hit is None:
        return Angular.Radian(0), Angular.Radian(0), 0.0, (future_x, future_y, future_z), 0, False

    # --- ФІНАЛЬНИЙ РОЗРАХУНОК КОРЕКЦІЙ ---
    distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
    # look_angle не потрібен тут, він був потрібен для TOF

    # 1. ОБЧИСЛЕННЯ LEAD (УПЕРЕДЖЕННЯ)

    # Горизонтальне упередження (вбік)
    lateral_offset_m = future_z
    D_ft = Distance.Meter(distance).get_in(Distance.Foot)
    Z_ft = Distance.Meter(lateral_offset_m).get_in(Distance.Foot)
    windage_lead_rad = TrajectoryData.get_correction(D_ft, Z_ft)  # Поправка на рух цілі

    # Вертикальне упередження
    # center_y_at_future - це точка, в яку б прицільна лінія прийшла на distance
    center_y_at_future = future_x * math.tan(math.radians(CENTER_LOOK_ANGLE))
    vertical_offset_m = future_y - center_y_at_future
    Y_ft = Distance.Meter(vertical_offset_m).get_in(Distance.Foot)
    elevation_lead_rad = TrajectoryData.get_correction(D_ft, Y_ft)  # Поправка на рух цілі

    # 2. ОТРИМАННЯ DRIFT & DROP (ДРЕЙФ І ПАДІННЯ)

    # hit.windage - це зміщення кулі через вітер
    # hit.drop - це зміщення кулі через гравітацію/опір (вертикальне)

    # Конвертуємо зміщення hit.windage (в метрах) в радіани
    windage_drift_rad = hit.windage.get_in(Distance.Meter) / hit.distance.get_in(Distance.Meter)

    # hit.drop_angle вже в радіанах
    # hit.drop_angle - це зміщення в кутових одиницях, яке треба компенсувати
    drop_rad = hit.drop_angle.get_in(Angular.Radian)

    # 3. ДОДАВАННЯ КОРЕКЦІЙ

    # Вертикальна корекція: Lead (рух цілі) + Drop (балістика)
    # Drop завжди від'ємний (вниз), тому ми його ДОДАЄМО, щоб "підняти" приціл
    total_elevation_rad = elevation_lead_rad + drop_rad

    # Горизонтальна корекція: Lead (рух цілі) + Drift (вітер)
    total_windage_rad = windage_lead_rad + windage_drift_rad

    return (
        Angular.Radian(total_windage_rad),
        Angular.Radian(total_elevation_rad),
        TOF,
        (future_x, future_y, future_z),
        iteration + 1,
        converged,
    )


def calculate_angular_lead_iterative(
    zero: Shot,
    target: Target,
    t: float = 0.0,
    max_iterations: int = 10,
    convergence_threshold: float = 0.001,
    use_acceleration: bool = True,
    reaction_time: float = 0.0,
):
    """ВСЕЗНАЮЧИЙ алгоритм - знає всю траєкторію наперед"""
    x, y, z = target.position(t)
    distance = math.sqrt(x**2 + y**2 + z**2)
    look_angle = math.degrees(math.atan2(y, x))

    try:
        hit = get_trajectory_at_distance(zero, distance, look_angle)
        TOF = hit.time + reaction_time
    except Exception as e:
        return Angular.Radian(0), Angular.Radian(0), 0.0, (x, y, z), 0, False

    converged = False
    for iteration in range(max_iterations):
        future_x, future_y, future_z = predict_target_position(target, t, TOF, use_acceleration)
        future_distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
        future_look_angle = math.degrees(math.atan2(future_y, future_x))

        try:
            hit_future = get_trajectory_at_distance(zero, future_distance, future_look_angle)
            TOF_new = hit_future.time + reaction_time
        except Exception as e:
            break

        if abs(TOF_new - TOF) < convergence_threshold:
            converged = True
            TOF = TOF_new
            break

        TOF = TOF_new

    future_x, future_y, future_z = predict_target_position(target, t, TOF, use_acceleration)
    future_distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)

    lateral_offset_m = future_z
    D_ft = Distance.Meter(future_distance).get_in(Distance.Foot)
    Z_ft = Distance.Meter(lateral_offset_m).get_in(Distance.Foot)
    windage_rad = TrajectoryData.get_correction(D_ft, Z_ft)

    center_y_at_future = future_x * math.tan(math.radians(look_angle))
    vertical_offset_m = future_y - center_y_at_future
    Y_ft = Distance.Meter(vertical_offset_m).get_in(Distance.Foot)
    elevation_rad = TrajectoryData.get_correction(D_ft, Y_ft)

    return (
        Angular.Radian(windage_rad),
        Angular.Radian(elevation_rad),
        TOF,
        (future_x, future_y, future_z),
        iteration + 1,
        converged,
    )


# --- Налаштування ---
MAKE_GIF = False
CENTER_LOOK_ANGLE = 45
TARGET_TYPE: Literal["circular", "elipsis", "crossing", "figure8", "zigzag", "spiral", "straight_crossing"] = "figure8"
USE_ACCELERATION = True
REACTION_TIME = 0.1
MAX_ITERATIONS = 10
CONVERGENCE_THRESHOLD = 0.001
TRACKING_MODE: Literal["OMNISCIENT", "REALISTIC", "MEASURED"] = "MEASURED"
TRACKING_HISTORY_LENGTH = 10
CYCLES_TO_RUN = 3
# SIGHT_FOV_X_DEG = 5.86
# SIGHT_FOV_Y_DEG = 4.69
SIGHT_FOV_X_DEG = 12.5
SIGHT_FOV_Y_DEG = 9.95

def main():
    if TARGET_TYPE == "circular":
        target = CircularTarget(radius=200, distance=700, angle_deg=CENTER_LOOK_ANGLE, speed=50)
        period = 2 * math.pi / target.omega
        total_time = period * CYCLES_TO_RUN
    elif TARGET_TYPE == "elipsis":
        target = EllipticalTarget(150, 250, distance=700, angle_deg=CENTER_LOOK_ANGLE, speed=50)
        period = 2 * math.pi / target.omega
        total_time = period * CYCLES_TO_RUN
    elif TARGET_TYPE == "crossing":
        target = CrossingZigzagTarget(400, 500, CENTER_LOOK_ANGLE, speed=50, period=2, 
                                    #   crossing_angle_deg=45, 
                                      crossing_angle_deg=90
                                      )
        period = target.period * 4
        total_time = period * CYCLES_TO_RUN
    elif TARGET_TYPE == "figure8":
        target = FigureEightTarget(width=200, height=150, distance=700, angle_deg=CENTER_LOOK_ANGLE, speed=30)
        period = 2 * math.pi / target.omega
        total_time = period * CYCLES_TO_RUN
    elif TARGET_TYPE == "zigzag":
        target = ZigzagTarget(amplitude=200, distance=700, angle_deg=CENTER_LOOK_ANGLE, speed=50, period=4)
        period = target.period
        total_time = period * CYCLES_TO_RUN
    elif TARGET_TYPE == "spiral":
        target = SpiralTarget(
            radius_start=100, radius_end=300, distance=700, angle_deg=CENTER_LOOK_ANGLE, speed=40, cycles=CYCLES_TO_RUN
        )
        total_time = target.total_angle / (target.speed / target.radius_end)
    elif TARGET_TYPE == "straight_crossing":
        # Той самий сценарій, що й у crossing_lead.py: висота цілі 500м, кут 45°,
        # 50 м/с строго перпендикулярно до лінії візування, без зигзагу.
        # Стартова позиція - як у "crossing" (z=-amplitude=-400). Кінець траєкторії -
        # дзеркально симетричний (z=+amplitude=400), один прохід через усю ширину.
        straight_amplitude = 400
        straight_speed = 50
        target = StraightCrossingTarget(
            height=500, angle_deg=CENTER_LOOK_ANGLE, speed=straight_speed, start_z=-straight_amplitude
        )
        total_time = (2 * straight_amplitude) / straight_speed

    center_y_screen = target.center_y * target.K / target.center_x if hasattr(target, "center_y") else 0

    num_frames = 400
    times = np.linspace(0, total_time, num_frames)
    tracker = TargetTracker(history_length=TRACKING_HISTORY_LENGTH, dt=total_time / num_frames)

    fig, ax = plt.subplots(figsize=(9, 6))

    # Заголовок
    title_line1 = [
        f"Lead Calculation - {TARGET_TYPE.upper()}",
        f"Mode: {TRACKING_MODE}",
    ]
    title_line2 = [
        f"Accel: {'ON' if USE_ACCELERATION else 'OFF'}",
        f"Reaction: {REACTION_TIME * 1000:.0f}ms" if REACTION_TIME > 0 else "",
        f"Projection angle: {CENTER_LOOK_ANGLE:.0f}deg",
    ]
    title_line3 = [f"Sight FOV {SIGHT_FOV_X_DEG:.2f}° x {SIGHT_FOV_Y_DEG:.2f}°"]
    title = "\n".join(" | ".join(filter(None, line)) for line in (title_line1, title_line2, title_line3))
    ax.set_title(title, fontsize=10)

    ax.set_xlabel("Horizontal (Z_screen)")
    ax.set_ylabel("Vertical (Y_screen)")
    ax.set_xlim(*PLOT_XLIM)
    ax.set_ylim(*PLOT_YLIM)
    ax.set_aspect("equal")
    ax.grid(True)

    # Лінії перехрестя
    ax.axvline(x=0, color="r", linestyle=":", linewidth=1, alpha=0.5)
    ax.axhline(y=center_y_screen, color="r", linestyle=":", linewidth=1, alpha=0.5)

    # Поле зору прицілу (SightFOV) - прямокутник навколо LEAD POINT + промені від
    # спостерігача (0,0) до кутів прямокутника, область між ними зафарбована.
    sight_fov = SightFOV(SIGHT_FOV_X_DEG, SIGHT_FOV_Y_DEG)
    fov_fill = Polygon(
        [(0, 0)], closed=True, facecolor="gold", alpha=0.2, edgecolor="orange", linewidth=1, zorder=1, label="Sight FOV"
    )
    ax.add_patch(fov_fill)
    fov_box = Polygon(
        [(0, 0)], closed=True, facecolor="gold", alpha=0.65, edgecolor="orange", linewidth=1.5, zorder=1.5
    )
    ax.add_patch(fov_box)
    (fov_rays,) = ax.plot([], [], color="orange", lw=1, alpha=0.7, zorder=2)

    # --- Графічні об'єкти ---
    (target_point,) = ax.plot([], [], "ro", markersize=8, label="Target")
    (trajectory_line,) = ax.plot([], [], "b--", lw=1, alpha=0.5, label="Trajectory")
    (position_vector,) = ax.plot([], [], ":", color="gray", lw=1.5)
    (lead_vector,) = ax.plot([], [], ":", color="purple", lw=1.5, alpha=0.7)
    (velocity_line,) = ax.plot([], [], "g-", lw=2, label="Velocity")
    velocity_head = ax.annotate(
        "", xy=(0, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="green", lw=2, shrinkA=0, shrinkB=0)
    )

    # Точки упередження та майбутньої позиції
    (lead_point,) = ax.plot([], [], "mo", markersize=10, label="Lead Point", markerfacecolor="none", markeredgewidth=2)
    (lead_line,) = ax.plot([], [], "m--", lw=1.5, alpha=0.7)
    (future_point,) = ax.plot([], [], "o", color="magenta", markersize=8, label="Future (TOF)")

    # Текстова інформація
    speed_text = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", fc="white", alpha=0.6),
    )

    ax.legend(loc="upper right")

    # Історія позицій
    projected_z_history = []
    projected_y_history = []
    SCALE_V = 1

    def init():
        target_point.set_data([], [])
        trajectory_line.set_data([], [])
        position_vector.set_data([], [])
        lead_vector.set_data([], [])
        velocity_line.set_data([], [])
        velocity_head.xy = (0, 0)
        velocity_head.set_position((0, 0))
        lead_point.set_data([], [])
        lead_line.set_data([], [])
        future_point.set_data([], [])
        fov_fill.set_xy([(0, 0)])
        fov_box.set_xy([(0, 0)])
        fov_rays.set_data([], [])
        speed_text.set_text("")
        projected_z_history.clear()
        projected_y_history.clear()
        tracker.history.clear()
        return (
            target_point,
            trajectory_line,
            position_vector,
            lead_vector,
            velocity_line,
            velocity_head,
            speed_text,
            lead_point,
            lead_line,
            future_point,
            fov_fill,
            fov_box,
            fov_rays,
        )

    def update(frame):
        t = times[frame]
        pos = target.projected_position(t)
        dz, dy, vx, vy, vz, V_scalar = target.projected_velocity(t)
        x3d, y3d, z3d = target.position(t)
        distance = math.sqrt(x3d**2 + y3d**2 + z3d**2)

        tracker.update(t, x3d, y3d, z3d)

        if TRACKING_MODE == "REALISTIC":
            windage, elevation, TOF, future_pos, iterations, converged = calculate_angular_lead_realistic(
                zero, tracker, t, MAX_ITERATIONS, CONVERGENCE_THRESHOLD, USE_ACCELERATION, REACTION_TIME
            )
        elif TRACKING_MODE == "MEASURED":
            windage, elevation, TOF, future_pos, iterations, converged = calculate_angular_lead_realistic_measured(
                zero, tracker, REACTION_TIME
            )
        else:
            windage, elevation, TOF, future_pos, iterations, converged = calculate_angular_lead_iterative(
                zero, target, t, MAX_ITERATIONS, CONVERGENCE_THRESHOLD, USE_ACCELERATION, REACTION_TIME
            )

        look_angle = math.degrees(math.atan2(y3d, x3d))

        if future_pos is None:
            future_x, future_y, future_z = x3d, y3d, z3d
        else:
            future_x, future_y, future_z = future_pos

        if pos:
            z, y = pos
            target_point.set_data([z], [y])
            projected_z_history.append(z)
            projected_y_history.append(y)
            trajectory_line.set_data(projected_z_history, projected_y_history)
            position_vector.set_data([0, z], [0, y])

            z2 = z + dz * SCALE_V
            y2 = y + dy * SCALE_V
            velocity_line.set_data([z, z2], [y, y2])
            velocity_head.xy = (z2, y2)
            velocity_head.set_position((z, y))

            # Lead point (упередження на основі прогнозу)
            lead_proj = target.project_3d_point(future_x, future_y, future_z)
            if lead_proj:
                lead_z, lead_y = lead_proj
                lead_point.set_data([lead_z], [lead_y])
                lead_line.set_data([z, lead_z], [y, lead_y])
                lead_vector.set_data([0, lead_z], [0, lead_y])

                # SightFOV: 2 промені від спостерігача (0,0) до кутів прямокутника з
                # максимальним кутовим розкидом навколо LEAD POINT, і залита область між
                # ними, продовжена до краю графіка
                future_slant_distance = math.sqrt(future_x**2 + future_y**2 + future_z**2)
                fov_corners = sight_fov.rectangle_corners(target.K, future_x, future_slant_distance, lead_z, lead_y)
                c_min, c_max = sight_fov.extreme_rays(target.K, future_x, future_slant_distance, lead_z, lead_y)
                e_min = extend_ray_to_bounds(*c_min)
                e_max = extend_ray_to_bounds(*c_max)
                fov_fill.set_xy([(0, 0), e_min, e_max])
                fov_box.set_xy(fov_corners)
                fov_rays.set_data([0, e_min[0], math.nan, 0, e_max[0]], [0, e_min[1], math.nan, 0, e_max[1]])
            else:
                lead_point.set_data([], [])
                lead_line.set_data([], [])
                lead_vector.set_data([], [])
                fov_fill.set_xy([(0, 0)])
                fov_box.set_xy([(0, 0)])
                fov_rays.set_data([], [])

            # Реальна майбутня позиція через TOF
            actual_future_pos = target.position(t + TOF)
            future_proj = target.project_3d_point(*actual_future_pos)
            if future_proj:
                fz, fy = future_proj
                future_point.set_data([fz], [fy])
            else:
                future_point.set_data([], [])

            prediction_error = math.sqrt(
                (actual_future_pos[0] - future_x) ** 2
                + (actual_future_pos[1] - future_y) ** 2
                + (actual_future_pos[2] - future_z) ** 2
            )

            convergence_status = "✓ CONVERGED" if converged else "✗ NOT CONVERGED"

            txt = (
                f"Mode: {TRACKING_MODE}\n"
                f"Position angle: {look_angle:.2f}°\n"
                f"Windage: {windage.get_in(Angular.Mil):.2f} mil\n"
                f"Elevation: {elevation.get_in(Angular.Mil):.2f} mil\n"
                f"Velocity: {V_scalar:.2f} m/s\n"
                f"Distance: {distance:.2f} m\n"
                f"TOF: {TOF:.3f} s\n"
                f"Iter: {iterations}/{MAX_ITERATIONS} {convergence_status}\n"
                f"Error: {prediction_error:.2f} m\n"
                f"History: {len(tracker.history)}"
            )
            speed_text.set_text(txt)

        else:
            target_point.set_data([], [])
            position_vector.set_data([], [])
            lead_vector.set_data([], [])
            velocity_line.set_data([], [])
            velocity_head.xy = (0, 0)
            velocity_head.set_position((0, 0))
            lead_point.set_data([], [])
            lead_line.set_data([], [])
            future_point.set_data([], [])
            fov_fill.set_xy([(0, 0)])
            fov_box.set_xy([(0, 0)])
            fov_rays.set_data([], [])
            speed_text.set_text("Target not visible")

        return (
            target_point,
            trajectory_line,
            position_vector,
            lead_vector,
            velocity_line,
            velocity_head,
            speed_text,
            lead_point,
            lead_line,
            future_point,  # <- додали сюди
            fov_fill,
            fov_box,
            fov_rays,
        )

    ani = FuncAnimation(fig, update, frames=num_frames, init_func=init, blit=True, interval=20)
    if MAKE_GIF:
        ani.save(f"{TARGET_TYPE}.gif", writer="pillow")
    plt.show()


if __name__ == "__main__":
    import argparse

    # --- Аргументи командного рядка ---
    parser = argparse.ArgumentParser(description="Lead Calculation Simulation Settings")

    parser.add_argument("--make-gif", action="store_true", help="Generate GIF output")
    parser.add_argument(
        "-t",
        "--target-type",
        type=str,
        choices=["circular", "elipsis", "crossing", "figure8", "zigzag", "spiral", "straight_crossing"],
        default=TARGET_TYPE,
        help="Type of target motion",
    )
    # parser.add_argument("--use-acceleration", action="store_true", help="Consider acceleration in calculations")
    parser.add_argument(
        "--projection-angle",
        type=float,
        default=CENTER_LOOK_ANGLE,
        help="Center look angle in degree (perpendicular to sight line)",
    )
    parser.add_argument("--reaction-time", type=float, default=REACTION_TIME, help="Reaction time in seconds")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS, help="Max iterations for convergence")
    parser.add_argument(
        "--convergence-threshold",
        type=float,
        default=CONVERGENCE_THRESHOLD,
        help="Convergence threshold for iterative calculation",
    )
    parser.add_argument(
        "--tracking-mode",
        type=str,
        choices=["OMNISCIENT", "REALISTIC", "MEASURED"],
        default=TRACKING_MODE,
        help="Tracking mode",
    )
    parser.add_argument(
        "--tracking-history-length",
        type=int,
        default=TRACKING_HISTORY_LENGTH,
        help="Length of history used for tracking",
    )

    args = parser.parse_args()
    print(args)
    # --- Присвоєння змінних ---
    CENTER_LOOK_ANGLE = args.projection_angle
    MAKE_GIF = args.make_gif
    TARGET_TYPE = args.target_type
    # USE_ACCELERATION = args.use_acceleration
    REACTION_TIME = args.reaction_time
    MAX_ITERATIONS = args.max_iterations
    CONVERGENCE_THRESHOLD = args.convergence_threshold
    TRACKING_MODE = args.tracking_mode
    TRACKING_HISTORY_LENGTH = args.tracking_history_length
    main()
