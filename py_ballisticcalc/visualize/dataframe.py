# pylint: skip-file
import warnings

from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData

try:
    from pandas import DataFrame
except ImportError as error:
    warnings.warn("Install pandas to convert trajectory to pandas.DataFrame", UserWarning)
    raise error


def hit_result_as_dataframe(hit_result: HitResult, formatted: bool = False) -> DataFrame:  # type: ignore
    """
    :param hit_result: HitResult object
    :param formatted: False for values as floats; True for strings with prefer_units
    :return: the trajectory table as a DataFrame
    """
    col_names = list(TrajectoryData._fields)
    if formatted:
        trajectory = [p.formatted() for p in hit_result]
    else:
        trajectory = [p.in_def_units() for p in hit_result]
    return DataFrame(trajectory, columns=col_names)
