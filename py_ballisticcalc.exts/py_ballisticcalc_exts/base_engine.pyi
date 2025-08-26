"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.base_engine`
to improve IDE completion for the Cythonized API.
"""

from typing import Any, Optional, Tuple

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag, ShotProps, BaseTrajData, TrajectoryData
from py_ballisticcalc.unit import Angular, Distance
from py_ballisticcalc.vector import Vector


class CythonizedBaseIntegrationEngine:
    def __cinit__(self, _config: Any) -> None: ...
    def __dealloc__(self) -> None: ...

    def get_calc_step(self) -> float: ...

    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[Distance, Angular]: ...
    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular: ...
    def find_apex(self, shot_info: Shot) -> TrajectoryData: ...
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular: ...
    def integrate(self,
                  shot_info: Shot,
                  max_range: Distance,
                  dist_step: Optional[Distance] = None,
                  time_step: float = 0.0,
                  filter_flags: "TrajFlag | int" = TrajFlag.NONE,
                  dense_output: bool = False,
                  **kwargs) -> HitResult: ...

    # Internal lifecycle / helpers exposed to Python callers (kept here for completeness)
    def _free_trajectory(self) -> None: ...
    def _init_trajectory(self, shot_info: ShotProps) -> None: ...


def create_trajectory_row(time: float,
                          range_vector: Vector,
                          velocity_vector: Vector,
                          mach: float,
                          shot_props: ShotProps,
                          density_ratio: float,
                          drag: float,
                          flag: int) -> TrajectoryData: ...
