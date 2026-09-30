"""
Header file for traj_data.pyx - C Buffer Trajectory Sequence
"""

from libcpp.vector cimport vector
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag
)
from py_ballisticcalc_exts.interp cimport BCLIBC_InterpMethod

# bclibc no longer throws: every fallible bclibc::BCLIBC_BaseTrajData /
# BCLIBC_BaseTrajSeq / BCLIBC_TrajectoryData method returns a Result
# (std::variant<BCLIBC_BaseError, T>) instead. Cython has no convenient binding
# for std::variant, so each fallible call gets a tiny plain-signature wrapper
# here (self-contained in this .cpp: the "traj_data" extension does not link
# py_bind.cpp) that checks has_error() and sets the equivalent Python
# exception via PyErr_SetString before returning a sentinel, matching what
# the old "except +<PyExc>" declarations used to do automatically for a
# thrown C++ exception.
cdef extern from *:
    """
    #include "bclibc/traj_data.hpp"
    #include <Python.h>
    #include <variant>
    #include <type_traits>

    namespace {
        static inline const char *bclibc_error_what(const bclibc::BCLIBC_BaseError &error) {
            return std::visit([](const auto &e) { return e.what(); }, error);
        }

        // Mirrors Cython's own default "except +" mapping for the std:: exceptions bclibc's
        // BCLIBC_BaseError alternatives replace (domain_error/invalid_argument -> ValueError,
        // out_of_range -> IndexError, everything else -> RuntimeError), so callers that used
        // to rely on that automatic translation (e.g. catching IndexError from a bad index)
        // keep seeing the same Python exception type.
        static void raise_bclibc_error(const bclibc::BCLIBC_BaseError &error) {
            std::visit([](const auto &e) {
                using T = std::decay_t<decltype(e)>;
                if constexpr (std::is_same_v<T, bclibc::BCLIBC_OutOfRangeError>)
                    PyErr_SetString(PyExc_IndexError, e.what());
                else if constexpr (std::is_same_v<T, bclibc::BCLIBC_DomainError> ||
                                    std::is_same_v<T, bclibc::BCLIBC_InvalidArgumentError>)
                    PyErr_SetString(PyExc_ValueError, e.what());
                else
                    PyErr_SetString(PyExc_RuntimeError, e.what());
            }, error);
        }

        static bool py_base_traj_interpolate(
            bclibc::BCLIBC_BaseTrajData_InterpKey key_kind, double key_value,
            const bclibc::BCLIBC_BaseTrajData &p0, const bclibc::BCLIBC_BaseTrajData &p1,
            const bclibc::BCLIBC_BaseTrajData &p2, bclibc::BCLIBC_BaseTrajData &out)
        {
            auto result = bclibc::BCLIBC_BaseTrajData::interpolate(key_kind, key_value, p0, p1, p2, out);
            if (bclibc::has_error(result))
            {
                PyErr_SetString(PyExc_ZeroDivisionError, bclibc_error_what(std::get<bclibc::BCLIBC_BaseError>(result)));
                return 0;
            }
            return 1;
        }

        static bool py_traj_seq_get_at(
            bclibc::BCLIBC_BaseTrajSeq &seq, bclibc::BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value, double start_from_time, bclibc::BCLIBC_BaseTrajData &out)
        {
            auto result = seq.get_at(key_kind, key_value, start_from_time, out);
            if (bclibc::has_error(result))
            {
                raise_bclibc_error(std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_traj_seq_get_at_slant_height(
            bclibc::BCLIBC_BaseTrajSeq &seq, double look_angle_rad, double value,
            bclibc::BCLIBC_BaseTrajData &out)
        {
            auto result = seq.get_at_slant_height(look_angle_rad, value, out);
            if (bclibc::has_error(result))
            {
                raise_bclibc_error(std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_traj_seq_interpolate_at(
            bclibc::BCLIBC_BaseTrajSeq &seq, Py_ssize_t idx, bclibc::BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value, bclibc::BCLIBC_BaseTrajData &out)
        {
            auto result = seq.interpolate_at(idx, key_kind, key_value, out);
            if (bclibc::has_error(result))
            {
                raise_bclibc_error(std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            return 1;
        }

        static const bclibc::BCLIBC_BaseTrajData *py_traj_seq_getitem(
            const bclibc::BCLIBC_BaseTrajSeq &seq, Py_ssize_t idx)
        {
            auto result = seq[idx];
            if (bclibc::has_error(result))
            {
                raise_bclibc_error(std::get<bclibc::BCLIBC_BaseError>(result));
                return nullptr;
            }
            return &std::get<std::reference_wrapper<const bclibc::BCLIBC_BaseTrajData>>(result).get();
        }

        static bool py_trajectory_data_from_base(
            const bclibc::BCLIBC_ShotProps &props, const bclibc::BCLIBC_BaseTrajData &data,
            bclibc::BCLIBC_TrajFlag flag, bclibc::BCLIBC_TrajectoryData &out)
        {
            auto result = bclibc::BCLIBC_TrajectoryData::from_base(props, data, flag);
            if (bclibc::has_error(result))
            {
                raise_bclibc_error(std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            out = std::get<bclibc::BCLIBC_TrajectoryData>(result);
            return 1;
        }
    }
    """
    bint py_base_traj_interpolate(
        BCLIBC_BaseTrajData_InterpKey, double,
        const BCLIBC_BaseTrajData&, const BCLIBC_BaseTrajData&, const BCLIBC_BaseTrajData&,
        BCLIBC_BaseTrajData&) except 0
    bint py_traj_seq_get_at(
        BCLIBC_BaseTrajSeq&, BCLIBC_BaseTrajData_InterpKey, double, double, BCLIBC_BaseTrajData&) except 0
    bint py_traj_seq_get_at_slant_height(
        BCLIBC_BaseTrajSeq&, double, double, BCLIBC_BaseTrajData&) except 0
    bint py_traj_seq_interpolate_at(
        BCLIBC_BaseTrajSeq&, Py_ssize_t, BCLIBC_BaseTrajData_InterpKey, double, BCLIBC_BaseTrajData&) except 0
    const BCLIBC_BaseTrajData* py_traj_seq_getitem(const BCLIBC_BaseTrajSeq&, Py_ssize_t) except NULL
    bint py_trajectory_data_from_base(
        const BCLIBC_ShotProps&, const BCLIBC_BaseTrajData&, BCLIBC_TrajFlag, BCLIBC_TrajectoryData&) except 0


