"""Shared ctypes/FFI plumbing for the tiny_bclibc example engines (see sp.py / dp.py).

Not meant to be used directly — import `TinyBclibcSingleIntegrationEngine` from `.sp` or
`TinyBclibcDoubleIntegrationEngine` from `.dp`. See the `tiny_bclibc` package docstring
(`__init__.py`) for the full picture and `CMakeLists.txt` for building the native libraries.
"""

import ctypes
import math
import os
import warnings
from functools import lru_cache
from types import SimpleNamespace

from typing_extensions import override

from py_ballisticcalc.engines.base_engine import (
    BaseEngineConfigDict,
    BaseIntegrationEngine,
    TrajectoryDataFilter,
)
from py_ballisticcalc.exceptions import RangeError, SolverRuntimeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.trajectory_data import BaseTrajData, HitResult, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Pressure, Temperature, Velocity
from py_ballisticcalc.vector import Vector

__all__ = ("TinyBclibcIntegrationEngineBase",)

# tiny_bclibc/include/tiny_bclibc/base_types.h: TINY_BCLIBC_TerminationReason
_TERM_NO_TERMINATE = 0
_TERM_TARGET_RANGE_REACHED = 1
_TERM_MIN_VELOCITY_REACHED = 2
_TERM_MAX_DROP_REACHED = 3
_TERM_MIN_ALTITUDE_REACHED = 4
_TERM_HANDLER_STOP = 5

_TERM_REASON_MAP = {
    _TERM_MIN_VELOCITY_REACHED: RangeError.MinimumVelocityReached,
    _TERM_MAX_DROP_REACHED: RangeError.MaximumDropReached,
    _TERM_MIN_ALTITUDE_REACHED: RangeError.MinimumAltitudeReached,
}

_TINY_BCLIBC_OK = 0


@lru_cache(maxsize=None)
def _make_ctypes_bindings(real_t) -> SimpleNamespace:
    """Build the ctypes Structure mirrors for one precision (real_t = c_float or c_double).

    Field order/types are taken from
    tiny_bclibc/include/tiny_bclibc/{base_types,traj_data,v3d}.h — every `real_t` field there
    maps to `real_t` here, so the whole struct tree must be regenerated per precision (a float
    build and a double build of tiny_bclibc do not share a struct layout).
    """

    class V3d(ctypes.Structure):
        _fields_ = (("x", real_t), ("y", real_t), ("z", real_t))

    class CurvePoint(ctypes.Structure):
        _fields_ = (("a", real_t), ("b", real_t), ("c", real_t), ("d", real_t))

    class Atmosphere(ctypes.Structure):
        _fields_ = (
            ("t0", real_t),
            ("a0", real_t),
            ("p0", real_t),
            ("mach", real_t),
            ("density_ratio", real_t),
            ("cLowestTempC", real_t),
        )

    class Coriolis(ctypes.Structure):
        _fields_ = (
            ("sin_lat", real_t),
            ("cos_lat", real_t),
            ("sin_az", real_t),
            ("cos_az", real_t),
            ("range_east", real_t),
            ("range_north", real_t),
            ("cross_east", real_t),
            ("cross_north", real_t),
            ("flat_fire_only", ctypes.c_int32),
            ("muzzle_velocity_fps", real_t),
        )

    class Wind(ctypes.Structure):
        _fields_ = (
            ("velocity_fps", real_t),
            ("direction_from_rad", real_t),
            ("until_distance_ft", real_t),
            ("max_distance_ft", real_t),
        )

    class WindSock(ctypes.Structure):
        _fields_ = (
            ("winds", ctypes.POINTER(Wind)),
            ("count", ctypes.c_int32),
            ("current_idx", ctypes.c_int32),
            ("next_range", real_t),
            ("last_vector", V3d),
        )

    class Config(ctypes.Structure):
        _fields_ = (
            ("cStepMultiplier", real_t),
            ("cZeroFindingAccuracy", real_t),
            ("cMinimumVelocity", real_t),
            ("cMaximumDrop", real_t),
            ("cMaxIterations", ctypes.c_int32),
            ("cGravityConstant", real_t),
            ("cMinimumAltitude", real_t),
        )

    class TbShotProps(ctypes.Structure):
        _fields_ = (
            ("bc", real_t),
            ("muzzle_velocity", real_t),
            ("weight", real_t),
            ("diameter", real_t),
            ("length", real_t),
            ("stability_coefficient", real_t),
            ("sight_height", real_t),
            ("twist", real_t),
            ("barrel_elevation", real_t),
            ("barrel_azimuth", real_t),
            ("look_angle", real_t),
            ("cant_cosine", real_t),
            ("cant_sine", real_t),
            ("alt0", real_t),
            ("calc_step", real_t),
            ("atmo", Atmosphere),
            ("coriolis", Coriolis),
            ("wind_sock", WindSock),
            ("cfg", Config),
            ("curve", ctypes.POINTER(CurvePoint)),
            ("mach_list", ctypes.POINTER(real_t)),
            ("curve_count", ctypes.c_int32),
        )

    class TbShot(ctypes.Structure):
        _fields_ = (
            ("bc", real_t),
            ("weight_grain", real_t),
            ("diameter_inch", real_t),
            ("length_inch", real_t),
            ("muzzle_velocity_fps", real_t),
            ("sight_height_ft", real_t),
            ("twist_inch", real_t),
            ("temp_c", real_t),
            ("pressure_hpa", real_t),
            ("altitude_ft", real_t),
            ("humidity", real_t),
            ("mach_data", ctypes.POINTER(real_t)),
            ("cd_data", ctypes.POINTER(real_t)),
            ("drag_table_size", ctypes.c_int32),
            ("winds", ctypes.POINTER(Wind)),
            ("wind_count", ctypes.c_int32),
            ("look_angle_rad", real_t),
            ("barrel_elevation_rad", real_t),
            ("barrel_azimuth_rad", real_t),
            ("cant_angle_rad", real_t),
            ("latitude_deg", real_t),
            ("azimuth_deg", real_t),
            ("config", Config),
        )

    class TbBaseTrajData(ctypes.Structure):
        _fields_ = (
            ("time", real_t),
            ("px", real_t),
            ("py", real_t),
            ("pz", real_t),
            ("vx", real_t),
            ("vy", real_t),
            ("vz", real_t),
            ("mach", real_t),
        )

    raw_step_cb = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.POINTER(TbBaseTrajData), ctypes.c_void_p)

    return SimpleNamespace(
        real_t=real_t,
        Wind=Wind,
        Config=Config,
        CurvePoint=CurvePoint,
        ShotProps=TbShotProps,
        Shot=TbShot,
        BaseTrajData=TbBaseTrajData,
        RawStepCb=raw_step_cb,
    )


