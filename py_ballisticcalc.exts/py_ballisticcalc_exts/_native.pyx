# cython: language_level=3
"""The bclibc engines as Cython over the C ABI of bclibc (bclibc_ffi.h, 2.2), not the C++ API."""
import math
import struct

from libc.math cimport NAN
from libc.stdint cimport int32_t
from cython cimport final
from libc.stdlib cimport free, malloc, realloc
from libc.string cimport memcpy

from py_ballisticcalc_exts._bcffi cimport *

from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, create_base_engine_config
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
        self.m = <double *>malloc((n if n else 1) * sizeof(double))
        self.c = <double *>malloc((n if n else 1) * sizeof(double))
        if self.m == NULL or self.c == NULL:
            free(self.m)
            free(self.c)
            self.m = self.c = NULL
            raise MemoryError()

    def __dealloc__(self):
        free(self.m)
        free(self.c)


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
    _raise_kind(err.code, msg)
    raise SolverRuntimeError(msg)


# ---------------------------------------------------------------------------------------------------------------------
# CythonizedBaseTrajData and CythonizedBaseTrajSeq: the two public buffers of the C++ layer (traj_data.pyx).
# Only the Python side is here: the buffer, the interpolation and the search are C functions of bclibc_ffi.h.
# ---------------------------------------------------------------------------------------------------------------------

cdef int _key_of(str key_attribute) except -1:
    cdef object k = _KEY.get(key_attribute)
    if k is None:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
    return <int>k


cdef int _raise_kind(int32_t code, str msg) except -1:
    """The kinds of error that are not a solver's (bclibc 2.2), as the C++ layer raises them: ValueError for a domain or
    an argument error, IndexError for an index or a value outside the data, RuntimeError for the rest."""
    if code == BCLIBCFFI_ERR_DOMAIN or code == BCLIBCFFI_ERR_INVALID_ARGUMENT:
        raise ValueError(msg)
    if code == BCLIBCFFI_ERR_OUT_OF_BOUNDS:
        raise IndexError(msg)
    if code == BCLIBCFFI_ERR_LOGIC or code == BCLIBCFFI_ERR_RUNTIME:
        raise RuntimeError(msg)
    return 0


cdef int _raise_get(const BCLIBCFFI_Error *err) except -1:
    """The error of get_at / get_at_slant_height (dense_get_at...): the code tells the kinds apart."""
    msg = (<bytes>err.message).decode("utf-8", "replace")
    if err.code == BCLIBCFFI_ERR_OUT_OF_RANGE or err.code == BCLIBCFFI_ERR_INTERCEPTION:
        raise IndexError(msg)
    _raise_kind(err.code, msg)
    raise ValueError(msg)


cdef int _raise_seq(const BCLIBCFFI_Error *err) except -1:
    """The error of a sequence call (interpolation, append)."""
    msg = (<bytes>err.message).decode("utf-8", "replace")
    if err.code == BCLIBCFFI_ERR_OUT_OF_RANGE or err.code == BCLIBCFFI_ERR_INTERCEPTION:
        raise IndexError(msg)
    _raise_kind(err.code, msg)
    raise ValueError(msg)


