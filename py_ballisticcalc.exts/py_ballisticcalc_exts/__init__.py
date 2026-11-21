"""The bclibc engines of py_ballisticcalc as Cython over the C ABI of bclibc (``bclibc_ffi.h``).

One extension module, ``_native`` (abi3 where the stable ABI is available), has the bclibc core and the C ABI wrapper
compiled into it: no shared library to load and no C++ API in Cython.

The names below are imported from ``_native`` on first access, so that the package itself imports without the main package.
:func:`check_versions` requires the main package to have the same version.
"""

__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)",
)

__credits__ = ["o-murphy", "dbookstaber"]

from importlib.metadata import PackageNotFoundError, metadata

CORE_PACKAGE_NAME = "py-ballisticcalc"
EXTS_PACKAGE_NAME = "py-ballisticcalc-exts"

_ENGINES = (
    "CythonizedEulerIntegrationEngine",
    "CythonizedRK4IntegrationEngine",
    "CythonizedVelocityVerletIntegrationEngine",
    "CythonizedCashKarpIntegrationEngine",
    "CythonizedDormandPrinceIntegrationEngine",
    "CythonizedTsitourasIntegrationEngine",
)
_BASES = ("CythonizedBaseIntegrationEngine", "CythonizedBaseTrajData", "CythonizedBaseTrajSeq")
__all__ = (*_ENGINES, *_BASES)


def __getattr__(name: str):
    if name in __all__:
        from . import _native

        return getattr(_native, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def check_versions(core_version: str, own_version: str) -> None:
    """The main package and this one are released together and must be the same version."""
    if core_version != own_version:
        raise AssertionError(
            f"Incompatible versions: {CORE_PACKAGE_NAME}@{core_version} "
            f"is incompatible with {EXTS_PACKAGE_NAME}@{own_version}. Versions must match."
        )


try:
    _core_version = metadata(CORE_PACKAGE_NAME)["Version"]
except PackageNotFoundError:
    _core_version = None
if _core_version is not None:
    try:
        check_versions(_core_version, metadata(EXTS_PACKAGE_NAME)["Version"])
    except PackageNotFoundError:  # run from a source tree, not installed
        pass
