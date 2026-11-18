# pyright: reportOptionalMemberAccess=false, reportInvalidTypeForm=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
# The library handle and the generated bindings module are set lazily (they start as None), and the
# annotations refer to names bound at load time. Typing this properly is a separate change; these rules are
# disabled for this file only, so the rest of the package is still checked.
"""ctypes engines over the bclibc C-ABI library.

The engines of py_ballisticcalc.exts with the same public surface, registered as ctypes+rk4, ... (the Cython ones are cython+rk4, ...);
the classes are named Native<Method>IntegrationEngine. Structs follow include/bclibc/ffi/bclibc_ffi.h.
The library is loaded lazily on first engine use.

Each engine owns one `_Scratch` (created on first use, after the library is loaded): the C structs and output
buffers are allocated once and reused by every call, the way the Cython engines keep `self._this`. A call only
assigns the fields that change; nothing per call is constructed except the Python result objects.
"""

import array
import ctypes as C
import math
import os
import struct
import threading
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine
from py_ballisticcalc.exceptions import (
    InterceptionError,
    OutOfRangeError,
    RangeError,
    SolverRuntimeError,
    ZeroFindingError,
)
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.trajectory_data import BaseTrajData, HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Energy, Unit, Velocity, Weight
from py_ballisticcalc.vector import Vector

# ---------------------------------------------------------------- generated bindings
# Structs, enums, constants and the BCLIBCFFI_* prototypes come from py_ballisticcalc_ctypes/_ctypesgen/_native_gen.py
# (ctypesgen over bclibc_ffi.h). Importing this module does not load the library: the generated module is
# imported by _load_library(), and its structs are reached through _T and _G from then on.

_G = None  # generated bindings module (set by _load_library)
_T = None  # namespace of generated struct types used here (set by _load_library)

# integration method enum values by engine name (BCLIBCFFI_IntegrationMethod)
_METHOD = {"rk4": 0, "euler": 1, "verlet": 2, "rkck": 3, "dopri": 4, "tsit": 5}

# termination reasons -> RangeError reason text, as in the Cython layer (BCLIBCFFI_TerminationReason values)
_TERMINATION = {
    1: None,  # target range reached
    2: RangeError.MinimumVelocityReached,
    3: RangeError.MaximumDropReached,
    4: RangeError.MinimumAltitudeReached,
}

# ---------------------------------------------------------------- library loading

_LIB = None
_LIB_NAME = "bclibc_ffi"  # ctypesgen library name: libbclibc_ffi.so / .dylib, bclibc_ffi.dll


def _library_dir() -> str:
    """Directory holding the native library.

    PY_BALLISTICCALC_NATIVE_LIB_DIR overrides the package default. On iOS the library is inside
    bclibc_ffi.framework/ (the loader then finds the framework binary named bclibc_ffi).
    """
    override = os.environ.get("PY_BALLISTICCALC_NATIVE_LIB_DIR")
    if override:
        return override
    base = Path(__file__).with_name("_native_lib")
    framework = base / "bclibc_ffi.framework"
    return str(framework if framework.is_dir() else base)


_LOAD_LOCK = threading.Lock()  # serialises the first load when several threads start engines at once


def _load_library():
    """Load the native library on first use and bind the generated prototypes."""
    if _LIB is not None:
        return _LIB
    with _LOAD_LOCK:
        return _load_library_locked()


def _check_library_version(G, lib):
    """The library and the generated bindings must come from the same bclibc major.minor (the C ABI changes there)."""
    import re

    built = re.search(r"of bclibc (\d+)\.(\d+)", G.__doc__ or "")
    found = re.match(r"(\d+)\.(\d+)", (G.BCLIBCFFI_get_version() or b"").decode())
    if built and found and built.groups() != found.groups():
        raise ImportError(
            f"bclibc_ffi library {'.'.join(found.groups())} does not match the bindings for bclibc "
            f"{'.'.join(built.groups())}: reinstall py_ballisticcalc.ctypes"
        )