cdef extern from "include/bclibc/traj_data.hpp" namespace "bclibc" nogil:

    cdef enum class BCLIBC_BaseTrajData_InterpKey:
        TIME
        MACH
        POS_X
        POS_Y
        POS_Z
        VEL_X
        VEL_Y
        VEL_Z

    cdef cppclass BCLIBC_BaseTrajData:
        double time
        double px
        double py
        double pz
        double vx
        double vy
        double vz
        double mach

        BCLIBC_BaseTrajData() except +
        BCLIBC_BaseTrajData(
            double time,
            double px,
            double py,
            double pz,
            double vx,
            double vy,
            double vz,
            double mach
        ) except +

        BCLIBC_BaseTrajData(
            double time,
            const BCLIBC_V3dT &position,
            const BCLIBC_V3dT &velocity,
            double mach
        ) except +

        BCLIBC_V3dT position() const
        BCLIBC_V3dT velocity() const

        double operator[](BCLIBC_BaseTrajData_InterpKey key_kind) const
        double slant_val_buf(double ca, double sa) const
        # static interpolate() now returns a Result; called only through
        # py_base_traj_interpolate() declared above.

    cdef cppclass BCLIBC_BaseTrajDataHandlerInterface:
        void handle(const BCLIBC_BaseTrajData &data) except +
        void insert_handler(vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator position,
                            BCLIBC_BaseTrajDataHandlerInterface *handler) except +
        vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator begin()
        vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator end()

    cdef cppclass BCLIBC_BaseTrajDataHandlerCompositor(BCLIBC_BaseTrajDataHandlerInterface):
        BCLIBC_BaseTrajDataHandlerCompositor() except +
        void handle(const BCLIBC_BaseTrajData& data) except +
        void add_handler(BCLIBC_BaseTrajDataHandlerInterface* handler) except +

    cdef cppclass BCLIBC_BaseTrajSeq(BCLIBC_BaseTrajDataHandlerInterface):

        BCLIBC_BaseTrajSeq() except +

        void append(
            const BCLIBC_BaseTrajData &data
        ) except +
        Py_ssize_t get_length() const
        Py_ssize_t get_capacity() const
        # interpolate_at/get_at_slant_height/get_at/operator[] all now return a Result
        # (bclibc::has_error()) instead of throwing/returning by reference; called only
        # through the py_traj_seq_*() wrappers declared above.

    cdef enum class BCLIBC_TrajectoryData_InterpKey:
        pass

    cdef cppclass BCLIBC_FlaggedData:
        BCLIBC_BaseTrajData data
        BCLIBC_TrajFlag flag

    # --- C++ Class BCLIBC_TrajectoryData ---
    cdef cppclass BCLIBC_TrajectoryData:
        double time
        double distance_ft
        double velocity_fps
        double mach
        double height_ft
        double slant_height_ft
        double drop_angle_rad
        double windage_ft
        double windage_angle_rad
        double slant_distance_ft
        double angle_rad
        double density_ratio
        double drag
        double energy_ft_lb
        double ogw_lb
        BCLIBC_TrajFlag flag

        BCLIBC_TrajectoryData() except +
        # The direct (props, ..., flag) constructors and the static interpolate() are gone from
        # bclibc: both are now BCLIBC_TrajectoryData::from_base()/::interpolate() returning a
        # Result. Only from_base(props, BCLIBC_BaseTrajData, flag) is used from Cython (_find_apex),
        # via the py_trajectory_data_from_base() wrapper above.


cdef class CythonizedBaseTrajSeq:
    cdef BCLIBC_BaseTrajSeq _this


cdef class CythonizedBaseTrajData:
    cdef BCLIBC_BaseTrajData _this


cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
cdef list TrajectoryData_list_from_cpp(const vector[BCLIBC_TrajectoryData] &records)