@final
cdef class CythonizedBaseTrajData:
    cdef BCLIBCFFI_BaseTrajData _d
    __slots__ = ('time', 'position', 'velocity', 'mach')  # for pure python mirror consistency

    def __repr__(self):
        cls_name = self.__class__.__name__

        field_names = self.__slots__
        field_values = self.__iter__()

        content = ", ".join(
            f"{name}={repr(value)}"
            for name, value in zip(field_names, field_values)
        )
        return f"{cls_name}({content})"

    def __str__(self):
        content = ", ".join(repr(value) for value in self)
        return f"({content})"

    def __len__(self):
        return len(self.__slots__)

    def __iter__(self):
        yield self.time
        yield self.position
        yield self.velocity
        yield self.mach

    def __getitem__(self, index):
        """Access to fields by index: self[0] -> time, self[1] -> position, and so on. Indexes and slices."""
        if index == 0:
            return self.time
        elif index == 1:
            return self.position
        elif index == 2:
            return self.velocity
        elif index == 3:
            return self.mach

        # Negative
        elif index == -4:
            return self.time
        elif index == -3:
            return self.position
        elif index == -2:
            return self.velocity
        elif index == -1:
            return self.mach

        # Slices
        elif isinstance(index, slice):
            return (self.time, self.position, self.velocity, self.mach)[index]

        raise IndexError("TrajData index out of range")

    def __eq__(self, other):
        if isinstance(other, CythonizedBaseTrajData):
            return (self.time == other.time and
                    self.position == other.position and
                    self.velocity == other.velocity and
                    self.mach == other.mach)

        elif len(self) == len(other):
            return all(a == b for a, b in zip(self, other))

        return NotImplemented

    @property
    def time(self):
        return self._d.time

    @property
    def mach(self):
        return self._d.mach

    @property
    def position(self):
        return Vector(self._d.px, self._d.py, self._d.pz)

    @property
    def velocity(self):
        return Vector(self._d.vx, self._d.vy, self._d.vz)

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                    CythonizedBaseTrajData p0, CythonizedBaseTrajData p1, CythonizedBaseTrajData p2):
        """PCHIP interpolation of a BaseTrajData point through three points surrounding where key_attribute == value.

        key_attribute: 'time', 'mach' or a component like 'position.x', 'velocity.z' (AttributeError otherwise).
        ZeroDivisionError when two of the points have the same key.
        """
        cdef int key = _key_of(key_attribute)
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBCFFI_Error err
        if BCLIBCFFI_base_traj_interpolate(key, key_value, &p0._d, &p1._d, &p2._d, &out._d, &err) != BCLIBCFFI_OK:
            raise ZeroDivisionError((<bytes>err.message).decode("utf-8", "replace"))
        return out


def make_base_traj_data(double time, double px, double py, double pz, double vx, double vy, double vz, double mach):
    """A CythonizedBaseTrajData of the eight numbers (the test helper of the C++ layer, of the same name)."""
    cdef CythonizedBaseTrajData d = CythonizedBaseTrajData()
    d._d.time = time
    d._d.px = px
    d._d.py = py
    d._d.pz = pz
    d._d.vx = vx
    d._d.vy = vy
    d._d.vz = vz
    d._d.mach = mach
    return d