def _load_library_locked():
    global _LIB, _G, _T
    if _LIB is not None:
        return _LIB
    from ._ctypesgen import ctypes_loader

    ctypes_loader.add_library_search_dirs([_library_dir()])
    from ._ctypesgen import _native_gen as G  # importing the generated module loads the library

    lib = G._libs[_LIB_NAME]
    _T = SimpleNamespace(
        Shot=G.BCLIBCFFI_Shot,
        Error=G.BCLIBCFFI_Error,
        Request=G.BCLIBCFFI_TrajectoryRequest,
        TrajData=G.BCLIBCFFI_TrajectoryData,
        BaseData=G.BCLIBCFFI_BaseTrajData,
        Config=G.BCLIBCFFI_Config,
        Wind=G.BCLIBCFFI_Wind,
        ZeroPointResult=G.BCLIBCFFI_ZeroPointResult,
        MaxRangeResult=G.BCLIBCFFI_MaxRangeResult,
        StepStats=G.BCLIBCFFI_StepStats,
        Interception=G.BCLIBCFFI_Interception,
    )
    _check_library_version(G, lib)
    if C.sizeof(_T.TrajData) != _TRAJ_FMT.size:  # the layout _traj reads
        raise RuntimeError(f"BCLIBCFFI_TrajectoryData is {C.sizeof(_T.TrajData)} bytes, expected {_TRAJ_FMT.size}")
    _G = G
    _LIB = lib
    return lib


# ---------------------------------------------------------------- preallocated call storage


class _Scratch:
    """Per-engine C storage, allocated once and reused by every call (the Cython engines' `self._this` members).

    Input: `shot` (with its config), `req`. Output: `recs`, `dense`, `n`, `dn`, `reason`, `err`, `stats`, and the
    result structs of the zero/apex/max-range/interception calls. Drag arrays and the wind array are reallocated only
    when their length changes; their contents are rewritten on each call.
    """

    def __init__(self):
        self.shot = _T.Shot()
        self.req = _T.Request()
        self.recs = C.POINTER(_T.TrajData)()
        self.dense = C.POINTER(_T.BaseData)()
        self.n = C.c_int32()
        self.dn = C.c_int32()
        self.reason = C.c_int32()
        self.err = _T.Error()
        self.stats = _T.StepStats()
        self.value = C.c_double()
        self.zp = _T.ZeroPointResult()
        self.mr = _T.MaxRangeResult()
        self.apex = _T.TrajData()
        self.it = _T.Interception()
        self.custom = None  # _Curve for a custom drag table, reallocated only when its length changes
        self.n_wind = -1
        self.wind_arr = None
        # the drag table of the previous call and the curve chosen for it: the same list object (with the same first and
        # last point objects and length) is checked against the curve by value (_same_curve), as a point may be edited in
        # place, which the Cython engines see because they read the table on every call
        self.table = None
        self.table_key = None
        self.table_curve = None


class _Curve:
    """A drag table as two double arrays: the Python-side storage (array.array, read and written by index) and the
    ctypes view over the same memory that the C shot points at. Built once; never copied per call."""

    __slots__ = ("c_store", "cd", "m_store", "mach", "n")

    def __init__(self, n: int):
        self.n = n
        self.m_store = array.array("d", [0.0]) * n
        self.c_store = array.array("d", [0.0]) * n
        self.mach = (C.c_double * n).from_buffer(self.m_store)
        self.cd = (C.c_double * n).from_buffer(self.c_store)


def _std_curve(table) -> "_Curve":
    """A standard table (dict points, as in py_ballisticcalc.drag_tables), stored once."""
    curve = _Curve(len(table))
    for i, point in enumerate(table):
        curve.m_store[i] = point["Mach"]
        curve.c_store[i] = point["CD"]
    return curve


# the standard G1 and G7 tables, built once: a drag model whose table has the same values is passed these arrays
_STD_G1 = _std_curve(TableG1)
_STD_G7 = _std_curve(TableG7)


def _same_curve(table, curve: "_Curve") -> bool:
    """True when the drag table's values equal the stored curve's. No allocation: a read-only pass over the points."""
    if len(table) != curve.n:
        return False
    ms, cs = curve.m_store, curve.c_store
    for i, point in enumerate(table):
        if point.Mach != ms[i] or point.CD != cs[i]:
            return False
    return True


