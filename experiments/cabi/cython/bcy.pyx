# cython: language_level=3
"""The bclibc engines as Cython over the C ABI (bclibc_ffi.h), not the C++ API."""
import math
import struct
from collections.abc import Sequence

from cpython.bytes cimport PyBytes_FromStringAndSize
from libc.math cimport NAN
from libc.stdint cimport int32_t
from libc.stdlib cimport free, malloc, realloc

from bcffi cimport *

from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine
from py_ballisticcalc.exceptions import (
    InterceptionError, OutOfRangeError, RangeError, SolverRuntimeError, ZeroFindingError,
)
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.trajectory_data import BaseTrajData, HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Energy, Unit, Velocity, Weight
from py_ballisticcalc.vector import Vector

_TERMINATION = {
    1: None,
    2: RangeError.MinimumVelocityReached,
    3: RangeError.MaximumDropReached,
    4: RangeError.MinimumAltitudeReached,
}
_KEY = {"time": 0, "mach": 1, "position.x": 2, "position.y": 3, "position.z": 4,
        "velocity.x": 5, "velocity.y": 6, "velocity.z": 7}
_BASE_FMT = struct.Struct("8d")

cdef object _tuple_new = tuple.__new__
cdef object _obj_new = object.__new__
cdef object _TD = TrajectoryData
cdef object _Distance = Distance, _Velocity = Velocity, _Angular = Angular, _Energy = Energy, _Weight = Weight
cdef object _U_FOOT = Unit.Foot, _U_FPS = Unit.FPS, _U_RAD = Unit.Radian, _U_FTLB = Unit.FootPound, _U_LB = Unit.Pound
cdef dict _flags = {}


cdef inline object _feet(double v):
    d = _obj_new(_Distance)
    d._value = v * 12
    d._defined_units = _U_FOOT
    return d


cdef inline object _fps(double v):
    d = _obj_new(_Velocity)
    d._value = v / 3.2808399
    d._defined_units = _U_FPS
    return d


cdef inline object _rad(double v):
    d = _obj_new(_Angular)
    d._value = v
    d._defined_units = _U_RAD
    return d


cdef inline object _ft_lb(double v):
    d = _obj_new(_Energy)
    d._value = v
    d._defined_units = _U_FTLB
    return d


cdef inline object _lb(double v):
    d = _obj_new(_Weight)
    d._value = v / 0.000142857143
    d._defined_units = _U_LB
    return d


cdef class _Curve:
    """A drag table as two C double arrays that the C shot points at."""
    cdef double *m
    cdef double *c
    cdef int n

    def __cinit__(self, int n):
        self.n = n
        self.m = <double *>malloc(n * sizeof(double))
        self.c = <double *>malloc(n * sizeof(double))

    def __dealloc__(self):
        free(self.m)
        free(self.c)


cdef _Curve _std_curve(table):
    cdef _Curve curve = _Curve(len(table))
    cdef int i = 0
    for point in table:
        curve.m[i] = point["Mach"]
        curve.c[i] = point["CD"]
        i += 1
    return curve


cdef _Curve _STD_G1 = _std_curve(TableG1)
cdef _Curve _STD_G7 = _std_curve(TableG7)


cdef bint _same_curve(table, _Curve curve):
    cdef int i = 0
    if len(table) != curve.n:
        return False
    for point in table:
        if point.Mach != curve.m[i] or point.CD != curve.c[i]:
            return False
        i += 1
    return True


cdef class _Scratch:
    """Per-engine C storage, allocated once and reused by every call."""
    cdef BCLIBCFFI_Shot shot
    cdef BCLIBCFFI_TrajectoryRequest req
    cdef BCLIBCFFI_Error err
    cdef BCLIBCFFI_StepStats stats
    cdef BCLIBCFFI_ZeroPointResult zp
    cdef BCLIBCFFI_MaxRangeResult mr
    cdef BCLIBCFFI_TrajectoryData apex
    cdef BCLIBCFFI_Interception it
    cdef BCLIBCFFI_TrajectoryData *recs
    cdef BCLIBCFFI_DenseStep *dense
    cdef int32_t n, dn, reason
    cdef double value
    cdef BCLIBCFFI_Wind *winds
    cdef int n_wind
    cdef _Curve custom
    cdef object table, table_key
    cdef _Curve table_curve

    def __cinit__(self):
        self.n_wind = 0
        self.winds = NULL

    def __dealloc__(self):
        free(self.winds)


