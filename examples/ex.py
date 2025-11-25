import matplotlib.pyplot as plt
import copy, math
from py_ballisticcalc import *

# Standard .50BMG


PreferredUnits.drop = Unit.Centimeter
PreferredUnits.distance = Unit.Meter


def get_zero_shot():
    dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
    ammo = Ammo(dm, 850, Temperature.Celsius(15), use_powder_sensitivity=True)
    ammo.calc_powder_sens(820, Temperature.Celsius(0))
    weapon = Weapon(sight_height=9, twist=15)
    atmo = Atmo(altitude=Distance.Foot(1000), temperature=Unit.Celsius(5), humidity=0.5)
    return Shot(weapon=weapon, ammo=ammo, atmo=atmo)


def get_zero_elev(zero: Shot, distance):
    zero_distance = Distance.Meter(distance)
    zero_elevation = calc.set_weapon_zero(zero, zero_distance)
    print(f"Barrel elevation for {zero_distance} zero: {zero_elevation << PreferredUnits.adjustment}")
    print(
        f"Muzzle velocity at zero temperature {zero.atmo.temperature} is {zero.ammo.get_velocity_for_temp(zero.atmo.temperature) << PreferredUnits.velocity}"
    )


def get_adjusted_trajectory(zero, target_distance, look_angle):
    new_shot: Shot = copy.copy(zero)  # Copy the zero properties; NB: Not a deepcopy!
    new_shot.look_angle = Angular.Degree(look_angle)
    new_target_distance = Distance.Meter(target_distance)
    new_elevation = calc.barrel_elevation_for_target(shot=new_shot, target_distance=new_target_distance)
    horizontal = Distance(
        math.cos(new_shot.look_angle >> Angular.Radian) * new_target_distance.unit_value, new_target_distance.units
    )
    # print(
    #     f"To hit target at look-distance of {new_target_distance << PreferredUnits.distance}"
    #     f" sighted at a {new_shot.look_angle << PreferredUnits.angular} look-angle,"
    #     f" barrel elevation={new_elevation << PreferredUnits.adjustment}"
    #     f"\n\t(horizontal distance to this target is {horizontal})"
    # )

    # Firing solution:
    hold = Angular.Mil((new_elevation >> Angular.Mil) - (zero.weapon.zero_elevation >> Angular.Mil))
    # print(
    #     f"Current zero has barrel elevated {zero.weapon.zero_elevation << PreferredUnits.adjustment}"
    #     f" so hold for new shot is {hold << PreferredUnits.adjustment}"
    # )

    # Plot this shot
    new_shot.relative_angle = hold
    return calc.fire(
        new_shot,
        trajectory_range=Distance.Meter(new_target_distance + 50),
        trajectory_step=Distance.Meter(10),
        flags=TrajFlag.ALL,
    )


def get_adjusted_last(zero: Shot, target_distance, look_angle):
    new_shot: Shot = copy.copy(zero)  # Copy the zero properties; NB: Not a deepcopy!
    new_shot.look_angle = Angular.Degree(look_angle)
    new_target_distance = Distance.Meter(target_distance)
    new_elevation = calc.barrel_elevation_for_target(shot=new_shot, target_distance=new_target_distance)
    # horizontal = Distance(
    #     math.cos(new_shot.look_angle >> Angular.Radian) * new_target_distance.unit_value, new_target_distance.units
    # )
    # print(
    #     f"To hit target at look-distance of {new_target_distance << PreferredUnits.distance}"
    #     f" sighted at a {new_shot.look_angle << PreferredUnits.angular} look-angle,"
    #     f" barrel elevation={new_elevation << PreferredUnits.adjustment}"
    #     f"\n\t(horizontal distance to this target is {horizontal})"
    # )

    # Firing solution:
    hold = Angular.Mil((new_elevation >> Angular.Mil) - (zero.weapon.zero_elevation >> Angular.Mil))
    # print(
    #     f"Current zero has barrel elevated {zero.weapon.zero_elevation << PreferredUnits.adjustment}"
    #     f" so hold for new shot is {hold << PreferredUnits.adjustment}"
    # )

    # Plot this shot
    new_shot.relative_angle = hold
    return calc.fire(
        new_shot,
        trajectory_range=new_target_distance,
        trajectory_step=new_target_distance,
        flags=TrajFlag.ALL,
    )


