__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)"
)

__credits__ = ["o-murphy", "dbookstaber"]

from .euler_engine import CythonizedEulerIntegrationEngine
from .rk4_engine import CythonizedRK4IntegrationEngine
from .test_engine import CythonEngineTestHarness


# Version matching guard
from importlib.metadata import metadata
try:
    CORE_PACKAGE_NAME = 'py-ballisticcalc'
    EXTS_PACKAGE_NAME = 'py-ballisticcalc-exts'
    __core_version = metadata(CORE_PACKAGE_NAME)['Version']
    __exts_version = metadata(EXTS_PACKAGE_NAME)['Version']
except KeyError:
    raise ImportError(f"Cannot read version from {CORE_PACKAGE_NAME} or {EXTS_PACKAGE_NAME} metadata.")

if __core_version != __exts_version:
    raise AssertionError(
        f"Incompatible versions: {CORE_PACKAGE_NAME}@{__core_version} "
        f"is incompatible with {EXTS_PACKAGE_NAME}@{__exts_version}. "
        "Versions must match."
    )


__all__ = (
    'CythonizedEulerIntegrationEngine',
    'CythonizedRK4IntegrationEngine',
    'CythonEngineTestHarness',
)
