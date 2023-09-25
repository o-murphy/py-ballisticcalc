from dataclasses import dataclass, field

import pyximport


pyximport.install(language_level=3)

from .trajectory_data import TrajectoryData
from .trajectory_calc import TrajectoryCalc
from .conditions import *
from .munition import *
from .unit import *
from .drag_model import *
from .drag_tables import *
from .settings import *


assert DefaultUnits
assert DragModel
assert TableG1


@dataclass
class Calculator:
    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo

    _elevation: Angular = field(init=False, repr=True, compare=False)
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False)

    def __post_init__(self):
        self._calc = TrajectoryCalc()

    def update_elevation(self):
        self._elevation = self._calc.sight_angle(self.ammo, self.weapon, self.zero_atmo)

    def trajectory(self, shot: Shot, atmo: Atmo, winds: list[Wind], as_pandas: bool = False):
        if not self._elevation:
            self.update_elevation()
        Shot.sight_angle = self._elevation
        data = self._calc.trajectory(self.ammo, self.weapon, atmo, shot, winds)
        if as_pandas:
            return self._to_dataframe(data)
        return data

    @staticmethod
    def _to_dataframe(data: list[TrajectoryData]):
        """
        Imorting pd localy
        Note: reimplement this method if needed
        """

        try:
            import pandas as pd
        except ImportError as error:
            raise ImportError(f"{error}, use trajectory with as_pandas=False or install 'pandas' library")

        table = [p.in_def_units() for p in data]
