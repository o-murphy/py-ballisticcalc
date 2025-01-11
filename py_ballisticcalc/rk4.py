# type: ignore

from typing import List

from py_ballisticcalc import TrajectoryCalc, Distance, Shot, TrajectoryData


class RK4TrajectoryCalc(TrajectoryCalc):

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False, time_step: float = 0.0) -> List[TrajectoryData]:
        # your rk4 implementation there
        ...