def _custom_curve(scr: "_Scratch", table, n: int) -> "_Curve":
    """The custom drag table in the scratch storage. Reallocated only when the length changes; otherwise only the
    points whose values changed are written."""
    if scr.custom is None or scr.custom.n != n:
        scr.custom = _Curve(n)
        curve = scr.custom
        for i, point in enumerate(table):
            curve.m_store[i] = point.Mach
            curve.c_store[i] = point.CD
        return curve
    curve = scr.custom
    ms, cs = curve.m_store, curve.c_store
    for i, point in enumerate(table):
        if point.Mach != ms[i]:
            ms[i] = point.Mach
        if point.CD != cs[i]:
            cs[i] = point.CD
    return curve


def _scratch_of(engine) -> _Scratch:
    """The engine's scratch storage, created on first use (the library must be loaded already)."""
    scr = engine.__dict__.get("_scratch")
    if scr is None:
        scr = engine.__dict__["_scratch"] = _Scratch()
    return scr


def _fill_shot(scr: _Scratch, shot_info, cfg, method: int) -> None:
    """BCLIBC_ShotProps_from_pyobject: writes the same fields in the same order into scr.shot, in place.

    The drag table is written element by element into the typed arrays on every call, as the Cython loop fills its
    vectors; the arrays themselves are only (re)allocated when the table length changes.
    """
    ammo = shot_info.ammo
    dm = ammo.dm
    atmo = shot_info.atmo
    weapon = shot_info.weapon
    table = dm.drag_table
    n = len(table)
    # standard G1/G7 tables: the stored arrays, no copy; any other table: the scratch copy, written where it changed
    key = (n, table[0], table[-1]) if n else None
    if table is scr.table and key == scr.table_key and _same_curve(table, scr.table_curve):
        curve = scr.table_curve
    else:
        if _same_curve(table, _STD_G7):
            curve = _STD_G7
        elif _same_curve(table, _STD_G1):
            curve = _STD_G1
        else:
            curve = _custom_curve(scr, table, n)
        scr.table, scr.table_key, scr.table_curve = table, key, curve

    winds = tuple(shot_info.winds)
    nw = len(winds)
    s = scr.shot
    if nw != scr.n_wind:
        scr.wind_arr = (_T.Wind * nw)() if nw else None
        scr.n_wind = nw
        s.winds = C.cast(scr.wind_arr, C.POINTER(_T.Wind)) if nw else None
    for i, w in enumerate(winds):
        wa = scr.wind_arr[i]
        wa.velocity_fps = w.velocity._fps
        wa.direction_from_rad = w.direction_from._rad
        wa.until_distance_ft = w.until_distance._feet
        wa.max_distance_ft = w.MAX_DISTANCE_FEET

    s.bc = dm.BC
    s.weight_grain = dm.weight._grain
    s.diameter_inch = dm.diameter._inch
    s.length_inch = dm.length._inch
    s.muzzle_velocity_fps = ammo.get_velocity_for_temp(atmo.powder_temp)._fps
    s.sight_height_ft = weapon.sight_height._feet
    s.twist_inch = weapon.twist._inch
    s.temp_c = atmo._t0
    s.pressure_hpa = atmo._p0
    s.altitude_ft = atmo._a0
    s.humidity = atmo.humidity
    s.mach_data = curve.mach
    s.cd_data = curve.cd
    s.drag_table_size = n
    s.wind_count = nw
    s.look_angle_rad = shot_info.look_angle._rad
    s.barrel_elevation_rad = shot_info.barrel_elevation._rad
    s.barrel_azimuth_rad = shot_info.barrel_azimuth._rad
    s.cant_angle_rad = shot_info.cant_angle._rad
    s.latitude_deg = math.nan if shot_info.latitude is None else shot_info.latitude
    s.azimuth_deg = math.nan if shot_info.azimuth is None else shot_info.azimuth
    c = s.config
    c.cStepMultiplier = cfg.cStepMultiplier
    c.cZeroFindingAccuracy = cfg.cZeroFindingAccuracy
    c.cMinimumVelocity = cfg.cMinimumVelocity
    c.cMaximumDrop = cfg.cMaximumDrop
    c.cMaxIterations = int(cfg.cMaxIterations)
    c.cGravityConstant = cfg.cGravityConstant
    c.cMinimumAltitude = cfg.cMinimumAltitude
    s.method = method


