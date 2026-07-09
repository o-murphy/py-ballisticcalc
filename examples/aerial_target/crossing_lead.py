# /// script
# dependencies = [
#   "py_ballisticcalc[exts]"
# ]
# ///

"""
Розрахунок кутового упередження (lead) методом ітеративної збіжності (convergence)
для цілі, що перетинає лінію візування - рух строго перпендикулярний до лінії
візування (класичний "crossing" постріл).

Вхідні умови:
  - кут візування (look angle):  45°
  - висота цілі:                 500 м
  - швидкість цілі:               50 м/с, рух перпендикулярно до лінії візування

Алгоритм (як в lead.py: calculate_angular_lead_iterative) на кожній ітерації:
  1. обчислює час польоту кулі (TOF) до поточної оцінки точки зустрічі;
  2. переносить ціль вперед на TOF (тут - лише вбік, бо рух суто перпендикулярний,
     дальність та висота не змінюються);
  3. перераховує TOF для нової дальності і повторює, поки TOF не перестане
     змінюватися (збіжність) або не буде вичерпано ліміт ітерацій.
"""

import copy
import math

from py_ballisticcalc import *

PreferredUnits.distance = Unit.Meter
PreferredUnits.adjustment = Unit.Mil
PreferredUnits.velocity = Unit.MPS

# --- Вхідні параметри цілі ---
LOOK_ANGLE_DEG = 45.0  # кут візування на ціль
TARGET_HEIGHT_M = 500.0  # висота цілі над рівнем стрільця
TARGET_SPEED_MPS = 50.0  # швидкість цілі, рух перпендикулярно до лінії візування

MAX_ITERATIONS = 10
CONVERGENCE_THRESHOLD = 0.001  # секунди, поріг збіжності TOF

calc = Calculator(engine="cythonized_rk4_engine")


def get_zero_shot() -> Shot:
    dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
    ammo = Ammo(dm, 850, Temperature.Celsius(15), use_powder_sensitivity=True)
    ammo.calc_powder_sens(820, Temperature.Celsius(0))
    weapon = Weapon(sight_height=9, twist=15)
    atmo = Atmo(altitude=Distance.Meter(1000), temperature=Unit.Celsius(5), humidity=0.5)
    return Shot(weapon=weapon, ammo=ammo, atmo=atmo)


def get_trajectory_at_distance(zero: Shot, slant_distance: float, look_angle: float) -> TrajectoryData:
    """
    Балістичні дані пострілу на задану похилу (slant) дальність під заданим кутом візування.

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


def calculate_crossing_lead(
    zero: Shot,
    look_angle_deg: float,
    target_height_m: float,
    target_speed_mps: float,
    max_iterations: int = MAX_ITERATIONS,
    convergence_threshold: float = CONVERGENCE_THRESHOLD,
):
    """
    Ітеративно шукає точку зустрічі кулі з ціллю, що рухається зі сталою
    швидкістю строго перпендикулярно до лінії візування (по осі Z).
    Дальність вздовж лінії візування (X) та висота (Y) при цьому не змінюються,
    міняється лише бічне зміщення (Z) - воно і дає бічне упередження (windage lead).
    """
    # X - дальність вздовж горизонталі, Y - висота цілі, Z - бічне зміщення (рух цілі)
    x = target_height_m / math.tan(math.radians(look_angle_deg))
    y = target_height_m
    z0 = 0.0

    initial_distance = math.sqrt(x**2 + y**2)
    TOF = get_trajectory_at_distance(zero, initial_distance, look_angle_deg).time

    converged = False
    iteration = 0
    for iteration in range(max_iterations):
        future_z = z0 + target_speed_mps * TOF
        future_distance = math.sqrt(x**2 + y**2 + future_z**2)

        hit_future = get_trajectory_at_distance(zero, future_distance, look_angle_deg)
        TOF_new = hit_future.time

        if abs(TOF_new - TOF) < convergence_threshold:
            converged = True
            TOF = TOF_new
            break

        TOF = TOF_new

    future_z = z0 + target_speed_mps * TOF
    future_distance = math.sqrt(x**2 + y**2 + future_z**2)

    D_ft = Distance.Meter(future_distance).get_in(Distance.Foot)
    Z_ft = Distance.Meter(future_z).get_in(Distance.Foot)
    windage_lead_rad = TrajectoryData.get_correction(D_ft, Z_ft)

    return {
        "initial_distance": initial_distance,
        "TOF": TOF,
        "future_distance": future_distance,
        "lateral_offset_m": future_z,
        "windage_lead": Angular.Radian(windage_lead_rad),
        "iterations": iteration + 1,
        "converged": converged,
    }


def main():
    zero = get_zero_shot()
    zero_distance = Distance.Meter(200)
    zero_elevation = calc.set_weapon_zero(zero, zero_distance)
    print(f"Перевірка нуля на {zero_distance}: {zero_elevation << Angular.Mil}")

    result = calculate_crossing_lead(
        zero,
        look_angle_deg=LOOK_ANGLE_DEG,
        target_height_m=TARGET_HEIGHT_M,
        target_speed_mps=TARGET_SPEED_MPS,
    )

    print("\n--- Вхідні дані ---")
    print(f"Кут візування:             {LOOK_ANGLE_DEG:.1f}°")
    print(f"Висота цілі:               {TARGET_HEIGHT_M:.1f} м")
    print(f"Початкова дальність:       {result['initial_distance']:.2f} м")
    print(f"Швидкість цілі:            {TARGET_SPEED_MPS:.1f} м/с (перпендикулярно до лінії візування)")

    print("\n--- Результат (ітеративна збіжність TOF) ---")
    print(f"Час польоту кулі (TOF):            {result['TOF']:.3f} с")
    print(f"Дальність у точці зустрічі:         {result['future_distance']:.2f} м")
    print(f"Бічне зміщення цілі за TOF:         {result['lateral_offset_m']:.2f} м")
    print(
        f"Упередження (windage lead):         {result['windage_lead'].get_in(Angular.Mil):.2f} mil "
        f"({result['windage_lead'].get_in(Angular.MOA):.2f} MOA)"
    )
    status = "збіглося" if result["converged"] else "НЕ збіглося"
    print(f"Ітерацій до збіжності:              {result['iterations']} ({status})")


if __name__ == "__main__":
    main()
