"""LGPL library for small arms ballistic calculations (Python 3.9+)"""

__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)"
)

__credits__ = ["o-murphy", "dbookstaber"]

import importlib.resources
import os
import sys

from typing_extensions import Dict, Optional

from .conditions import *
from .drag_model import *
from .drag_tables import *
from .engines import *
from .exceptions import *
from .interface import *
from .logger import *
from .munition import *
from .trajectory_data import *
from .unit import *
from .vector import *

if sys.version_info[:2] < (3, 11):
    import tomli as tomllib
else:
    import tomllib


def _load_config(filepath=None, suppress_warnings=False):
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
                    if not suppress_warnings:
                        logger.warning("Config has no `pybc.preferred_units` section")
            else:
                if not suppress_warnings:
                    logger.warning("Config has no `pybc` section")

    logger.debug("Calculator globals and PreferredUnits load success")


def _basic_config(filename=None,
                  preferred_units: Optional[Dict[str, Unit]] = None, suppress_warnings=False):
    """
    Method to load preferred units from file or Mapping
    """
    if filename and preferred_units:
        raise ValueError("Can't use preferred_units and config file at same time")
    if not filename and preferred_units:
        PreferredUnits.set(**preferred_units)
    else:
        # trying to load definitions from pybc.toml
        _load_config(filename, suppress_warnings)


def _resolve_resource_path(path: str):
    return importlib.resources.files('py_ballisticcalc').joinpath(path)


def _load_imperial_units():
    _basic_config(_resolve_resource_path('assets/.pybc-imperial.toml'), suppress_warnings=True)


def _load_metric_units():
    _basic_config(_resolve_resource_path('assets/.pybc-metrics.toml'), suppress_warnings=True)


def _load_mixed_units():
    _basic_config(_resolve_resource_path('assets/.pybc-mixed.toml'), suppress_warnings=True)


loadImperialUnits = _load_imperial_units
loadMetricUnits = _load_metric_units
loadMixedUnits = _load_mixed_units

basicConfig = _basic_config

basicConfig()

# pylint: disable=duplicate-code
__all__ = [
    'Calculator',
    'basicConfig',
    'loadImperialUnits',
    'loadMetricUnits',
    'loadMixedUnits',
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'BaseIntegrationEngine',
    'EulerIntegrationEngine',
    'RK4IntegrationEngine',
    'Vector',
    'DragModel',
    'DragDataPoint',
    'BCPoint',
    'DragModelMultiBC',
    'TrajectoryData',
    'HitResult',
    'DangerSpace',
    'TrajFlag',
    'Atmo',
    'Vacuum',
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
    'GenericDimension',
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
    'logger',
    'enable_file_logging',
    'disable_file_logging',
    'get_debug',
    'set_debug',
]

# __all__ += ["TableG%s" % n for n in (1, 7, 2, 5, 6, 8, 'I', 'S', 'RA4')]
__all__ += [
    'TableG1',
    'TableG7',
    'TableG2',
    'TableG5',
    'TableG6',
    'TableG8',
    'TableGI',
    'TableGS',
    'TableRA4',
]