@final
cdef class CythonizedBaseTrajSeq:
    """Contiguous C buffer of BCLIBCFFI_BaseTrajData points with append and interpolation."""
    cdef BCLIBCFFI_BaseTrajBuf _buf
    # the array is the library's own (the dense steps of integrate()): freed by BCLIBCFFI_free_base_trajectory
    cdef bint _lib

    def __dealloc__(self):
        if self._lib:
            BCLIBCFFI_free_base_trajectory(self._buf.data)
        else:
            BCLIBCFFI_base_traj_buf_free(&self._buf)

    cdef void _adopt(self, BCLIBCFFI_DenseStep *steps, int32_t count) noexcept:
        """Takes the array the library allocated, without copying it."""
        self._buf.data = steps
        self._buf.count = count
        self._buf.capacity = count
        self._lib = True

    cdef int _own(self) except -1:
        """Copies the library's array into one the buffer can grow."""
        cdef BCLIBCFFI_BaseTrajData *mine = <BCLIBCFFI_BaseTrajData *>malloc(
            self._buf.count * sizeof(BCLIBCFFI_BaseTrajData))
        if mine == NULL:
            raise MemoryError()
        memcpy(mine, self._buf.data, self._buf.count * sizeof(BCLIBCFFI_BaseTrajData))
        BCLIBCFFI_free_base_trajectory(self._buf.data)
        self._buf.data = mine
        self._buf.capacity = self._buf.count
        self._lib = False
        return 0

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        cdef BCLIBCFFI_BaseTrajData item = BCLIBCFFI_BaseTrajData(time, px, py, pz, vx, vy, vz, mach)
        cdef BCLIBCFFI_Error err
        if self._lib:
            self._own()
        if BCLIBCFFI_base_traj_buf_append(&self._buf, &item, &err) != BCLIBCFFI_OK:
            raise MemoryError((<bytes>err.message).decode("utf-8", "replace"))

    def reserve(self, int min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        import warnings
        warnings.warn("reserve method deprecated due to auto resources manage")
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")

    def __len__(self):
        return self._buf.count

    def __getitem__(self, Py_ssize_t idx):
        """The point at idx (negative from the end) as CythonizedBaseTrajData."""
        cdef CythonizedBaseTrajData out
        if idx < 0:
            idx += self._buf.count
        if idx < 0 or idx >= self._buf.count:
            raise IndexError("Index out of range")
        out = CythonizedBaseTrajData()
        out._d = self._buf.data[idx]
        return out

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        return self._interpolate_at(idx, _key_of(key_attribute), key_value)

    cdef CythonizedBaseTrajData _interpolate_at(self, Py_ssize_t idx, int key, double key_value):
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBCFFI_Error err
        if BCLIBCFFI_base_traj_interpolate_at(
                self._buf.data, self._buf.count, idx, key, key_value, &out._d, &err) != BCLIBCFFI_OK:
            _raise_seq(&err)
        return out

    def get_at(self, str key_attribute, double key_value, object start_from_time=None):
        """The point where key_attribute == key_value (monotone PCHIP interpolation).

        If start_from_time > 0 the search starts from the first point where time >= start_from_time and goes forward
        or backward by the local direction, as HitResult.get_at() does.
        """
        cdef double t0 = 0.0
        if start_from_time is not None:
            t0 = <double>start_from_time
        return self._get_at(_key_of(key_attribute), key_value, t0)

    cdef CythonizedBaseTrajData _get_at(self, int key, double key_value, double t0):
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBCFFI_Error err
        cdef int32_t rc
        with nogil:
            rc = BCLIBCFFI_dense_get_at(self._buf.data, self._buf.count, key, key_value, t0, &out._d, &err)
        if rc != BCLIBCFFI_OK:
            _raise_get(&err)
        return out

    def get_at_slant_height(self, double look_angle_rad, double value):
        """The point where value == slant height = position.y*cos(a) - position.x*sin(a)."""
        return self._get_at_slant_height(look_angle_rad, value)

    cdef CythonizedBaseTrajData _get_at_slant_height(self, double look_angle_rad, double value):
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBCFFI_Error err
        cdef int32_t rc
        with nogil:
            rc = BCLIBCFFI_dense_get_at_slant_height(
                self._buf.data, self._buf.count, look_angle_rad, value, &out._d, &err)
        if rc != BCLIBCFFI_OK:
            _raise_get(&err)
        return out


cdef class CythonizedBaseIntegrationEngine:
    """Native engine: fixed-step (RK4, Euler, Verlet) or adaptive (Cash-Karp, Dormand-Prince, Tsitouras)."""
    _METHOD = 0
    _ADAPTIVE = False
    DEFAULT_TIME_STEP = 0.0025
    # a cdef class cannot derive from the Python class BaseIntegrationEngine (as the old C++ exts engines): the
    # constants and the attributes the library reads from an engine are repeated here
    APEX_IS_MAX_RANGE_RADIANS = BaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS
    ALLOWED_ZERO_ERROR_FEET = BaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET

    # per-engine C storage, allocated once with the engine and reused by every call
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
    cdef int _method
    cdef bint _adaptive
    cdef double _time_step
    # the step statistics of the last integrate()
    cdef int _last_accepted
    cdef int _last_rejected
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # the numbers of the engine config the hot path reads, cached once in __init__ (_config stays the public attribute)
    cdef double _step_multiplier
    cdef double _zero_finding_accuracy
    cdef double _minimum_velocity
    cdef double _maximum_drop
    cdef int32_t _max_iterations
    cdef double _gravity_constant
    cdef double _minimum_altitude
    cdef double _calc_step_value
    cdef public object _config
    cdef public object gravity_vector

    def __cinit__(self, *args, **kwargs):
        cls = type(self)
        self._method = cls._METHOD
        self._adaptive = cls._ADAPTIVE
        self._time_step = cls.DEFAULT_TIME_STEP
        self.n_wind = 0
        self.winds = NULL
        self.recs = NULL
        self.dense = NULL

    def __dealloc__(self):
        free(self.winds)
        if self.dense != NULL:
            BCLIBCFFI_free_base_trajectory(self.dense)
            self.dense = NULL

    def __init__(self, config=None):
        self._config = create_base_engine_config(config)
        cfg = self._config
        self._step_multiplier = cfg.cStepMultiplier
        self._zero_finding_accuracy = cfg.cZeroFindingAccuracy
        self._minimum_velocity = cfg.cMinimumVelocity
        self._maximum_drop = cfg.cMaximumDrop
        self._max_iterations = int(cfg.cMaxIterations)
        self._gravity_constant = cfg.cGravityConstant
        self._minimum_altitude = cfg.cMinimumAltitude
        self._calc_step_value = self._step_multiplier * self._time_step
        self.gravity_vector = Vector(0.0, self._gravity_constant, 0.0)

    def _init_trajectory(self, shot):
        props = ShotProps.from_shot(shot)
        props.calc_step = self.get_calc_step()
        return props

    def get_calc_step(self) -> float:
        return self._calc_step()

    cdef double _calc_step(self):
        return self._calc_step_value

    cdef int _init_shot(self, shot_info) except -1:
        cdef BCLIBCFFI_Shot *s = &self.shot
        cdef BCLIBCFFI_Config *c = &s.config
        cdef int i, nt, nw
        cdef _Curve curve
        cdef BCLIBCFFI_Wind *tmp
        ammo = shot_info.ammo
        dm = ammo.dm
        atmo = shot_info.atmo
        weapon = shot_info.weapon
        table = dm.drag_table
        nt = len(table)
        # the table is copied on every call, as the exts engine does (bind.pyx): no cache of the table
        if self.custom is None or self.custom.n != nt:
            self.custom = _Curve(nt)
        curve = self.custom
        i = 0
        for point in table:
            curve.m[i] = point.Mach
            curve.c[i] = point.CD
            i += 1

        winds = shot_info.winds
        nw = len(winds)
        if nw != self.n_wind:
            tmp = <BCLIBCFFI_Wind *>realloc(self.winds, (nw if nw else 1) * sizeof(BCLIBCFFI_Wind))
            if tmp == NULL:
                raise MemoryError()
            self.winds = tmp
            self.n_wind = nw
            s.winds = self.winds if nw else NULL
        for i in range(nw):
            w = winds[i]
            self.winds[i].velocity_fps = w.velocity._fps
            self.winds[i].direction_from_rad = w.direction_from._rad
            self.winds[i].until_distance_ft = w.until_distance._feet
            self.winds[i].max_distance_ft = w.MAX_DISTANCE_FEET

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
        s.drag_table_size = nt
        s.wind_count = nw
        s.look_angle_rad = shot_info.look_angle._rad
        s.barrel_elevation_rad = shot_info.barrel_elevation._rad
        s.barrel_azimuth_rad = shot_info.barrel_azimuth._rad
        s.cant_angle_rad = shot_info.cant_angle._rad
        s.latitude_deg = NAN if shot_info.latitude is None else shot_info.latitude
        s.azimuth_deg = NAN if shot_info.azimuth is None else shot_info.azimuth
        c.cStepMultiplier = self._step_multiplier
        c.cZeroFindingAccuracy = self._zero_finding_accuracy
        c.cMinimumVelocity = self._minimum_velocity
        c.cMaximumDrop = self._maximum_drop
        c.cMaxIterations = self._max_iterations
        c.cGravityConstant = self._gravity_constant
        c.cMinimumAltitude = self._minimum_altitude
        s.method = <BCLIBCFFI_IntegrationMethod>self._method
        return 0

    cdef object _run(self, shot_info, double range_limit_ft, double range_step_ft, double time_step, filter_flags,
                     dense_output):
        cdef int rc, i, count, want = 1 if dense_output else 0, method = self._method, ff = filter_flags
        cdef double rtol, atol
        cdef BCLIBCFFI_Shot *shot = &self.shot
        # the stats of this call only: zeroed in the scratch too, since a failed adaptive call leaves them untouched
        self._last_accepted = self._last_rejected = 0
        self.stats.accepted = self.stats.rejected = 0
        if self.dense != NULL:
            BCLIBCFFI_free_base_trajectory(self.dense)
            self.dense = NULL
        self.recs = NULL
        self.n = self.dn = 0
        self._init_shot(shot_info)
        self.req.range_limit_ft = range_limit_ft
        self.req.range_step_ft = range_step_ft
        self.req.time_step = time_step
        self.req.filter_flags = ff
        if self._adaptive:
            rtol = self._relative_tolerance
            atol = self._absolute_tolerance
            with nogil:
                rc = BCLIBCFFI_integrate_adaptive_shot(shot, method, rtol, atol, &self.req, want, &self.recs, &self.n,
                                                       &self.dense, &self.dn, &self.reason, &self.stats, &self.err)
            self._last_accepted, self._last_rejected = self.stats.accepted, self.stats.rejected
        else:
            with nogil:
                rc = BCLIBCFFI_integrate_dense_shot_stats(shot, &self.req, want, &self.recs, &self.n, &self.dense,
                                                          &self.dn, &self.reason, &self.stats, &self.err)
            self._last_accepted, self._last_rejected = self.stats.accepted, self.stats.rejected
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        count = self.n
        try:
            trajectory = [_traj(&self.recs[i]) for i in range(count)]
        finally:
            if count:
                BCLIBCFFI_free_trajectory(self.recs)
            self.recs = NULL
        base_data = None
        cdef CythonizedBaseTrajSeq seq
        if dense_output:
            seq = CythonizedBaseTrajSeq()
            if self.dn:
                seq._adopt(self.dense, self.dn)
                self.dense = NULL
            base_data = seq
        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self._calc_step()
        term = _TERMINATION.get(self.reason)
        error = RangeError(term, trajectory) if term is not None else None
        return HitResult(props, trajectory, base_data, filter_flags != TrajFlag.NONE, error)

    def integrate(self, shot_info, max_range, dist_step=None, time_step=0.0, filter_flags=0, dense_output=False,
                  **kwargs):
        cdef double limit = max_range._feet
        cdef double step = limit if dist_step is None else dist_step._feet
        return self._run(shot_info, limit, step, time_step, filter_flags, dense_output)

    def _integrate(self, props, double range_limit_ft, double range_step_ft, double time_step, filter_flags,
                   dense_output, **kwargs):
        return self._run(props.shot, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output)

    def integrate_raw_at(self, shot_info, str key_attribute, double target_value):
        if key_attribute not in _KEY:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        self._init_shot(shot_info)
        cdef int rc, key = _KEY[key_attribute], method = self._method
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_integrate_at_adaptive_shot(&self.shot, method, rtol, atol, key, target_value, &self.it,
                                                          &self.stats, &self.err)
            else:
                rc = BCLIBCFFI_integrate_at_shot(&self.shot, key, target_value, &self.it, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        # the raw point is a CythonizedBaseTrajData, as in the exts engine (base_engine.pyx integrate_raw_at)
        raw = CythonizedBaseTrajData()
        raw._d = self.it.raw_data
        return raw, _traj(&self.it.full_data)

    def zero_angle(self, shot_info, distance):
        self._init_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._method
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_angle_adaptive_shot(&self.shot, method, rtol, atol, ft, &self.value,
                                                             &self.stats, &self.err)
            else:
                rc = BCLIBCFFI_find_zero_angle_shot(&self.shot, ft, &self.value, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return Angular.Radian(self.value)

    def zero_point(self, shot_info, distance):
        self._init_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._method
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_point_adaptive_shot(&self.shot, method, rtol, atol, ft, &self.zp, &self.stats,
                                                             &self.err)
            else:
                rc = BCLIBCFFI_find_zero_point_shot(&self.shot, ft, &self.zp, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return Angular.Radian(self.zp.angle_rad), _traj(&self.zp.point)

    def find_zero_angle(self, shot_info, distance, lofted=False):
        self._init_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._method, lo = 1 if lofted else 0
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_angle_lofted_adaptive_shot(&self.shot, method, rtol, atol, ft, lo,
                                                                    &self.value, &self.stats, &self.err)
            else:
                rc = BCLIBCFFI_find_zero_angle_lofted_shot(&self.shot, ft, lo, &self.value, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return Angular.Radian(self.value)

    def find_zero_point(self, shot_info, distance, lofted=False):
        self._init_shot(shot_info)
        cdef double ft = distance._feet
        cdef int rc, method = self._method, lo = 1 if lofted else 0
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_zero_point_lofted_adaptive_shot(&self.shot, method, rtol, atol, ft, lo, &self.zp,
                                                                    &self.stats, &self.err)
            else:
                rc = BCLIBCFFI_find_zero_point_lofted_shot(&self.shot, ft, lo, &self.zp, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return Angular.Radian(self.zp.angle_rad), _traj(&self.zp.point)

    def find_max_range(self, shot_info, angle_bracket_deg=(0, 90)):
        self._init_shot(shot_info)
        cdef double lo_deg = angle_bracket_deg[0], hi_deg = angle_bracket_deg[1]
        cdef int rc, method = self._method
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_max_range_adaptive_shot(&self.shot, method, rtol, atol, lo_deg, hi_deg, &self.mr,
                                                            &self.stats, &self.err)
            else:
                rc = BCLIBCFFI_find_max_range_shot(&self.shot, lo_deg, hi_deg, &self.mr, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return Distance.Foot(self.mr.max_range_ft), Angular.Radian(self.mr.angle_at_max_rad)

    def find_apex(self, shot_info):
        self._init_shot(shot_info)
        cdef int rc, method = self._method
        cdef bint adaptive = self._adaptive
        cdef double rtol = self._relative_tolerance, atol = self._absolute_tolerance
        with nogil:
            if adaptive:
                rc = BCLIBCFFI_find_apex_adaptive_shot(&self.shot, method, rtol, atol, &self.apex, &self.stats,
                                                       &self.err)
            else:
                rc = BCLIBCFFI_find_apex_shot(&self.shot, &self.apex, &self.err)
        if rc != BCLIBCFFI_OK:
            _raise(&self.err)
        return _traj(&self.apex)

    def get_step_stats(self):
        return self._last_accepted, self._last_rejected

    @property
    def integration_step_count(self):
        """The steps of the last integration, as the exts engine's counter. The C ABI reports them per call: the
        accepted steps of an adaptive call, the steps of BCLIBCFFI_integrate_dense_shot_stats for a fixed-step one."""
        return self._last_accepted


cdef class _AdaptiveEngine(CythonizedBaseIntegrationEngine):
    """Adaptive engines: per-instance tolerances and the step statistics of the last integrate()."""
    _ADAPTIVE = True

    def __cinit__(self, *args, **kwargs):
        self._relative_tolerance = self._absolute_tolerance = 1e-6

    def __init__(self, config=None):
        rtol = atol = 1e-6
        base = config
        if isinstance(config, dict):
            base = config.copy()
            rtol = base.pop("relative_tolerance", rtol)
            atol = base.pop("absolute_tolerance", atol)
        self.relative_tolerance = rtol
        self.absolute_tolerance = atol
        CythonizedBaseIntegrationEngine.__init__(self, base)

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


cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    _METHOD = 1
    DEFAULT_TIME_STEP = 0.5


cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    _METHOD = 0


cdef class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine):
    _METHOD = 2
    DEFAULT_TIME_STEP = 0.001


cdef class CythonizedCashKarpIntegrationEngine(_AdaptiveEngine):
    _METHOD = 3


cdef class CythonizedDormandPrinceIntegrationEngine(_AdaptiveEngine):
    _METHOD = 4


cdef class CythonizedTsitourasIntegrationEngine(_AdaptiveEngine):
    _METHOD = 5
