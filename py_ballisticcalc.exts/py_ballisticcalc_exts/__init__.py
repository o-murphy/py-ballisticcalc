__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)",
)

__credits__ = ["o-murphy", "dbookstaber"]

import sys

from .bind import set_log_level
from .euler_engine import CythonizedEulerIntegrationEngine
from .rk4_engine import CythonizedRK4IntegrationEngine
from .test_engine import CythonEngineTestHarness


# Version matching guard
from importlib.metadata import metadata

try:
    CORE_PACKAGE_NAME = "py-ballisticcalc"
    EXTS_PACKAGE_NAME = "py-ballisticcalc-exts"
    __core_version = metadata(CORE_PACKAGE_NAME)["Version"]
    __exts_version = metadata(EXTS_PACKAGE_NAME)["Version"]
except KeyError:
    raise ImportError(f"Cannot read version from {CORE_PACKAGE_NAME} or {EXTS_PACKAGE_NAME} metadata.")

__PYTEST_DETECTED = "pytest" in sys.modules

if __core_version != __exts_version:
    raise AssertionError(
        f"Incompatible versions: {CORE_PACKAGE_NAME}@{__core_version} "
        f"is incompatible with {EXTS_PACKAGE_NAME}@{__exts_version}. "
        "Versions must match."
    )

if __PYTEST_DETECTED:
    from py_ballisticcalc.logger import logger

    logger.debug("pytest detected: setting C library log level to DEBUG")
    # During pytest runs, set C library log level to INFO for more verbose output
    set_log_level(10)  # LogLevel.DEBUG


__all__ = (
    "set_log_level",
    "CythonizedEulerIntegrationEngine",
    "CythonizedRK4IntegrationEngine",
    "CythonEngineTestHarness",
)