def _find_library_path(env_var: str, precision_flag: str) -> str:
    path = os.environ.get(env_var)
    if path:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{env_var} is set to '{path}', but no such file exists.")
        return path
    raise FileNotFoundError(
        f"tiny_bclibc shared library not found ({precision_flag}). Build it via the "
        "CMakeLists.txt in this directory (builds both precisions from the bclibc git "
        "submodule already vendored at "
        "py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc):\n"
        "  git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc\n"
        "  cmake -B examples/tiny_bclibc/build -S examples/tiny_bclibc\n"
        "  cmake --build examples/tiny_bclibc/build\n"
        f"then set {env_var} to the resulting libtiny_bclibc.so (.dylib/.dll) path."
    )


@lru_cache(maxsize=None)
def _load_library(env_var: str, precision_flag: str, real_t) -> ctypes.CDLL:
    b = _make_ctypes_bindings(real_t)
    lib = ctypes.CDLL(_find_library_path(env_var, precision_flag))

    lib.tiny_bclibc_sizeof_shot_props.argtypes = ()
    lib.tiny_bclibc_sizeof_shot_props.restype = ctypes.c_int32
    lib.tiny_bclibc_sizeof_curve_point.argtypes = ()
    lib.tiny_bclibc_sizeof_curve_point.restype = ctypes.c_int32

    c_size = lib.tiny_bclibc_sizeof_shot_props()
    py_size = ctypes.sizeof(b.ShotProps)
    if c_size != py_size:
        raise RuntimeError(
            f"tiny_bclibc ABI mismatch: sizeof(TINY_BCLIBC_ShotProps) is {c_size} bytes in the "
            f"compiled library but {py_size} bytes per this module's ctypes mirror ({precision_flag}). "
            "The library was likely built from a different tiny_bclibc header version, or with "
            "the wrong TINY_BCLIBC_SINGLE_PRECISION setting for this engine; rebuild it to match, "
            "or update the ctypes structures in _common.py."
        )
    c_curve_size = lib.tiny_bclibc_sizeof_curve_point()
    if c_curve_size != ctypes.sizeof(b.CurvePoint):
        raise RuntimeError("tiny_bclibc ABI mismatch: sizeof(TINY_BCLIBC_CurvePoint) differs.")

    lib.tiny_bclibc_build_shot_props.argtypes = (
        ctypes.POINTER(b.Shot),
        ctypes.POINTER(b.CurvePoint),
        ctypes.POINTER(b.ShotProps),
    )
    lib.tiny_bclibc_build_shot_props.restype = ctypes.c_int32

    lib.tiny_bclibc_integrate_raw.argtypes = (
        ctypes.POINTER(b.ShotProps),
        b.real_t,
        b.RawStepCb,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int32),
    )
    lib.tiny_bclibc_integrate_raw.restype = ctypes.c_int32

    lib.tiny_bclibc_last_error.argtypes = ()
    lib.tiny_bclibc_last_error.restype = ctypes.c_char_p

    return lib


