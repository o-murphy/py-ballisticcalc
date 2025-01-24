import bisect
import math
from typing import Callable, Any, Final, List

from py_ballisticcalc import HitResult, TrajFlag, TrajectoryData, Velocity, Distance, AbstractDimension

EARTH_GRAVITY_CONSTANT_IN_SI: Final[float] = 9.81 # Acceleration due to gravity (m/s^2)

def calculate_drag_free_range(
    velocity_in_mps: float, angle_in_degrees: float, gravity: float = EARTH_GRAVITY_CONSTANT_IN_SI
)->float:
    """Compute the maximal range for the projectile launched with `velocity_mps` with angle `angle_in_degrees`.
       The result assumes absence of drag force - so this distance will definitely overestimate (ca 4 times)
       the range in presence of drag force.
    """
    angle_rad = math.radians(angle_in_degrees)
    return (velocity_in_mps ** 2 * math.sin(2 * angle_rad)) / gravity


def find_first_index_matching_condition(
    shot: HitResult, condition: Callable[[TrajectoryData], bool]
) -> int:
    """Search sequentially for the index of first point in the trajectory, which matches condition.
       Returns:
            Index of the first point, matching condition, and 1 if no such point was found.
    """
    for i, e in enumerate(shot.trajectory):
        if condition(e):
            return i
    return -1

def find_index_of_point_with_flag(shot: HitResult, flag:int=TrajFlag.ZERO_DOWN)->int:
    """Find index of first point, for which `flag` is set.
       Returns:
            Index of first point with TrajFlag.ZERO_DOWN `.
            -1 if no such point was found.
     """
    return find_first_index_matching_condition(shot, lambda p: p.flag & flag)

def find_mach_point_index(shot: HitResult)->int:
    """Find index of point for which TrjFlag.MACH was set.
       Note - this requires calling calculator with extra_data=True.
       Returns:
            Index of first point with TrajFlag.ZERO_DOWN `.
            -1 if no such point was found.
    """
    return find_index_of_point_with_flag(shot, TrajFlag.MACH)

def find_touch_point_index(shot: HitResult)->int:
    """Find index of point when earth was hit by the bullet.
       Note - this requires calling calculator with extra_data=True.
       Returns:
            Index of first point with TrajFlag.ZERO_DOWN `.
            -1 if no such point was found.
    """
    return find_index_of_point_with_flag(shot, TrajFlag.ZERO_DOWN)

def find_velocity_less_than_index(
    shot: HitResult, velocity_in_units: float, velocity_unit=Velocity.MPS
)->int:
    """Find index of point where velocity became less than provided velocity.
       Note - this requires calling calculator with extra_data=True.
       Returns:
            Index of first point with velocity less  than `velocity_in_units`.
            -1  if no such point was found.
    """
    return find_first_index_matching_condition(
        shot, lambda p: (p.velocity >> velocity_unit) < velocity_in_units
    )

class BisectWrapper:
    """Wrapper for usage with bisect_for_condition."""
    def __init__(self, array: List, callable: Callable)->None:
        self.array = array
        self.callable = callable

    def __getitem__(self, index:int)->Any:
        return self.callable(self.array[index])

    def check_condition(self, index:int)->bool:
        return self.callable(self.array[index])

    def __len__(self)->int:
        return len(self.array)


def bisect_for_monotonic_condition(arr: List, wrapper: BisectWrapper)->int:
    """ Perform search in the ordered array for the first point, satisfying monotonic condition.

        Monotonic condition is a condition, which is consistently increases or decreases.
        For a bisection algorithm, a monotonic condition means the function maintains a consistent direction:
        Monotonically increasing: Each subsequent value is greater than or equal to the previous
        Monotonically decreasing: Each subsequent value is less than or equal to the previous
        WARNING: if condition for which you are searching is not monotonic, use
        `find_first_index_matching_condition`.
    """
    idx = bisect.bisect_left(wrapper, True, 0, len(arr))
    if idx >= len(arr):
        return -1
    if wrapper.check_condition(idx):
        return idx
    return -1

def find_first_index_satisfying_monotonic_condition(
    arr: List[TrajectoryData], monotonic_condition: Callable[[Any], bool]
)->int:
    # Find the index where the condition first becomes true
    # Uses bisect to find the first index satisfying the condition.
    return bisect_for_monotonic_condition(arr, BisectWrapper(arr, monotonic_condition))