cdef _Scratch _scratch_of(engine):
    scr = engine.__dict__.get("_scratch")
    if scr is None:
        scr = engine.__dict__["_scratch"] = _Scratch()
    return scr


cdef _Curve _custom_curve(_Scratch scr, table, int n):
    cdef int i = 0
    if scr.custom is None or scr.custom.n != n:
        scr.custom = _Curve(n)
    for point in table:
        scr.custom.m[i] = point.Mach
        scr.custom.c[i] = point.CD
        i += 1
    return scr.custom


cdef int _fill_shot(_Scratch scr, shot_info, cfg, int method) except -1:
    cdef BCLIBCFFI_Shot *s = &scr.shot
    cdef BCLIBCFFI_Config *c = &s.config
    cdef int i, n, nw
    cdef _Curve curve
    ammo = shot_info.ammo
    dm = ammo.dm
    atmo = shot_info.atmo
    weapon = shot_info.weapon
    table = dm.drag_table
    n = len(table)
    key = (n, table[0], table[-1]) if n else None
    if table is scr.table and key == scr.table_key:
        curve = scr.table_curve
    else:
        if _same_curve(table, _STD_G7):
            curve = _STD_G7
        elif _same_curve(table, _STD_G1):
            curve = _STD_G1
        else:
            curve = _custom_curve(scr, table, n)
        scr.table, scr.table_key, scr.table_curve = table, key, curve

    winds = shot_info.winds
    nw = len(winds)
    if nw != scr.n_wind:
        scr.winds = <BCLIBCFFI_Wind *>realloc(scr.winds, (nw if nw else 1) * sizeof(BCLIBCFFI_Wind))
        scr.n_wind = nw
        s.winds = scr.winds if nw else NULL
    for i in range(nw):
        w = winds[i]
        scr.winds[i].velocity_fps = w.velocity._fps
        scr.winds[i].direction_from_rad = w.direction_from._rad
        scr.winds[i].until_distance_ft = w.until_distance._feet
        scr.winds[i].max_distance_ft = w.MAX_DISTANCE_FEET

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
    s.mach_data = curve.m
    s.cd_data = curve.c
    s.drag_table_size = n
    s.wind_count = nw
    s.look_angle_rad = shot_info.look_angle._rad
    s.barrel_elevation_rad = shot_info.barrel_elevation._rad
    s.barrel_azimuth_rad = shot_info.barrel_azimuth._rad
    s.cant_angle_rad = shot_info.cant_angle._rad
    s.latitude_deg = NAN if shot_info.latitude is None else shot_info.latitude
    s.azimuth_deg = NAN if shot_info.azimuth is None else shot_info.azimuth
    c.cStepMultiplier = cfg.cStepMultiplier
    c.cZeroFindingAccuracy = cfg.cZeroFindingAccuracy
    c.cMinimumVelocity = cfg.cMinimumVelocity
    c.cMaximumDrop = cfg.cMaximumDrop
    c.cMaxIterations = int(cfg.cMaxIterations)
    c.cGravityConstant = cfg.cGravityConstant
    c.cMinimumAltitude = cfg.cMinimumAltitude
    s.method = <BCLIBCFFI_IntegrationMethod>method
    return 0


cdef object _traj(const BCLIBCFFI_TrajectoryData *r):
    cdef int f = r.flag
    flag = _flags.get(f)
    if flag is None:
        flag = _flags[f] = TrajFlag(f)
    # TrajectoryData is a NamedTuple: its fields in order, without the Python-level __new__
    return _tuple_new(_TD, (
        r.time, _feet(r.distance_ft), _fps(r.velocity_fps), r.mach, _feet(r.height_ft), _feet(r.slant_height_ft),
        _rad(r.drop_angle_rad), _feet(r.windage_ft), _rad(r.windage_angle_rad), _feet(r.slant_distance_ft),
        _rad(r.angle_rad), r.density_ratio, r.drag, _ft_lb(r.energy_ft_lb), _lb(r.ogw_lb), flag,
    ))