# BCLIBCFFI_TrajectoryData: 15 doubles and the int32 flag, read in one call instead of one ctypes descriptor access per
# field. The tail padding is the C compiler's: "0d" pads to the alignment of a double like the structure does, so it is
# 4 bytes where a double is aligned to 8 (128 bytes in all) and none on 32-bit x86 Linux, where it is aligned to 4 (124).
_TRAJ_FMT = struct.Struct("15di0d")


_tuple_new = tuple.__new__
_obj_new = object.__new__
_FOOT, _FPS, _RAD, _FTLB, _LB = Unit.Foot, Unit.FPS, Unit.Radian, Unit.FootPound, Unit.Pound
_FLAGS: dict[int, TrajFlag] = {}  # TrajFlag(...) of each flag value, looked up once


def _traj_values(v) -> TrajectoryData:
    """A TrajectoryData from the unpacked fields of one BCLIBCFFI_TrajectoryData (the order of the struct).

    TrajectoryData is a NamedTuple: it is built with tuple.__new__ from its fields in order, and the unit objects are
    created inline (object.__new__ and the two attribute stores TrajectoryData._new_feet and the like do), which saves
    the Python-level __new__ with sixteen keyword arguments and ten calls per record.
    """
    flag = _FLAGS.get(v[15])
    if flag is None:
        flag = _FLAGS[v[15]] = TrajFlag(v[15])
    distance = _obj_new(Distance)
    distance._value = v[1] * 12
    distance._defined_units = _FOOT
    velocity = _obj_new(Velocity)
    velocity._value = v[2] / 3.2808399
    velocity._defined_units = _FPS
    height = _obj_new(Distance)
    height._value = v[4] * 12
    height._defined_units = _FOOT
    slant_height = _obj_new(Distance)
    slant_height._value = v[5] * 12
    slant_height._defined_units = _FOOT
    drop_angle = _obj_new(Angular)
    drop_angle._value = v[6]
    drop_angle._defined_units = _RAD
    windage = _obj_new(Distance)
    windage._value = v[7] * 12
    windage._defined_units = _FOOT
    windage_angle = _obj_new(Angular)
    windage_angle._value = v[8]
    windage_angle._defined_units = _RAD
    slant_distance = _obj_new(Distance)
    slant_distance._value = v[9] * 12
    slant_distance._defined_units = _FOOT
    angle = _obj_new(Angular)
    angle._value = v[10]
    angle._defined_units = _RAD
    energy = _obj_new(Energy)
    energy._value = v[13]
    energy._defined_units = _FTLB
    ogw = _obj_new(Weight)
    ogw._value = v[14] / 0.000142857143
    ogw._defined_units = _LB
    return _tuple_new(
        TrajectoryData,
        (v[0], distance, velocity, v[3], height, slant_height, drop_angle, windage, windage_angle, slant_distance,
         angle, v[11], v[12], energy, ogw, flag),
    )  # fmt: skip


def _traj(r: "_T.TrajData") -> TrajectoryData:
    # the bytes of the struct through its address: the ctypes structures of PyPy (older releases) and GraalPy do not export the
    # buffer interface that struct.unpack_from(r) would need
    return _traj_values(_TRAJ_FMT.unpack_from(C.string_at(C.addressof(r), _TRAJ_FMT.size)))


def _raise(err: "_T.Error"):
    msg = err.message.decode("utf-8", "replace")
    if err.code == _G.BCLIBCFFI_ERR_OUT_OF_RANGE:
        raise OutOfRangeError(Distance.Foot(err.f64_0), Distance.Foot(err.f64_1), Angular.Radian(err.f64_2), msg)
    if err.code == _G.BCLIBCFFI_ERR_ZERO_FINDING:
        raise ZeroFindingError(err.f64_0, err.i32_0, Angular.Radian(err.f64_1), msg)
    if err.code == _G.BCLIBCFFI_ERR_INTERCEPTION:
        raise InterceptionError(msg, (None, None))
    raise SolverRuntimeError(msg)


# ---------------------------------------------------------------- engine mixin