def find_nearest_index_satisfying_monotonic_condition(arr: List[TrajectoryData], target_value:float,
                                                      value_getter: Callable[[TrajectoryData],float]):
    """
    Finds the index of the object with the nearest value to the target value.
    This performs bisect search for target value, and then compares differences from target value
    to previous and next index, and select index with the smallest difference.
    In case of tie, the smaller index is returned.
    Args:
        arr: The sorted array of trajectory data (always true for time, and almost always
               true for distances (except for extreme cases)).
        target_value: int or float - The target value to find the nearest object for.
        value_getter: function which returns the compared value

    Returns:
        The index of the object with the nearest target value. In case of tie, the smaller index is returned.

    """
    # Find the position where target_time would fit
    pos = bisect.bisect_left(BisectWrapper(arr, value_getter), target_value)

    # Compare neighbors to find the nearest index
    if pos == 0:
        return 0
    if pos == len(arr):
        return len(arr) - 1
    before = pos - 1
    after = pos
    if abs(value_getter(arr[before]) - target_value) <= abs(
        value_getter(arr[after]) - target_value
    ):
        return before
    return after


def find_index_of_point_for_distance(
    shot: HitResult, distance: float, distance_unit=Distance.Meter
)->int:
    """Find index of point, for which distance is bigger or equal to given `distance`.
       Returns:
            Index of point, where distance >= distance of point.
            -1 if no such point was found.
    """
    distance_is_bigger_or_equal = lambda p: (p.distance >> distance_unit) >= distance
    # return find_first_index_matching_condition(shot, distance_is_bigger_or_equal)
    return find_first_index_satisfying_monotonic_condition(
        shot.trajectory, distance_is_bigger_or_equal
    )


def find_index_for_time_point(
    shot: HitResult,
    time: float,
    strictly_bigger_or_equal: bool = True,
    max_time_deviation_in_seconds: float = 1,
) -> int:
    """Find index of time point with nearest time to provided `time`.
       If `strictly_bigger_or_equal` is set, then the first point with time equal to bigger than time is returned.
       Otherwise, the index with smaller deviation will be returned.
       Returns -1 if no such time point exists, or if points with existing time in shot.trajectory have deviation
       bigger than `max_time_deviation_in_seconds`.
    """
    if max_time_deviation_in_seconds < 0:
        raise ValueError(
            f"Max time deviation should be bigger then zero, but was {max_time_deviation_in_seconds}"
        )
    if time < 0:
        raise ValueError(f"Illegal searched time passed {time}")
    if strictly_bigger_or_equal:
        return find_first_index_satisfying_monotonic_condition(
            shot.trajectory, lambda e: e.time - time >= 0
        )
    else:
        index = find_nearest_index_satisfying_monotonic_condition(
            shot.trajectory, time, lambda e: e.time
        )
        if abs(shot.trajectory[index].time - time) <= max_time_deviation_in_seconds:
            return index
        return -1
    # This is original sequential code for search of index for time point

    # min_time_diff = None
    # min_index = -1
    # for i, e in enumerate(shot.trajectory):
    #     t_diff = abs(e.time - t)
    #     if min_time_diff is None or t_diff < min_time_diff:
    #         min_time_diff = t_diff
    #         min_index = i
    # if min_time_diff <= max_time_deviation_in_seconds:
    #     if strictly_bigger_or_equal:
    #         if shot.trajectory[min_index].time>=t:
    #             return min_index
    #         if min_index+1<len(shot.trajectory):
    #             if shot.trajectory[min_index+1].time>=t:
    #                 return min_index +1
    #         return -1
    #     return min_index
    # return -1


def find_index_of_apex_point(shot: HitResult) -> int:
    """Find index of the highest point in the trajectory.
      This method assumes that trajectory is uni-modal."""
    return find_index_of_apex_in_points(shot.trajectory)


def find_index_of_apex_in_points(trajectory_points: List)->int:
    """
    Finds the index of the apex in the uni-modal trajectory.
    :param trajectory_points: The array of objects with a 'height' field, where the height increases
    up to the apex and decreases thereafter.
    :return: int - The index of the apex, or -1 if no valid apex exists (this will happen only if
    trajectory_points is empty.
    """
    points_count = len(trajectory_points)
    if points_count == 0:
        return -1
    left, right = 0, points_count - 1
    while left < right:
        mid = (left + right) // 2
        # Compare mid and mid+1 to decide which side to search
        if trajectory_points[mid].height < trajectory_points[mid + 1].height:
            # Move right to the increasing side
            left = mid + 1
        else:
            # Move left to the decreasing side (possible apex)
            right = mid

    # Left and right converge to the apex
    return left

def find_time_for_distance_in_shot(
    shot: HitResult, distance_in_unit: float, distance_unit=Distance.Meter
) -> float:
    """Finds time corresponding to certain distance being reached in shot.
    Distance exceed maximal distance in shoot (i.e., no information is available),
    then float('NaN') is returned.
    """
    point_index = find_index_of_point_for_distance(
        shot, distance_in_unit, distance_unit
    )
    if point_index >= 0:
        return shot[point_index].time
    return float("NaN")

