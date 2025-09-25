"""
Lightweight Cython data types for trajectory rows and interpolation helpers.

This module mirrors a subset of the Python API in py_ballisticcalc.trajectory_data:
 - BaseTrajDataT: minimal row with time, position (V3dT), velocity (V3dT), mach.
 - TrajectoryDataT: Python-facing richer row used mainly for formatting or tests.
 - interpolate_3_pt / interpolate_2_pt: monotone PCHIP and linear helpers.

Primary producer/consumer is the Cython engines which operate on a dense C buffer
and convert to these types as needed for interpolation or presentation.
"""
from cython cimport final
from py_ballisticcalc_exts.v3d cimport V3dT, set
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t

from py_ballisticcalc.vector import Vector
import py_ballisticcalc.unit as pyunit


# Helper functions to create unit objects
cdef object _new_feet(double val):
    return pyunit.Distance(float(val), pyunit.Unit.Foot)
    
cdef object _new_fps(double val):
    return pyunit.Velocity(float(val), pyunit.Unit.FPS)
    
cdef object _new_rad(double val):
    return pyunit.Angular(float(val), pyunit.Unit.Radian)
    
cdef object _new_ft_lb(double val):
    return pyunit.Energy(float(val), pyunit.Unit.FootPound)
    
cdef object _new_lb(double val):
    return pyunit.Weight(float(val), pyunit.Unit.Pound)

# Additional angular helper for MOA-based fields
cdef object _new_moa(double val):
    return pyunit.Angular(float(val), pyunit.Unit.MOA)

cdef object _v3d_to_vector(V3dT v):
    """Convert C V3dT -> Python Vector"""
    return Vector(<float>v.x, <float>v.y, <float>v.z)

cdef inline int _sign(double a) noexcept nogil:
    return 1 if a > 0 else (-1 if a < 0 else 0)

cdef inline void _sort3(double* xs, double* ys) noexcept nogil:
    cdef int i, j, min_idx
    cdef double tx, ty
    for i in range(2):
        min_idx = i
        for j in range(i+1, 3):
            if xs[j] < xs[min_idx]:
                min_idx = j
        if min_idx != i:
            tx = xs[i]; xs[i] = xs[min_idx]; xs[min_idx] = tx
            ty = ys[i]; ys[i] = ys[min_idx]; ys[min_idx] = ty