cdef object _base(const BCLIBCFFI_BaseTrajData *r):
    return BaseTrajData(r.time, Vector(r.px, r.py, r.pz), Vector(r.vx, r.vy, r.vz), r.mach)


cdef int _raise(const BCLIBCFFI_Error *err) except -1:
    msg = (<bytes>err.message).decode("utf-8", "replace")
    if err.code == BCLIBCFFI_ERR_OUT_OF_RANGE:
        raise OutOfRangeError(Distance.Foot(err.f64_0), Distance.Foot(err.f64_1), Angular.Radian(err.f64_2), msg)
    if err.code == BCLIBCFFI_ERR_ZERO_FINDING:
        raise ZeroFindingError(err.f64_0, err.i32_0, Angular.Radian(err.f64_1), msg)
    if err.code == BCLIBCFFI_ERR_INTERCEPTION:
        raise InterceptionError(msg, (None, None))
    raise SolverRuntimeError(msg)


cdef class _DenseSeq:
    """Dense accepted steps of one integrate() call: owns the array the library allocated, items built on access."""
    cdef BCLIBCFFI_DenseStep *p
    cdef int n

    def __dealloc__(self):
        if self.p != NULL:
            BCLIBCFFI_free_base_trajectory(self.p)

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        cdef int i
        if isinstance(idx, slice):
            return [self[j] for j in range(*idx.indices(self.n))]
        i = idx
        if i < 0:
            i += self.n
        if i < 0 or i >= self.n:
            raise IndexError(idx)
        return _base(&self.p[i])


Sequence.register(_DenseSeq)


