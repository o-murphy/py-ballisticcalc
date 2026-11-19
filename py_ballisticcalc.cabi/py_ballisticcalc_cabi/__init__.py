"""The bclibc engines of py_ballisticcalc as Cython over the C ABI of bclibc (``bclibc_ffi.h``).

One abi3 extension module, ``_native``, has the bclibc core and the C ABI wrapper compiled into it: there is no shared library
to load (as in ``py_ballisticcalc.ctypes``) and no C++ API in Cython (as in ``py_ballisticcalc.exts``).

The engines are registered as the entry points ``cabi+euler``, ``cabi+rk4``, ``cabi+verlet``, ``cabi+rkck``, ``cabi+dopri`` and
``cabi+tsitouras`` and are imported on first access of the ``Native<Method>IntegrationEngine`` names, so that the package itself
imports without the main package. :func:`check_versions` requires the main package to have the same version.
"""

from importlib.metadata import PackageNotFoundError, metadata

CORE_PACKAGE_NAME = "py-ballisticcalc"
CABI_PACKAGE_NAME = "py-ballisticcalc-cabi"

_ENGINES = (
    "NativeEulerIntegrationEngine",
    "NativeRK4IntegrationEngine",
    "NativeVelocityVerletIntegrationEngine",
    "NativeCashKarpIntegrationEngine",
    "NativeDormandPrinceIntegrationEngine",
    "NativeTsitourasIntegrationEngine",
)
# the two public buffers of the C++ layer (py_ballisticcalc_exts.traj_data), under the same names
_BUFFERS = ("CythonizedBaseTrajSeq", "CythonizedBaseTrajData")
__all__ = ["check_versions", *_ENGINES, *_BUFFERS]


def __getattr__(name: str):
    if name in _ENGINES or name in _BUFFERS:
        from . import _native

        return getattr(_native, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def check_versions(core_version: str, own_version: str) -> None:
    """The main package and this one are released together and must be the same version."""
    if core_version != own_version:
        raise AssertionError(
            f"Incompatible versions: {CORE_PACKAGE_NAME}@{core_version} "
            f"is incompatible with {CABI_PACKAGE_NAME}@{own_version}. Versions must match."
        )


try:
    _core_version = metadata(CORE_PACKAGE_NAME)["Version"]
except PackageNotFoundError:
    _core_version = None
if _core_version is not None:
    try:
        check_versions(_core_version, metadata(CABI_PACKAGE_NAME)["Version"])
    except PackageNotFoundError:  # run from a source tree, not installed
        pass