_KEY = {  # BCLIBCFFI_BaseTrajInterpKey by attribute name (the Cython layer's _attribute_to_key)
    "time": 0,
    "mach": 1,
    "position.x": 2,
    "position.y": 3,
    "position.z": 4,
    "velocity.x": 5,
    "velocity.y": 6,
    "velocity.z": 7,
}


def _integrate_common(engine, shot_info, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, call):
    """The shared body of integrate(): shot fill, one C call (through `call`), result conversion.

    `call(lib, scr, want_dense)` makes the single C call of the engine family, with the engine's scratch storage.
    Mirrors CythonizedBaseIntegrationEngine.integrate: conversion, integrate_filtered, record list, termination,
    ShotProps and HitResult.
    """
    lib = _LIB or _load_library()
    scr = _scratch_of(engine)
    _fill_shot(scr, shot_info, engine._config, _METHOD[engine._NATIVE_METHOD])
    req = scr.req
    req.range_limit_ft = range_limit_ft
    req.range_step_ft = range_step_ft
    req.time_step = time_step
    req.filter_flags = int(filter_flags)
    rc = call(lib, scr, 1 if dense_output else 0)
    if rc != _G.BCLIBCFFI_OK:
        _raise(scr.err)
    count = scr.n.value
    if count:
        # the native records are copied once, then freed; the fields are unpacked from the copy
        buf = C.string_at(scr.recs, count * _TRAJ_FMT.size)
        trajectory = [_traj_values(v) for v in _TRAJ_FMT.iter_unpack(buf)]
    else:
        trajectory = []
    if count:
        lib.BCLIBCFFI_free_trajectory(scr.recs)
    base_data = None
    if dense_output:
        # the dense steps stay native-sized: one copy into a buffer, items are built on access (as the Cython sequence)
        base_data = _DenseSeq(scr.dense, scr.dn.value, lib)
    props = ShotProps.from_shot(shot_info)
    props.filter_flags = filter_flags
    props.calc_step = engine.get_calc_step()
    term = _TERMINATION.get(scr.reason.value)
    error = RangeError(term, trajectory) if term is not None else None
    return HitResult(props, trajectory, base_data, filter_flags != TrajFlag.NONE, error), scr.reason.value, scr.shot


_BASE_FMT = struct.Struct("8d")  # BCLIBCFFI_BaseTrajData: time, px, py, pz, vx, vy, vz, mach


class _DenseSeq(Sequence):
    """Dense accepted steps of one integrate() call. The native array is copied once and freed; each item is a
    BaseTrajData built on access (the Cython layer's CythonizedBaseTrajSeq does the same on __getitem__)."""

    __slots__ = ("_buf", "_n")

    def __init__(self, ptr, count, lib):
        size = _BASE_FMT.size
        self._buf = C.string_at(ptr, count * size) if count else b""
        self._n = count
        if count:
            lib.BCLIBCFFI_free_base_trajectory(ptr)

    def __len__(self):
        return self._n

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return [self[i] for i in range(*idx.indices(self._n))]
        if idx < 0:
            idx += self._n
        if not 0 <= idx < self._n:
            raise IndexError(idx)
        t, px, py, pz, vx, vy, vz, mach = _BASE_FMT.unpack_from(self._buf, idx * _BASE_FMT.size)
        return BaseTrajData(t, Vector(px, py, pz), Vector(vx, vy, vz), mach)


def _fixed_call(lib, scr, want_dense):
    return lib.BCLIBCFFI_integrate_dense_shot(
        C.byref(scr.shot),
        C.byref(scr.req),
        want_dense,
        C.byref(scr.recs),
        C.byref(scr.n),
        C.byref(scr.dense),
        C.byref(scr.dn),
        C.byref(scr.reason),
        C.byref(scr.err),
    )