calc = Calculator(engine="cythonized_rk4_engine")
print(calc._engine_class)
zero = get_zero_shot()
get_zero_elev(zero, 200)

# hit = get_adjusted_trajectory(zero, 200, 0)
# ax = hit.plot()

# hit = get_adjusted_trajectory(zero, 400, 5)
# ax = hit.plot()

# hit = get_adjusted_trajectory(zero, 400, 10)
# ax = hit.plot()

# hit = get_adjusted_trajectory(zero, 400, 20)
# ax = hit.plot()

# # # Find danger space for a 4-meter tall target
# # danger_space = adjusted_result.danger_space(at_range=new_target_distance, target_height=Distance.Meter(2.2))
# # print(danger_space)
# # # Highlight danger space on the plot
# # danger_space.overlay(ax, f"Danger Space\n({danger_space.target_height << PreferredUnits.distance} Target)")
# plt.show()



# def get_sampled(zero):
#     import numpy as np
#     import matplotlib.pyplot as plt
#     from scipy.spatial import ConvexHull
#     # -----------------------------
#     # 1. Generate sampled data
#     # -----------------------------
#     distances = np.arange(100, 501, 20)  # 100..500 step 20
#     angles = np.arange(0, 51, 5)         # 0..50° step 5

#     points = []  # (distance, time)
#     i = 0
#     for d in distances:
#         for a in angles:
#             traj = get_adjusted_trajectory(zero, d, a)
#             last = traj[-1]  # last trajectory point
#             t = last.time    # <-- flight time
#             points.append([d, t])

#     points = np.array(points)

#     # -----------------------------
#     # 2. Compute convex hull
#     # -----------------------------
#     hull = ConvexHull(points)

#     # -----------------------------
#     # 3. Plot hull + point cloud
#     # -----------------------------
#     plt.figure(figsize=(10, 6))

#     # scatter all points
#     plt.scatter(points[:, 0], points[:, 1], s=15, alpha=0.4, label="Samples")

#     # draw hull edges
#     for simplex in hull.simplices:
#         x = points[simplex, 0]
#         y = points[simplex, 1]
#         plt.plot(x, y, "r-")

#     plt.xlabel("Horizontal distance [m]")
#     plt.ylabel("Flight time [s]")
#     plt.title("Convex Hull of (distance, time)")
#     plt.grid(True)
#     plt.legend()
#     plt.show()

# def get_sampled(zero):
#     import numpy as np
#     import matplotlib.pyplot as plt
#     from scipy.spatial import ConvexHull
#     import math

#     los_distances = np.arange(0, 1000, 5)  # LOS distances
#     angles = np.arange(0, 80, 1)             # degrees

#     points = []  # (horizontal_distance, time)

#     print("sampling", los_distances.size * angles.size)
#     for d_los in los_distances:
#         for a_deg in angles:

#             # convert to radians
#             a = math.radians(a_deg)

#             # compute horizontal distance
#             d_hor = d_los * math.cos(a)

#             # get trajectory using LOS distance (d_los) and angle (a_deg)
#             traj = get_adjusted_last(zero, d_los, a_deg)
#             last = traj[-1]
#             t = last.time

#             # add point to sample
#             points.append([d_hor, t])

#     points = np.array(points)

#     hull = ConvexHull(points)

#     plt.figure(figsize=(10, 6))
#     plt.scatter(points[:, 0], points[:, 1], s=15, alpha=0.4, label="Samples")

#     for simplex in hull.simplices:
#         plt.plot(points[simplex, 0], points[simplex, 1], "r-")

#     plt.xlabel("Horizontal distance [m]")
#     plt.ylabel("Flight time [s]")
#     plt.title("Convex Hull of (horizontal distance, time)")
#     plt.grid(True)
#     plt.legend()
#     plt.show()

# def get_sampled(zero):
#     import numpy as np
#     import matplotlib.pyplot as plt
#     from scipy.spatial import ConvexHull
#     import math

#     los_distances = np.arange(0, 1000, 10)
#     angles = np.arange(0, 80, 0.5)

