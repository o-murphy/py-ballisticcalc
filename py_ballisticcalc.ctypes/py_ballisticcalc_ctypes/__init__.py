"""The bclibc engines of py_ballisticcalc through ctypes.

The package carries the ``bclibc_ffi`` shared library (``_native_lib/``), which setup.py builds from the bclibc
sources. Importing this module does not load it.

The engines are registered as the entry points ``ctypes+euler``, ``ctypes+rk4``, ``ctypes+verlet``, ``ctypes+rkck``,
``ctypes+dopri`` and ``ctypes+tsitouras`` (the Cython engines of ``py_ballisticcalc.exts`` are ``cython+<method>``, so both packages
can be installed) and are imported on first access of the ``Native<Method>IntegrationEngine`` names. :func:`check_versions` requires the
main package to have the same version.
"""

from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

CORE_PACKAGE_NAME = "py-ballisticcalc"
CTYPES_PACKAGE_NAME = "py-ballisticcalc-ctypes"

NATIVE_LIB_DIR = Path(__file__).with_name("_native_lib")

# The engine classes (what the entry points name) live in _native, which needs the main package: they are imported when asked
# for, so that the package itself, and the library path above, work without it.
_ENGINES = (
    "NativeEulerIntegrationEngine",
    "NativeRK4IntegrationEngine",
    "NativeVelocityVerletIntegrationEngine",
    "NativeCashKarpIntegrationEngine",
    "NativeDormandPrinceIntegrationEngine",
    "NativeTsitourasIntegrationEngine",
)
__all__ = ["NATIVE_LIB_DIR", "library_path", "check_versions", *_ENGINES]


def __getattr__(name: str):
    if name in _ENGINES:
        from . import _native

        return getattr(_native, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# libbclibc_ffi.so (Linux), libbclibc_ffi.dylib (macOS), bclibc_ffi.dll (Windows)
_LIB_PATTERNS = ("libbclibc_ffi.so", "libbclibc_ffi.dylib", "bclibc_ffi.dll")


def library_path() -> Path:
    """The bclibc_ffi library of this wheel; an absolute path, which is what ctypes.CDLL needs on every libc."""
    for name in _LIB_PATTERNS:
        candidate = NATIVE_LIB_DIR / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"the bclibc_ffi library is not in {NATIVE_LIB_DIR}")


def check_versions(core_version: str, own_version: str) -> None:
    """The main package and this one are released together and must be the same version
    (the `ctypes` extra pins it)."""
    if core_version != own_version:
        raise AssertionError(
            f"Incompatible versions: {CORE_PACKAGE_NAME}@{core_version} "
            f"is incompatible with {CTYPES_PACKAGE_NAME}@{own_version}. Versions must match."
        )


# Version matching guard, the same as in py_ballisticcalc_exts. Without the main package there is nothing to match.
try:
    _core_version = metadata(CORE_PACKAGE_NAME)["Version"]
except PackageNotFoundError:
    _core_version = None
if _core_version is not None:
    try:
        check_versions(_core_version, metadata(CTYPES_PACKAGE_NAME)["Version"])
    except PackageNotFoundError:  # run from a source tree, not installed
        pass