class TinyBclibcIntegrationEngineBase(BaseIntegrationEngine):
    """Shared implementation for the single- and double-precision tiny_bclibc engines.

    Subclasses (`sp.TinyBclibcSingleIntegrationEngine`, `dp.TinyBclibcDoubleIntegrationEngine`)
    set `REAL_T` (`ctypes.c_float` or `ctypes.c_double`), `LIB_ENV_VAR` (the env var naming that
    precision's compiled library), and `PRECISION_LABEL` (used in error/log messages).
    Everything else — building the tiny_bclibc Shot/ShotProps, streaming raw RK4 steps into
    `TrajectoryDataFilter`, mapping termination reasons — is precision-agnostic.
    """

    DEFAULT_TIME_STEP = 0.0025  # matches tiny_bclibc_build_shot_props' calc_step formula

    REAL_T: type
    LIB_ENV_VAR: str
    PRECISION_LABEL: str

    # Subclasses may set this to override BaseEngineConfig's default cZeroFindingAccuracy
    # (5e-6 ft) when the caller doesn't explicitly configure it -- see
    # TinyBclibcSingleIntegrationEngine, whose default is loosened to match float32's
    # representable precision at typical zero distances (mirroring tiny_bclibc's own
    # TINY_BCLIBC_SINGLE_PRECISION zero_angle_newton, which uses the same 1e-3 ft). Without
    # this, BaseIntegrationEngine._zero_angle's primary (fast, damped-Newton) method can
    # never converge tight enough for single precision and always falls back to
    # _find_zero_angle's guaranteed-but-~10-50x-more-expensive golden-section + Ridder's
    # search.
    DEFAULT_ZERO_FINDING_ACCURACY: float | None = None

    def __init__(self, config: BaseEngineConfigDict | None) -> None:
        if self.DEFAULT_ZERO_FINDING_ACCURACY is not None and (
            config is None or "cZeroFindingAccuracy" not in config
        ):
            config = {**(config or {}), "cZeroFindingAccuracy": self.DEFAULT_ZERO_FINDING_ACCURACY}
        super().__init__(config)
        self._b = _make_ctypes_bindings(self.REAL_T)
        self._lib = _load_library(self.LIB_ENV_VAR, self.PRECISION_LABEL, self.REAL_T)
        self.integration_step_count: int = 0
        self.trajectory_count = 0

    @override
    def get_calc_step(self) -> float:
        return super().get_calc_step() * self.DEFAULT_TIME_STEP

    def _build_tiny_shot(self, props: ShotProps):
        """Build a ctypes TINY_BCLIBC_Shot from the current (Python) ShotProps.

        Returns the struct plus a tuple of buffers that must stay alive for as long as the
        struct (and any ShotProps built from it) is in use — tiny_bclibc's ShotProps only
        stores pointers into these arrays, it does not copy them.
        """
        b = self._b
        real_t = b.real_t

        drag_table = props.shot.ammo.dm.drag_table
        n = len(drag_table)
        mach_arr = (real_t * n)(*(dp.Mach for dp in drag_table))
        cd_arr = (real_t * n)(*(dp.CD for dp in drag_table))

        winds = props.winds
        wind_arr = (b.Wind * len(winds))(
            *(
                b.Wind(
                    velocity_fps=w.velocity >> Velocity.FPS,
                    direction_from_rad=w.direction_from >> Angular.Radian,
                    until_distance_ft=w.until_distance >> Distance.Foot,
                    max_distance_ft=w.MAX_DISTANCE_FEET,
                )
                for w in winds
            )
        )

        latitude_deg = props.latitude if props.latitude is not None else math.nan
        azimuth_deg = props.azimuth if props.azimuth is not None else math.nan

        cfg = b.Config(
            cStepMultiplier=self._config.cStepMultiplier,
            cZeroFindingAccuracy=self._config.cZeroFindingAccuracy,
            cMinimumVelocity=self._config.cMinimumVelocity,
            cMaximumDrop=self._config.cMaximumDrop,
            cMaxIterations=self._config.cMaxIterations,
            cGravityConstant=self._config.cGravityConstant,
            cMinimumAltitude=self._config.cMinimumAltitude,
        )

        shot = b.Shot(
            bc=props.bc,
            weight_grain=props.weight_grains,
            diameter_inch=props.diameter_inch,
            length_inch=props.length_inch,
            muzzle_velocity_fps=props.muzzle_velocity_fps,
            sight_height_ft=props.sight_height_ft,
            twist_inch=props.twist_inch,
            temp_c=props.shot.atmo.temperature >> Temperature.Celsius,
            pressure_hpa=props.shot.atmo.pressure >> Pressure.hPa,
            altitude_ft=props.alt0_ft,
            humidity=props.shot.atmo.humidity,
            mach_data=mach_arr,
            cd_data=cd_arr,
            drag_table_size=n,
            winds=wind_arr,
            wind_count=len(winds),
            look_angle_rad=props.look_angle_rad,
            barrel_elevation_rad=props.barrel_elevation_rad,
            barrel_azimuth_rad=props.barrel_azimuth_rad,
            cant_angle_rad=props.shot.cant_angle >> Angular.Radian,
            latitude_deg=latitude_deg,
            azimuth_deg=azimuth_deg,
            config=cfg,
        )
        # Keep the backing arrays alive alongside the struct that points into them.
        return shot, (mach_arr, cd_arr, wind_arr)

    @override
    def _integrate(
        self,
        props: ShotProps,
        range_limit_ft: float,
        range_step_ft: float,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = TrajFlag.NONE,
        dense_output: bool = False,
        **kwargs,
    ) -> HitResult:
        """Create HitResult for the specified shot.

        Runs tiny_bclibc's RK4 core (at this engine's precision) for the raw kinematic
        stepping; all trajectory-point filtering, interpolation, and derived-quantity math run
        in Python exactly as they do for
        [`RK4IntegrationEngine`][py_ballisticcalc.engines.rk4.RK4IntegrationEngine].
        """
        self.trajectory_count += 1
        props.filter_flags = filter_flags
        b = self._b

        step_data: list[BaseTrajData] = []
        data_filter = TrajectoryDataFilter(
            props=props,
            filter_flags=filter_flags,
            range_limit=range_limit_ft,
            range_step=range_step_ft,
            time_step=time_step,
        )

        tb_shot, _keepalive = self._build_tiny_shot(props)
        curve_buf = (b.CurvePoint * tb_shot.drag_table_size)()
        tb_props = b.ShotProps()
        rc = self._lib.tiny_bclibc_build_shot_props(ctypes.byref(tb_shot), curve_buf, ctypes.byref(tb_props))
        if rc != _TINY_BCLIBC_OK:
            raise SolverRuntimeError(
                f"tiny_bclibc_build_shot_props failed: "
                f"{self._lib.tiny_bclibc_last_error().decode('utf-8', 'replace')}"
            )

        integration_step_count = 0
        callback_error: list[BaseException] = []

        def _on_step(pt_ptr, _ctx) -> int:  # type: ignore[no-untyped-def]
            nonlocal integration_step_count
            try:
                pt = pt_ptr.contents
                integration_step_count += 1
                position = Vector(pt.px, pt.py, pt.pz)
                velocity = Vector(pt.vx, pt.vy, pt.vz)
                _density_ratio, mach = props.get_density_and_mach_for_altitude(position.y)
                data = BaseTrajData(time=pt.time, position=position, velocity=velocity, mach=mach)
                data_filter.record(data)
                if dense_output:
                    step_data.append(data)
            except BaseException as exc:  # pylint: disable=broad-except
                callback_error.append(exc)
                return _TERM_HANDLER_STOP
            return 0

        out_reason = ctypes.c_int32(_TERM_NO_TERMINATE)
        warnings.simplefilter("once")
        rc = self._lib.tiny_bclibc_integrate_raw(
            ctypes.byref(tb_props),
            b.real_t(range_limit_ft),
            b.RawStepCb(_on_step),
            None,
            ctypes.byref(out_reason),
        )

        if callback_error:
            raise callback_error[0]
        if rc != _TINY_BCLIBC_OK:
            raise SolverRuntimeError(
                f"tiny_bclibc_integrate_raw failed: "
                f"{self._lib.tiny_bclibc_last_error().decode('utf-8', 'replace')}"
            )

        termination_reason = _TERM_REASON_MAP.get(out_reason.value)
        data_filter.finalize(termination_reason)

        ranges = data_filter.records
        logger.debug(f"tiny_bclibc ({self.PRECISION_LABEL}) ran {integration_step_count} iterations")
        self.integration_step_count += integration_step_count
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props, ranges, step_data, filter_flags > 0, error)