#     points = []          # (horizontal_distance, time)
#     height_points = []   # (horizontal_distance, height, time)

#     print("sampling", los_distances.size * angles.size)

#     for d_los in los_distances:
#         for a_deg in angles:

#             a = math.radians(a_deg)
#             d_hor = d_los * math.cos(a)

#             traj = get_adjusted_last(zero, d_los, a_deg)
#             last = traj[-1]

#             t = last.time
#             z = last.z           # ВИСОТА останньої точки !!!

#             points.append([d_hor, t])
#             height_points.append([d_hor, z, t])

#     points = np.array(points)
#     height_points = np.array(height_points)

#     hull = ConvexHull(points)

#     # ---------- 1) CONVEX HULL на (distance, time) ----------
#     plt.figure(figsize=(10, 6))
#     plt.scatter(points[:, 0], points[:, 1], s=15, alpha=0.4, label="Samples")

#     for simplex in hull.simplices:
#         plt.plot(points[simplex, 0], points[simplex, 1], "r-")

#     plt.xlabel("Horizontal distance [m]")
#     plt.ylabel("Flight time [s]")
#     plt.title("Convex Hull of (horizontal distance, time)")
#     plt.grid(True)
#     plt.legend()
#     # plt.show()


#     # ---------- 2) SCATTER height vs distance with time gradient ----------
#     plt.figure(figsize=(10, 6))

#     sc = plt.scatter(
#         height_points[:, 0],        # x = distance
#         height_points[:, 1],        # y = height
#         c=height_points[:, 2],      # color = time
#         cmap="viridis",
#         s=15
#     )

#     plt.xlabel("Horizontal distance [m]")
#     plt.ylabel("Height [m]")
#     plt.title("Last trajectory points: height vs distance (colored by time)")
#     plt.grid(True)

#     # colorbar showing time
#     cbar = plt.colorbar(sc)
#     cbar.set_label("Flight time [s]")

#     plt.show()

def get_sampled(zero):
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull
    import math
    from time import perf_counter

    start = perf_counter()

    los_distances = np.arange(0, 800, 5)
    angles = np.arange(0, 90, 0.1)

    points = []          # (horizontal_distance, time)
    height_points = []   # (horizontal_distance, height, time)

    print("sampling", los_distances.size * angles.size)

    for d_los in los_distances:
        for a_deg in angles:

            a = math.radians(a_deg)
            d_hor = d_los * math.cos(a)

            traj: HitResult = get_adjusted_last(zero, d_hor, a_deg)
            last: TrajectoryData = traj[-1]

            d = last.distance.get_in(Distance.Meter)
            t = last.time
            ht = last.height.get_in(Distance.Meter)

            if d < d_hor:
                continue

            points.append([d, t])
            height_points.append([d, ht, t])

    points = np.array(points)
    height_points = np.array(height_points)

    # hull = ConvexHull(points)

    print("time", perf_counter() - start)


    # # ---------- 1) CONVEX HULL на (distance, time) ----------
    # plt.figure(figsize=(10, 6))
    # plt.scatter(points[:, 0], points[:, 1], s=15, alpha=0.4, label="Samples")

    # for simplex in hull.simplices:
    #     plt.plot(points[simplex, 0], points[simplex, 1], "r-")

    # plt.xlabel("Horizontal distance [m]")
    # plt.ylabel("Flight time [s]")
    # plt.title("Convex Hull of (horizontal distance, time)")
    # plt.grid(True)
    # plt.legend()
    # # plt.show()


    # ---------- 2) height vs distance (фільтруємо з > 200м) ----------
    mask = height_points[:, 1] <= 1000
    hp = height_points[mask]

    plt.figure(figsize=(10, 6))
    sc = plt.scatter(
        hp[:, 0],          # dist
        hp[:, 1],          # height
        c=hp[:, 2],        # time
        cmap="viridis",
        s=15
    )

    plt.xlabel("Horizontal distance [m]")
    plt.ylabel("Height [m]")
    plt.title("Last trajectory points: height vs distance (colored by time)")
    plt.grid(True)

    cbar = plt.colorbar(sc)
    cbar.set_label("Flight time [s]")

    plt.show()


get_sampled(zero)