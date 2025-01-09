"""LGPL library for small arms ballistic calculations (Python 3.8+)"""

__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)"
)

__credits__ = ["o-murphy", "dbookstaber"]

import os
import sys
from typing_extensions import Dict, Union, Optional

from .trajectory_calc import *
from .conditions import *
from .drag_model import *
from .drag_tables import *
from .interface import *
from .logger import logger
from .munition import *
from .trajectory_data import *
from .unit import *
from .interface_config import *
from .exceptions import *

if sys.version_info[:2] < (3, 11):
    import tomli as tomllib
else:
    import tomllib


def _load_config(filepath=None):
    def find_pybc_toml(start_dir=os.getcwd()):
        """
        Search for the pyproject.toml file starting from the specified directory.
        :param start_dir: (str) The directory to start searching from. Default is the current working directory.
        :return: str: The absolute path to the pyproject.toml file if found, otherwise None.
        """
        current_dir = os.path.abspath(start_dir)
        while True:
            # Check if pybc.toml or .pybc.toml exists in the current directory
            pybc_paths = [
                os.path.join(current_dir, '.pybc.toml'),
                os.path.join(current_dir, 'pybc.toml'),
            ]
            for pypc_path in pybc_paths:
                if os.path.exists(pypc_path):
                    return os.path.abspath(pypc_path)

            # Move to the parent directory
            parent_dir = os.path.dirname(current_dir)

            # If we have reached the root directory, stop searching
            if parent_dir == current_dir:
                return None

            current_dir = parent_dir

    if filepath is None:
        if (filepath := find_pybc_toml()) is None:
            filepath = find_pybc_toml(os.path.dirname(__file__))

    if filepath is not None:
        logger.debug(f"Found {os.path.basename(filepath)} at {os.path.dirname(filepath)}")

        with open(filepath, "rb") as fp:
            _config = tomllib.load(fp)

            if _pybc := _config.get('pybc'):
                if preferred_units := _pybc.get('preferred_units'):
                    PreferredUnits.set(**preferred_units)
                else:
                    logger.warning("Config has not `pybc.preferred_units` section")

                if calculator := _pybc.get('calculator'):
                    if max_calc_step_size := calculator.get('max_calc_step_size'):
                        try:
                            _val = max_calc_step_size.get("value")
                            _units = Unit[max_calc_step_size.get("units")]
                            set_global_max_calc_step_size(_units(_val))
                        except (KeyError, TypeError, ValueError):
                            logger.warning("Wrong max_calc_step_size units or value")

                    if use_powder_sensitivity := calculator.get('use_powder_sensitivity'):
                        set_global_use_powder_sensitivity(use_powder_sensitivity)
                else:
                    logger.warning("Config has not `pybc.calculator` section")
            else:
                logger.warning("Config has not `pybc` section")

    logger.debug("Calculator globals and PreferredUnits load success")


def _basic_config(filename=None,
                  max_calc_step_size: Optional[Union[float, Distance]] = None,
                  use_powder_sensitivity: bool = False,
                  preferred_units: Optional[Dict[str, Unit]] = None):
    """
    Method to load preferred units from file or Mapping
    """
    if filename and (preferred_units or max_calc_step_size or use_powder_sensitivity):
        raise ValueError("Can't use preferred_units and config file at same time")
    if not filename and (preferred_units or max_calc_step_size or use_powder_sensitivity):
        if preferred_units:
            PreferredUnits.set(**preferred_units)
        if max_calc_step_size:
            set_global_max_calc_step_size(max_calc_step_size)
        if use_powder_sensitivity:
            set_global_use_powder_sensitivity(use_powder_sensitivity)
    else:
        # trying to load definitions from pybc.toml
        _load_config(filename)


basicConfig = _basic_config

basicConfig()

# pylint: disable=duplicate-code
__all__ = [
    'Calculator',
    'basicConfig',
    'logger',
    'TrajectoryCalc',
    'Vector',
    "InterfaceConfigDict",
    'get_global_max_calc_step_size',
    'get_global_use_powder_sensitivity',
    'set_global_max_calc_step_size',
    'set_global_use_powder_sensitivity',
    'reset_globals',
    'DragModel',
    'DragDataPoint',
    'BCPoint',
    'DragModelMultiBC',
    'TrajectoryData',
    'HitResult',
    'DangerSpace',
    'TrajFlag',
    'Atmo',
    'Wind',
    'Shot',
    'Weapon',
    'Ammo',
    'Sight',
    'SightFocalPlane',
    'SightClicks',
    'SightReticleStep',
    'Unit',
    'UnitAliases',
    'AbstractDimension',
    'AbstractDimensionType',
    'UnitProps',
    'UnitPropsDict',
    'Distance',
    'Velocity',
    'Angular',
    'Temperature',
    'Pressure',
    'Energy',
    'Weight',
    'PreferredUnits',
    'get_drag_tables_names',
    'constants',
    'exceptions',
    'UnitAliasError',
    'UnitTypeError',
    'UnitConversionError',
    'ZeroFindingError',
    'RangeError',
]

# __all__ += ["TableG%s" % n for n in (1, 7, 2, 5, 6, 8, 'I', 'S')]
__all__ += [
    'TableG1',
    'TableG7',
    'TableG2',
    'TableG5',
    'TableG6',
    'TableG8',
    'TableGI',
    'TableGS'
]


try:
    # check if cython based extensions installed
    import py_ballisticcalc_exts  # type: ignore
    logger.debug("Binary modules found, running in binary mode")
except ImportError as error:
    import warnings
    warnings.warn("Library running in pure python mode. "
                  "For better performance install 'py_ballisticcalc.exts' binary package", UserWarning)