cdef inline void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                                double* m0, double* m1, double* m2) noexcept nogil:
    cdef double h0 = x1 - x0
    cdef double h1 = x2 - x1
    cdef double d0 = (y1 - y0) / h0
    cdef double d1 = (y2 - y1) / h1
    cdef double m1l
    cdef double w1
    cdef double w2
    cdef double m0l
    cdef double m2l
    if _sign(d0) * _sign(d1) <= 0:
        m1l = 0.0
    else:
        w1 = 2.0 * h1 + h0
        w2 = h1 + 2.0 * h0
        m1l = (w1 + w2) / (w1 / d0 + w2 / d1)
    m0l = ((2.0 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
    if _sign(m0l) != _sign(d0):
        m0l = 0.0
    elif abs(m0l) > 3.0 * abs(d0):
        m0l = 3.0 * d0
    m2l = ((2.0 * h1 + h0) * d1 - h1 * d0) / (h0 + h1)
    if _sign(m2l) != _sign(d1):
        m2l = 0.0
    elif abs(m2l) > 3.0 * abs(d1):
        m2l = 3.0 * d1
    m0[0] = m0l; m1[0] = m1l; m2[0] = m2l

cdef inline double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1) noexcept nogil:
    cdef double h = xk1 - xk
    cdef double t = (x - xk) / h
    cdef double t2 = t * t
    cdef double t3 = t2 * t
    return (
        (2.0 * t3 - 3.0 * t2 + 1.0) * yk
        + (t3 - 2.0 * t2 + t) * (mk * h)
        + (-2.0 * t3 + 3.0 * t2) * yk1
        + (t3 - t2) * (mk1 * h)
    )

cpdef double interpolate_3_pt(double x, double x0, double y0, double x1, double y1, double x2, double y2):
    cdef double xs[3]
    cdef double ys[3]
    xs[0] = x0; xs[1] = x1; xs[2] = x2
    ys[0] = y0; ys[1] = y1; ys[2] = y2
    _sort3(&xs[0], &ys[0])
    x0 = xs[0]; x1 = xs[1]; x2 = xs[2]
    y0 = ys[0]; y1 = ys[1]; y2 = ys[2]
    cdef double m0, m1, m2
    _pchip_slopes3(x0, y0, x1, y1, x2, y2, &m0, &m1, &m2)
    if x <= x1:
        return _hermite(x, x0, x1, y0, y1, m0, m1)
    else:
        return _hermite(x, x1, x2, y1, y2, m1, m2)

cpdef double interpolate_2_pt(double x, double x0, double y0, double x1, double y1):
    if x1 == x0:
        raise ZeroDivisionError("Duplicate x for linear interpolation")
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, double time, V3dT position, V3dT velocity, double mach):
        self.time = time
        self._position = position
        self._velocity = velocity
        self.mach = mach

    # Hot-path C accessors (used by Cython code directly)
    cdef V3dT c_position(self):
        return self._position

    cdef V3dT c_velocity(self):
        return self._velocity

    # Python-facing properties return Vector, not dict
    @property
    def position(self):
        return _v3d_to_vector(self._position)

    @property
    def velocity(self):
        return _v3d_to_vector(self._velocity)

    # Back-compat names used elsewhere in ext code
    @property
    def position_vector(self):
        return _v3d_to_vector(self._position)

    @property
    def velocity_vector(self):
        return _v3d_to_vector(self._velocity)

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                   object p0, object p1, object p2):
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach', or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (BaseTrajDataT): Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        cdef:
            double x0, x1, x2
            double time, px, py, pz, vx, vy, vz, mach
            BaseTrajDataT _p0
            BaseTrajDataT _p1
            BaseTrajDataT _p2

        _p0 = <BaseTrajDataT> p0
        _p1 = <BaseTrajDataT> p1
        _p2 = <BaseTrajDataT> p2

        # Determine independent variable values from key_attribute
        if key_attribute == 'time':
            x0 = _p0.time
            x1 = _p1.time
            x2 = _p2.time
        elif key_attribute == 'mach':
            x0 = _p0.mach
            x1 = _p1.mach
            x2 = _p2.mach
        elif key_attribute == 'position.x':
            x0 = _p0._position.x
            x1 = _p1._position.x
            x2 = _p2._position.x
        elif key_attribute == 'position.y':
            x0 = _p0._position.y
            x1 = _p1._position.y
            x2 = _p2._position.y
        elif key_attribute == 'position.z':
            x0 = _p0._position.z
            x1 = _p1._position.z
            x2 = _p2._position.z
        elif key_attribute == 'velocity.x':
            x0 = _p0._velocity.x
            x1 = _p1._velocity.x
            x2 = _p2._velocity.x
        elif key_attribute == 'velocity.y':
            x0 = _p0._velocity.y
            x1 = _p1._velocity.y
            x2 = _p2._velocity.y
        elif key_attribute == 'velocity.z':
            x0 = _p0._velocity.z
            x1 = _p1._velocity.z
            x2 = _p2._velocity.z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        # Guard against degenerate segments
        if x0 == x1 or x0 == x2 or x1 == x2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        # Helper for scalar interpolation using PCHIP
        def _interp(double y0, double y1, double y2) -> double:
            return interpolate_3_pt(key_value, x0, y0, x1, y1, x2, y2)

        # Interpolate all scalar fields
        time = key_value if key_attribute == 'time' else _interp(_p0.time, _p1.time, _p2.time)
        px = _interp(_p0._position.x, _p1._position.x, _p2._position.x)
        py = _interp(_p0._position.y, _p1._position.y, _p2._position.y)
        pz = _interp(_p0._position.z, _p1._position.z, _p2._position.z)
        vx = _interp(_p0._velocity.x, _p1._velocity.x, _p2._velocity.x)
        vy = _interp(_p0._velocity.y, _p1._velocity.y, _p2._velocity.y)
        vz = _interp(_p0._velocity.z, _p1._velocity.z, _p2._velocity.z)
        mach = key_value if key_attribute == 'mach' else _interp(_p0.mach, _p1.mach, _p2.mach)

        # Construct the resulting BaseTrajDataT
        return BaseTrajDataT(time, set(px, py, pz), set(vx, vy, vz), mach)


cdef BaseTrajDataT BaseTrajDataT_create(double time, V3dT position, V3dT velocity, double mach):
    return BaseTrajDataT(time, position, velocity, mach)

# Small Python factory for tests and convenience
def make_base_traj_data(double time, double px, double py, double pz,
                        double vx, double vy, double vz, double mach):
    return BaseTrajDataT(time, set(px, py, pz), set(vx, vy, vz), mach)