class _Engine(BaseIntegrationEngine):
    """Native engine: fixed-step (RK4, Euler, Verlet) or adaptive (Cash-Karp, Dormand-Prince, Tsitouras)."""
    _METHOD = 0
    _ADAPTIVE = False
    _relative_tolerance = 0.0
    _absolute_tolerance = 0.0
    DEFAULT_TIME_STEP = 0.0025

    def get_calc_step(self) -> float:
        return self._config.cStepMultiplier * self.DEFAULT_TIME_STEP

    def _native_shot(self, shot_info):
        cdef _Scratch scr = _scratch_of(self)
        _fill_shot(scr, shot_info, self._config, self._METHOD)
        return scr

    def _run(self, shot_info, double range_limit_ft, double range_step_ft, double time_step, filter_flags, dense_output):
        cdef _Scratch scr = _scratch_of(self)
        cdef int rc, i, count, want = 1 if dense_output else 0, method = self._METHOD
        cdef double rtol, atol
        cdef BCLIBCFFI_Shot *shot = &scr.shot
        _fill_shot(scr, shot_info, self._config, method)
        scr.req.range_limit_ft = range_limit_ft
        scr.req.range_step_ft = range_step_ft
        scr.req.time_step = time_step
        scr.req.filter_flags = int(filter_flags)
        if self._ADAPTIVE:
            rtol = self._relative_tolerance
            atol = self._absolute_tolerance
            with nogil:
                rc = BCLIBCFFI_integrate_adaptive_shot(shot, method, rtol, atol, &scr.req, want, &scr.recs, &scr.n,
                                                       &scr.dense, &scr.dn, &scr.reason, &scr.stats, &scr.err)
            self._last_accepted, self._last_rejected = scr.stats.accepted, scr.stats.rejected
        else:
            with nogil:
                rc = BCLIBCFFI_integrate_dense_shot(shot, &scr.req, want, &scr.recs, &scr.n, &scr.dense, &scr.dn,
                                                    &scr.reason, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        count = scr.n
        trajectory = [_traj(&scr.recs[i]) for i in range(count)]
        if count:
            BCLIBCFFI_free_trajectory(scr.recs)
        base_data = None
        cdef _DenseSeq seq
        if dense_output:
            seq = _DenseSeq.__new__(_DenseSeq)
            if scr.dn:
                seq.p = scr.dense
                seq.n = scr.dn
                scr.dense = NULL
            base_data = seq
        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()
        term = _TERMINATION.get(scr.reason)
        error = RangeError(term, trajectory) if term is not None else None
        return HitResult(props, trajectory, base_data, filter_flags != TrajFlag.NONE, error)

    def integrate(self, shot_info, max_range, dist_step=None, time_step=0.0, filter_flags=0, dense_output=False, **kwargs):
        limit = max_range._feet
        return self._run(shot_info, limit, limit if dist_step is None else dist_step._feet, time_step, filter_flags,
                         dense_output)

    def _integrate(self, props, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, **kwargs):
        return self._run(props.shot, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output)

    def integrate_raw_at(self, shot_info, str key_attribute, double target_value):
        if key_attribute not in _KEY:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef int rc, key = _KEY[key_attribute], method = self._METHOD
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_integrate_at_adaptive_shot(&scr.shot, method, rtol, atol, key, target_value, &scr.it,
                                                          &scr.stats, &scr.err)
            else:
                rc = BCLIBCFFI_integrate_at_shot(&scr.shot, key, target_value, &scr.it, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return _base(&scr.it.raw_data), _traj(&scr.it.full_data)

    def zero_angle(self, shot_info, distance):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._METHOD
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_angle_adaptive_shot(&scr.shot, method, rtol, atol, ft, &scr.value,
                                                             &scr.stats, &scr.err)
            else:
                rc = BCLIBCFFI_find_zero_angle_shot(&scr.shot, ft, &scr.value, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return Angular.Radian(scr.value)

    def zero_point(self, shot_info, distance):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._METHOD
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_point_adaptive_shot(&scr.shot, method, rtol, atol, ft, &scr.zp, &scr.stats,
                                                             &scr.err)
            else:
                rc = BCLIBCFFI_find_zero_point_shot(&scr.shot, ft, &scr.zp, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(&scr.zp.point)

    def find_zero_angle(self, shot_info, distance, lofted=False):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._METHOD, lo = 1 if lofted else 0
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_angle_lofted_adaptive_shot(&scr.shot, method, rtol, atol, ft, lo,
                                                                    &scr.value, &scr.stats, &scr.err)
            else:
                rc = BCLIBCFFI_find_zero_angle_lofted_shot(&scr.shot, ft, lo, &scr.value, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return Angular.Radian(scr.value)

    def find_zero_point(self, shot_info, distance, lofted=False):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._METHOD, lo = 1 if lofted else 0
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_point_lofted_adaptive_shot(&scr.shot, method, rtol, atol, ft, lo, &scr.zp,
                                                                    &scr.stats, &scr.err)
            else:
                rc = BCLIBCFFI_find_zero_point_lofted_shot(&scr.shot, ft, lo, &scr.zp, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return Angular.Radian(scr.zp.angle_rad), _traj(&scr.zp.point)

    def find_max_range(self, shot_info, angle_bracket_deg=(0, 90)):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef double lo_deg = angle_bracket_deg[0], hi_deg = angle_bracket_deg[1]
        cdef int rc, method = self._METHOD
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_max_range_adaptive_shot(&scr.shot, method, rtol, atol, lo_deg, hi_deg, &scr.mr,
                                                            &scr.stats, &scr.err)
            else:
                rc = BCLIBCFFI_find_max_range_shot(&scr.shot, lo_deg, hi_deg, &scr.mr, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return Distance.Foot(scr.mr.max_range_ft), Angular.Radian(scr.mr.angle_at_max_rad)

    def find_apex(self, shot_info):
        cdef _Scratch scr = self._native_shot(shot_info)
        cdef int rc, method = self._METHOD
        cdef bint adaptive = self._ADAPTIVE
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_apex_adaptive_shot(&scr.shot, method, rtol, atol, &scr.apex, &scr.stats,
                                                       &scr.err)
            else:
                rc = BCLIBCFFI_find_apex_shot(&scr.shot, &scr.apex, &scr.err)
        if rc != BCLIBCFFI_OK:
            _raise(&scr.err)
        return _traj(&scr.apex)


class _AdaptiveEngine(_Engine):
    """Adaptive engines: per-instance tolerances and the step statistics of the last integrate()."""
    _ADAPTIVE = True

    def __init__(self, config=None):
        rtol = atol = 1e-6
        base = config
        if isinstance(config, dict):
            base = config.copy()
            rtol = base.pop("relative_tolerance", rtol)
            atol = base.pop("absolute_tolerance", atol)
        self.relative_tolerance = rtol
        self.absolute_tolerance = atol
        self._last_accepted, self._last_rejected = 0, 0
        BaseIntegrationEngine.__init__(self, base)

    @property
    def relative_tolerance(self) -> float:
        return self._relative_tolerance

    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("relative_tolerance must be finite and positive")
        self._relative_tolerance = float(value)

    @property
    def absolute_tolerance(self) -> float:
        return self._absolute_tolerance

    @absolute_tolerance.setter
    def absolute_tolerance(self, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError("absolute_tolerance must be finite and non-negative")
        self._absolute_tolerance = float(value)

    def get_step_stats(self):
        return self._last_accepted, self._last_rejected


class NativeEulerIntegrationEngine(_Engine):
    _METHOD = 1
    DEFAULT_TIME_STEP = 0.5


class NativeRK4IntegrationEngine(_Engine):
    _METHOD = 0


class NativeVelocityVerletIntegrationEngine(_Engine):
    _METHOD = 2
    DEFAULT_TIME_STEP = 0.001


class NativeCashKarpIntegrationEngine(_AdaptiveEngine):
    _METHOD = 3


class NativeDormandPrinceIntegrationEngine(_AdaptiveEngine):
    _METHOD = 4


class NativeTsitourasIntegrationEngine(_AdaptiveEngine):
    _METHOD = 5


def _probe(engine, shot_info, int n, str what, double range_ft, int dense):
    """Timing probe: n repetitions of one stage of the integrate path, seconds per call."""
    from time import perf_counter
    cdef _Scratch scr = _scratch_of(engine)
    cdef int i, rc, method = engine._METHOD
    cdef double rtol = engine._relative_tolerance, atol = engine._absolute_tolerance
    cdef BCLIBCFFI_Shot *shot = &scr.shot
    cdef double t0, t1
    _fill_shot(scr, shot_info, engine._config, method)
    scr.req.range_limit_ft = range_ft
    scr.req.range_step_ft = range_ft
    scr.req.time_step = 0.0
    scr.req.filter_flags = 63
    if what == "fill":
        t0 = perf_counter()
        for i in range(n):
            _fill_shot(scr, shot_info, engine._config, method)
        return (perf_counter() - t0) / n
    if what == "call":
        t0 = perf_counter()
        for i in range(n):
            with nogil:
                rc = BCLIBCFFI_integrate_adaptive_shot(shot, method, rtol, atol, &scr.req, dense, &scr.recs, &scr.n,
                                                       &scr.dense, &scr.dn, &scr.reason, &scr.stats, &scr.err)
            if scr.n:
                BCLIBCFFI_free_trajectory(scr.recs)
            if scr.dn:
                BCLIBCFFI_free_base_trajectory(scr.dense)
        return (perf_counter() - t0) / n
    if what == "conv":
        with nogil:
            rc = BCLIBCFFI_integrate_adaptive_shot(shot, method, rtol, atol, &scr.req, dense, &scr.recs, &scr.n,
                                                   &scr.dense, &scr.dn, &scr.reason, &scr.stats, &scr.err)
        t0 = perf_counter()
        for i in range(n):
            lst = [_traj(&scr.recs[j]) for j in range(scr.n)]
        t1 = perf_counter()
        if scr.n:
            BCLIBCFFI_free_trajectory(scr.recs)
        if scr.dn:
            BCLIBCFFI_free_base_trajectory(scr.dense)
        return (t1 - t0) / n, scr.n, scr.dn
