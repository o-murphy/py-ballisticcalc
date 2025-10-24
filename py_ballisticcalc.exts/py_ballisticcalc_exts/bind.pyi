# py_ballisticcalc_exts/bclib_ext.pyi (Example name for this file)

# --- Imports for Type Hinting ---

# Import types that are used as arguments or return values

# Re-export of C types/enums used in public interfaces (for type checkers)
# NOTE: These C types (MachList_t, Config_t, etc.) are opaque objects in Python,
# but we define them here for completeness.

class LogLevel:
    """Equivalent to the C enum LogLevel."""

    LOG_LEVEL_CRITICAL: int = 50
    LOG_LEVEL_ERROR: int = 40
    LOG_LEVEL_WARNING: int = 30
    LOG_LEVEL_INFO: int = 20
    LOG_LEVEL_DEBUG: int = 10
    LOG_LEVEL_NOTSET: int = 0

class MachList_t: ...
class Curve_t: ...
class Config_t: ...
class Wind_t: ...
class WindSock_t: ...
class Coriolis_t: ...
class V3dT: ...
class InterpKey: ...

# --- Public Python Functions ---

def initLogLevel() -> None:
    """
    Initializes the global log level, typically by checking environment variables.
    This function is called automatically upon module import in the .pyx file.
    """
    ...

def set_log_level(level: int) -> None:
    """
    Set the global log level for the C library.

    Args:
        level: The desired log level (e.g., LogLevel.LOG_LEVEL_DEBUG, which is 10).
    """
    ...

# --- Non-Public Cython-Only Helpers (Optional for .pyi) ---
# NOTE: The following cdef functions (Config_t_from_pyobject, _v3d_to_vector, etc.)
# are internal helpers and typically *not* included in the public .pyi file
# unless they are explicitly exposed via a 'def' function.

# If the module exposes a public API to create Config_t, it would look like this:
# def create_config(config_data: Any) -> Config_t: ...

# If the module exposes a public API to convert a V3dT to a Vector, it would look like this:
# def v3d_to_vector(v3d_struct: V3dT) -> Vector: ...