@final
cdef class TrajectoryDataT:
    __slots__ = ('time', 'distance', 'velocity',
                 'mach', 'height', 'slant_height', 'drop_angle',
                 'windage', 'windage_angle', 'slant_distance',
                 'angle', 'density_ratio', 'drag', 'energy', 'ogw', 'flag')
    _fields = __slots__

    def __cinit__(self,
                  double time,
                  object distance,
                  object velocity,
                  double mach,
                  object height,
                  object slant_height,
                  object drop_angle,
                  object windage,
                  object windage_angle,
                  object slant_distance,
                  object angle,
                  double density_ratio,
                  double drag,
                  object energy,
                  object ogw,
                  int flag):
        self.time = time
        self.distance = distance
        self.velocity = velocity
        self.mach = mach
        self.height = height
        self.slant_height = slant_height
        self.drop_angle = drop_angle
        self.windage = windage
        self.windage_angle = windage_angle
        self.slant_distance = slant_distance
        self.angle = angle
        self.density_ratio = density_ratio
        self.drag = drag
        self.energy = energy
        self.ogw = ogw
        self.flag = flag

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                    TrajectoryDataT t0, TrajectoryDataT t1, TrajectoryDataT t2,
                    int flag):
        """
        Interpolate a TrajectoryDataT using PCHIP (monotone Hermite) for all fields.

        key_attribute: 'time', 'mach', or 'slant_height' (feet raw value).
        key_value: location at which to interpolate (raw units if dimensioned).
        """
        cdef:
            double x0, x1, x2
            double time, mach, density_ratio, drag
            object distance, velocity, height, slant_height, drop_angle
            object windage, windage_angle, slant_distance, angle, energy, ogw

        if key_attribute == 'time':
            x0, x1, x2 = t0.time, t1.time, t2.time
        elif key_attribute == 'mach':
            x0, x1, x2 = t0.mach, t1.mach, t2.mach
        elif key_attribute == 'slant_height':
            x0, x1, x2 = t0.slant_height._feet, t1.slant_height._feet, t2.slant_height._feet
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        time = key_value if key_attribute == 'time' else interpolate_3_pt(key_value, x0, t0.time, x1, t1.time, x2, t2.time)
        mach = key_value if key_attribute == 'mach' else interpolate_3_pt(key_value, x0, t0.mach, x1, t1.mach, x2, t2.mach)

        distance = _new_feet(interpolate_3_pt(key_value, x0, t0.distance._feet, x1, t1.distance._feet, x2, t2.distance._feet))
        velocity = _new_fps(interpolate_3_pt(key_value, x0, t0.velocity._fps, x1, t1.velocity._fps, x2, t2.velocity._fps))
        height = _new_feet(interpolate_3_pt(key_value, x0, t0.height._feet, x1, t1.height._feet, x2, t2.height._feet))
        slant_height = _new_feet(interpolate_3_pt(key_value, x0, t0.slant_height._feet, x1, t1.slant_height._feet, x2, t2.slant_height._feet))
        drop_angle = _new_moa(interpolate_3_pt(key_value, x0, t0.drop_angle._moa, x1, t1.drop_angle._moa, x2, t2.drop_angle._moa))
        windage = _new_feet(interpolate_3_pt(key_value, x0, t0.windage._feet, x1, t1.windage._feet, x2, t2.windage._feet))
        windage_angle = _new_moa(interpolate_3_pt(key_value, x0, t0.windage_angle._moa, x1, t1.windage_angle._moa, x2, t2.windage_angle._moa))
        slant_distance = _new_feet(interpolate_3_pt(key_value, x0, t0.slant_distance._feet, x1, t1.slant_distance._feet, x2, t2.slant_distance._feet))
        angle = _new_rad(interpolate_3_pt(key_value, x0, t0.angle._rad, x1, t1.angle._rad, x2, t2.angle._rad))
        density_ratio = interpolate_3_pt(key_value, x0, t0.density_ratio, x1, t1.density_ratio, x2, t2.density_ratio)
        drag = interpolate_3_pt(key_value, x0, t0.drag, x1, t1.drag, x2, t2.drag)
        energy = _new_ft_lb(interpolate_3_pt(key_value, x0, t0.energy._ft_lb, x1, t1.energy._ft_lb, x2, t2.energy._ft_lb))
        ogw = _new_lb(interpolate_3_pt(key_value, x0, t0.ogw._lb, x1, t1.ogw._lb, x2, t2.ogw._lb))

        return TrajectoryDataT(time, distance, velocity, mach, height, slant_height,
                               drop_angle, windage, windage_angle, slant_distance,
                               angle, density_ratio, drag, energy, ogw,
                               <TrajFlag_t>flag)
