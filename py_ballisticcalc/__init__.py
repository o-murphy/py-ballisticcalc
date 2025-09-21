"""LGPL library for small arms ballistic calculations."""

import importlib.metadata

__version__ = importlib.metadata.version("py_ballisticcalc")
__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)"
)

__credits__ = ["o-murphy", "dbookstaber"]

# Standard library imports
import importlib.resources
import os
import sys

# Third-party imports
from typing_extensions import Dict, Optional

# Local imports
from .logger import logger as log
from .unit import Unit, PreferredUnits

if sys.version_info[:2] < (3, 11):
    import tomli as tomllib
else:
    import tomllib


def _load_config(filepath: Optional[str] = None, suppress_warnings: bool = False) -> None:
    """Load configuration from a .pybc.toml file.
    
    Args:
        filepath: Path to configuration file. If None, searches for .pybc.toml or pybc.toml
        suppress_warnings: If True, suppress warning messages
    """
    def find_pybc_toml(start_dir: str = os.getcwd()) -> Optional[str]:
        """Search for the pyproject.toml file starting from the specified directory.
        
        Args:
            start_dir: The directory to start searching from. Default is the current working directory.
            
        Returns:
            The absolute path to the pyproject.toml file if found, otherwise None.
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
        log.debug(f"Found {os.path.basename(filepath)} at {os.path.dirname(filepath)}")

        with open(filepath, "rb") as fp:
            _config = tomllib.load(fp)

            if _pybc := _config.get('pybc'):
                if preferred_units := _pybc.get('preferred_units'):
                    PreferredUnits.set(**preferred_units)
                else:
                    if not suppress_warnings:
                        log.warning("Config has no `pybc.preferred_units` section")
            else:
                if not suppress_warnings:
                    log.warning("Config has no `pybc` section")

    log.debug("Calculator globals and PreferredUnits load success")


def _basic_config(filename: Optional[str] = None,
                  preferred_units: Optional[Dict[str, Unit]] = None, 
                  suppress_warnings: bool = False) -> None:
    """Load preferred units from file or Mapping.
    
    Args:
        filename: Configuration file path
        preferred_units: Dictionary of preferred units
        suppress_warnings: If True, suppress warning messages
        
    Raises:
        ValueError: If both filename and preferred_units are provided
    """
    if filename and preferred_units:
        raise ValueError("Can't use preferred_units and config file at same time")
    if not filename and preferred_units:
        PreferredUnits.set(**preferred_units)
    else:
        # trying to load definitions from pybc.toml
        _load_config(filename, suppress_warnings)


def _resolve_resource_path(path: str) -> str:
    """Resolve a resource path relative to the package.
    
    Args:
        path: Resource path relative to package
        
    Returns:
        Resolved path
    """
    return str(importlib.resources.files('py_ballisticcalc').joinpath(path))


def _load_imperial_units() -> None:
    """Load imperial unit preferences."""
    _basic_config(_resolve_resource_path('assets/.pybc-imperial.toml'), suppress_warnings=True)


def _load_metric_units() -> None:
    """Load metric unit preferences."""
    _basic_config(_resolve_resource_path('assets/.pybc-metrics.toml'), suppress_warnings=True)


def _load_mixed_units() -> None:
    """Load mixed unit preferences."""
    _basic_config(_resolve_resource_path('assets/.pybc-mixed.toml'), suppress_warnings=True)


loadImperialUnits = _load_imperial_units
loadMetricUnits = _load_metric_units
loadMixedUnits = _load_mixed_units

basicConfig = _basic_config

basicConfig()


from .conditions import Atmo, Vacuum, Wind, Shot, ShotProps
from .drag_model import DragModel, DragDataPoint, BCPoint, DragModelMultiBC
from .drag_tables import (TableG1, TableG7, TableG2, TableG5, TableG6, TableG8, 
                         TableGI, TableGS, TableRA4, get_drag_tables_names)
from .engines import (create_base_engine_config, BaseEngineConfig, BaseEngineConfigDict, 
                     BaseIntegrationEngine, EulerIntegrationEngine, RK4IntegrationEngine,
                     SciPyIntegrationEngine, VelocityVerletIntegrationEngine, SciPyEngineConfigDict)
from .exceptions import (UnitTypeError, UnitConversionError, UnitAliasError, 
                        SolverRuntimeError, OutOfRangeError, ZeroFindingError, RangeError)
from .interface import Calculator, _EngineLoader
from .interpolation import InterpolationMethod, InterpolationMethodEnum, interpolate_2_pt, interpolate_3_pt
from .logger import logger, enable_file_logging, disable_file_logging
from .munition import Weapon, Ammo, Sight, SightFocalPlane, SightClicks, SightReticleStep
from .trajectory_data import BaseTrajData, TrajectoryData, HitResult, DangerSpace, TrajFlag
from .unit import (Unit, counter, iterator, UnitAliases, Measurable, GenericDimension,
                  UnitProps, UnitPropsDict, Distance, Velocity, Angular, Temperature,
                  Pressure, Energy, Weight, Time, PreferredUnits)
from .vector import Vector

# DRY: build __all__ from global symbols
_SKIP_GLOBALS = {
    # Skip Python builtins
    "__name__", "__doc__", "__package__", "__loader__", "__spec__", 
    "__file__", "__cached__", "__builtins__",
    # Skip imported modules
    "tomllib", "sys", "os", "importlib",
    # Skip private/internal symbols
    "_load_config", "_basic_config", "_resolve_resource_path",
    "_load_imperial_units", "_load_metric_units", "_load_mixed_units"
}
# Build __all__ from the module's global namespace
__all__ = [
    name for name in globals()
    if not name.startswith("_") and name not in _SKIP_GLOBALS
]
# Add the public aliases for private functions
__all__.extend(["basicConfig", "loadImperialUnits", "loadMetricUnits", "loadMixedUnits"])