class _FixedEngine(BaseIntegrationEngine):
    """Fixed-step engines (RK4, Euler, Velocity Verlet): the C entry points are called directly, no Python engine
    is inherited."""

    _NATIVE_METHOD = "rk4"
    DEFAULT_TIME_STEP = 0.0025

    def get_calc_step(self) -> float:
        """The integration step in seconds: the engine's base step (`DEFAULT_TIME_STEP`) times `cStepMultiplier`."""
        return self._config.cStepMultiplier * self.DEFAULT_TIME_STEP

    def _native_shot(self, shot_info):
        """The shot as filled into this engine's scratch storage (the C input for every call)."""
        _LIB or _load_library()
        scr = _scratch_of(self)
        _fill_shot(scr, shot_info, self._config, _METHOD[self._NATIVE_METHOD])
        return scr

    def integrate(
        self, shot_info, max_range, dist_step=None, time_step=0.0, filter_flags=0, dense_output=False, **kwargs
    ):
        """Same as the base engine's `integrate()`; the integration is one call of the native library, and the result is
        built from its records."""
        range_limit_ft = max_range._feet
        range_step_ft = range_limit_ft if dist_step is None else dist_step._feet
        return _integrate_common(
            self, shot_info, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, _fixed_call
        )[0]

    def _integrate(self, props, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, **kwargs):
        return _integrate_common(
            self, props.shot, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, _fixed_call
        )[0]

    def integrate_raw_at(self, shot_info, key_attribute: str, target_value: float):
        """Same as the base engine's `integrate_raw_at()`: integrates until `key_attribute` reaches `target_value`, in
        the native library (see the base engine for the keys)."""
        if key_attribute not in _KEY:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_integrate_at_shot(
            C.byref(scr.shot), _KEY[key_attribute], target_value, C.byref(scr.it), C.byref(scr.err)
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        raw = scr.it.raw_data
        return (
            BaseTrajData(raw.time, Vector(raw.px, raw.py, raw.pz), Vector(raw.vx, raw.vy, raw.vz), raw.mach),
            _traj(scr.it.full_data),
        )

    def zero_angle(self, shot_info, distance):
        """Same as the base engine's `zero_angle()`: the barrel elevation that hits the sight line at `distance`, found
        in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_angle_shot(C.byref(scr.shot), distance._feet, C.byref(scr.value), C.byref(scr.err))
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.value.value)

    def zero_point(self, shot_info, distance):
        """Same as the base engine's `zero_point()`: the zero angle and the trajectory point it was determined at, found
        in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_point_shot(C.byref(scr.shot), distance._feet, C.byref(scr.zp), C.byref(scr.err))
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(scr.zp.point)

    def find_zero_angle(self, shot_info, distance, lofted=False):
        """Same as the base engine's `find_zero_angle()` (`lofted` picks the high solution), found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_angle_lofted_shot(
            C.byref(scr.shot), distance._feet, 1 if lofted else 0, C.byref(scr.value), C.byref(scr.err)
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.value.value)

    def find_zero_point(self, shot_info, distance, lofted=False):
        """Same as the base engine's `find_zero_point()` (`lofted` picks the high solution), found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_point_lofted_shot(
            C.byref(scr.shot), distance._feet, 1 if lofted else 0, C.byref(scr.zp), C.byref(scr.err)
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(scr.zp.point)

    def find_max_range(self, shot_info, angle_bracket_deg=(0, 90)):
        """Same as the base engine's `find_max_range()`: the maximum range and the launch angle that reaches it, found in
        the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_max_range_shot(
            C.byref(scr.shot), angle_bracket_deg[0], angle_bracket_deg[1], C.byref(scr.mr), C.byref(scr.err)
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Distance.Foot(scr.mr.max_range_ft), Angular.Radian(scr.mr.angle_at_max_rad)

    def find_apex(self, shot_info):
        """Same as the base engine's `find_apex()`: the apex of the trajectory, found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_apex_shot(C.byref(scr.shot), C.byref(scr.apex), C.byref(scr.err))
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return _traj(scr.apex)


class _AdaptiveEngine(BaseIntegrationEngine):
    """Adaptive engines (Cash-Karp, Dormand-Prince, Tsitouras): per-instance tolerances (plain attributes, set through
    the properties) and step statistics, snapshotted after each successful integrate(), as in the Cython engines."""

    _NATIVE_METHOD = "dopri"
    DEFAULT_TIME_STEP = 0.0025
    _DEFAULT_TOL = 1e-6

    def __init__(self, config=None):
        rtol, atol = self._DEFAULT_TOL, self._DEFAULT_TOL
        base = config
        if isinstance(config, dict):
            base = config.copy()
            rtol = base.pop("relative_tolerance", rtol)
            atol = base.pop("absolute_tolerance", atol)
        self._relative_tolerance = None
        self._absolute_tolerance = None
        self.relative_tolerance = rtol
        self.absolute_tolerance = atol
        self._last_accepted, self._last_rejected = 0, 0
        BaseIntegrationEngine.__init__(self, base)  # configuration only

    @property
    def relative_tolerance(self) -> float:
        """SciPy-style relative local-error tolerance (default: ``1e-6``). Must be finite and positive, `ValueError`
        otherwise."""
        return self._relative_tolerance

    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None:
        """SciPy-style relative local-error tolerance (default: ``1e-6``). Must be finite and positive, `ValueError`
        otherwise."""
        if not math.isfinite(value) or value <= 0:
            raise ValueError("relative_tolerance must be finite and positive")
        self._relative_tolerance = float(value)

    @property
    def absolute_tolerance(self) -> float:
        """Scalar SciPy-style absolute local-error tolerance (default: ``1e-6``), applied to all six state components.
        Must be finite and non-negative, `ValueError` otherwise."""
        return self._absolute_tolerance

    @absolute_tolerance.setter
    def absolute_tolerance(self, value: float) -> None:
        """Scalar SciPy-style absolute local-error tolerance (default: ``1e-6``), applied to all six state components.
        Must be finite and non-negative, `ValueError` otherwise."""
        if not math.isfinite(value) or value < 0:
            raise ValueError("absolute_tolerance must be finite and non-negative")
        self._absolute_tolerance = float(value)

    def get_step_stats(self) -> tuple[int, int]:
        """The numbers of accepted and rejected steps of the last successful `integrate()` call, as ``(accepted,
        rejected)``."""
        return self._last_accepted, self._last_rejected

    def get_calc_step(self) -> float:
        """The integration step in seconds: the engine's base step (`DEFAULT_TIME_STEP`) times `cStepMultiplier`."""
        return self._config.cStepMultiplier * self.DEFAULT_TIME_STEP

    def _native_shot(self, shot_info):
        """The shot as filled into this engine's scratch storage (the C input for every call)."""
        _LIB or _load_library()
        scr = _scratch_of(self)
        _fill_shot(scr, shot_info, self._config, _METHOD[self._NATIVE_METHOD])
        return scr

    def integrate(
        self, shot_info, max_range, dist_step=None, time_step=0.0, filter_flags=0, dense_output=False, **kwargs
    ):
        """Same as the base engine's `integrate()`; the integration is one call of the native library, and this call's
        own step stats are snapshotted (see `get_step_stats()`)."""
        range_limit_ft = max_range._feet
        range_step_ft = range_limit_ft if dist_step is None else dist_step._feet
        return self._integrate_adaptive(shot_info, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output)

    def _integrate(self, props, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, **kwargs):
        return self._integrate_adaptive(
            props.shot, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output
        )

    def _integrate_adaptive(self, shot_info, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output):
        _LIB or _load_library()
        method = _METHOD[self._NATIVE_METHOD]
        rtol, atol = self._relative_tolerance, self._absolute_tolerance

        def call(lib, scr, want_dense):
            return lib.BCLIBCFFI_integrate_adaptive_shot(
                C.byref(scr.shot),
                method,
                rtol,
                atol,
                C.byref(scr.req),
                want_dense,
                C.byref(scr.recs),
                C.byref(scr.n),
                C.byref(scr.dense),
                C.byref(scr.dn),
                C.byref(scr.reason),
                C.byref(scr.stats),
                C.byref(scr.err),
            )

        result, _reason, _s = _integrate_common(
            self, shot_info, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, call
        )
        stats = _scratch_of(self).stats
        self._last_accepted, self._last_rejected = stats.accepted, stats.rejected
        return result

    def integrate_raw_at(self, shot_info, key_attribute: str, target_value: float):
        """Same as the base engine's `integrate_raw_at()`: integrates until `key_attribute` reaches `target_value`, in
        the native library (see the base engine for the keys)."""
        if key_attribute not in _KEY:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_integrate_at_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            _KEY[key_attribute],
            target_value,
            C.byref(scr.it),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        raw = scr.it.raw_data
        return (
            BaseTrajData(raw.time, Vector(raw.px, raw.py, raw.pz), Vector(raw.vx, raw.vy, raw.vz), raw.mach),
            _traj(scr.it.full_data),
        )

    def zero_angle(self, shot_info, distance):
        """Same as the base engine's `zero_angle()`: the barrel elevation that hits the sight line at `distance`, found
        in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_angle_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            distance._feet,
            C.byref(scr.value),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.value.value)

    def zero_point(self, shot_info, distance):
        """Same as the base engine's `zero_point()`: the zero angle and the trajectory point it was determined at, found
        in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_point_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            distance._feet,
            C.byref(scr.zp),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(scr.zp.point)

    def find_zero_angle(self, shot_info, distance, lofted=False):
        """Same as the base engine's `find_zero_angle()` (`lofted` picks the high solution), found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_angle_lofted_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            distance._feet,
            1 if lofted else 0,
            C.byref(scr.value),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.value.value)

    def find_zero_point(self, shot_info, distance, lofted=False):
        """Same as the base engine's `find_zero_point()` (`lofted` picks the high solution), found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_zero_point_lofted_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            distance._feet,
            1 if lofted else 0,
            C.byref(scr.zp),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(scr.zp.point)

    def find_max_range(self, shot_info, angle_bracket_deg=(0, 90)):
        """Same as the base engine's `find_max_range()`: the maximum range and the launch angle that reaches it, found in
        the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_max_range_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            angle_bracket_deg[0],
            angle_bracket_deg[1],
            C.byref(scr.mr),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return Distance.Foot(scr.mr.max_range_ft), Angular.Radian(scr.mr.angle_at_max_rad)

    def find_apex(self, shot_info):
        """Same as the base engine's `find_apex()`: the apex of the trajectory, found in the native library."""
        lib = _LIB or _load_library()
        scr = self._native_shot(shot_info)
        rc = lib.BCLIBCFFI_find_apex_adaptive_shot(
            C.byref(scr.shot),
            _METHOD[self._NATIVE_METHOD],
            self._relative_tolerance,
            self._absolute_tolerance,
            C.byref(scr.apex),
            C.byref(scr.stats),
            C.byref(scr.err),
        )
        if rc != _G.BCLIBCFFI_OK:
            _raise(scr.err)
        return _traj(scr.apex)


# ---------------------------------------------------------------- engine classes (names as Cython layer)


class NativeEulerIntegrationEngine(_FixedEngine):
    """Euler integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedEulerIntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.5 s)."""

    _NATIVE_METHOD = "euler"
    DEFAULT_TIME_STEP = 0.5


class NativeRK4IntegrationEngine(_FixedEngine):
    """RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedRK4IntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.0025 s)."""

    _NATIVE_METHOD = "rk4"
    DEFAULT_TIME_STEP = 0.0025


class NativeVelocityVerletIntegrationEngine(_FixedEngine):
    """Velocity Verlet integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedVelocityVerletIntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.001 s)."""

    _NATIVE_METHOD = "verlet"
    DEFAULT_TIME_STEP = 0.001


class NativeCashKarpIntegrationEngine(_AdaptiveEngine):
    """Cash-Karp (embedded adaptive RK45) integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedCashKarpIntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.0025 s;
    `relative_tolerance` and `absolute_tolerance` default to ``1e-6``)."""

    _NATIVE_METHOD = "rkck"
    DEFAULT_TIME_STEP = 0.0025


class NativeDormandPrinceIntegrationEngine(_AdaptiveEngine):
    """Dormand-Prince 5(4) integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedDormandPrinceIntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.0025 s;
    `relative_tolerance` and `absolute_tolerance` default to ``1e-6``)."""

    _NATIVE_METHOD = "dopri"
    DEFAULT_TIME_STEP = 0.0025


class NativeTsitourasIntegrationEngine(_AdaptiveEngine):
    """Tsitouras 5(4) integration engine for ballistic calculations through ctypes: the engine of
    `CythonizedTsitourasIntegrationEngine`, run by the native `bclibc_ffi` library (base step 0.0025 s;
    `relative_tolerance` and `absolute_tolerance` default to ``1e-6``)."""

    _NATIVE_METHOD = "tsit"
    DEFAULT_TIME_STEP = 0.0025
