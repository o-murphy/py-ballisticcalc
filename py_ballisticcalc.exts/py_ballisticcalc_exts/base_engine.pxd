# pxd for py_ballisticcalc_exts.base_engine

from libcpp.vector cimport vector
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_Config,
    BCLIBC_ShotProps,
    BCLIBC_WindSock,
    BCLIBC_TrajFlag,
    BCLIBC_TerminationReason,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport (
    BCLIBC_BaseTrajSeq,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
    BCLIBC_BaseTrajData_InterpKey,
    BCLIBC_BaseTrajDataHandlerInterface
)


cdef extern from "<functional>" namespace "std":
    cdef cppclass function[F]:
        function() except +
        function(F *f_ptr) except +
        function(const function[F]& other) except +
        function(function[F]&& other)
        function[F]& operator=(F *f_ptr) except +
        function[F]& operator=(const function[F]& other) except +
        function[F]& operator=(function[F]&& other)
        # Lets integrate_func be assigned a stateful integrator functor
        # (e.g. BCLIBC_CashKarpIntegrator) directly, by value.
        function[F]& operator=[U](U u) except +
        bint operator bool() const
        # Pointer to std::function's own internal copy of the callable it
        # holds, if it was constructed/assigned as exactly T (nullptr
        # otherwise). Used to get back at a stateful integrator's tolerances
        # and accepted/rejected-step counters *after* assigning it into
        # integrate_func by value above -- std::function copies whatever
        # it's given, so this is the one way to reach that specific copy
        # (the one actually driving integration) rather than some other
        # instance the caller might separately be holding.
        T* target[T]()


cdef extern from "include/bclibc/engine.hpp" namespace "bclibc" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    cdef enum class BCLIBC_ZeroInitialStatus:
        CONTINUE
        DONE

    cdef cppclass BCLIBC_ZeroInitialData:
        BCLIBC_ZeroInitialStatus status
        double look_angle_rad
        double slant_range_ft
        double target_x_ft
        double target_y_ft
        double start_height_ft

    cdef cppclass BCLIBC_MaxRangeResult:
        double max_range_ft
        double angle_at_max_rad

    cdef cppclass BCLIBC_ZeroPointResult:
        double angle_rad
        BCLIBC_TrajectoryData point
        bint has_point

    # Forward declaration
    cdef cppclass BCLIBC_BaseEngine

    # Declare the function signature type (not a pointer yet). The real
    # signature returns BCLIBC_BaseResult<std::monostate> (never void) --
    # Cython does not need that template spelled out here since assignment
    # into integrate_func (operator=[U]) and BCLIBC_BaseEngine::integrate()
    # calling it are both resolved against the real header at C++ compile
    # time, not against this declaration.
    ctypedef void BCLIBC_IntegrateFunc(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &trajectory,
        BCLIBC_TerminationReason &reason,
    ) except +

    # Declare function
    ctypedef function[BCLIBC_IntegrateFunc] BCLIBC_IntegrateCallable

    cdef cppclass BCLIBC_BaseEngine:
        int integration_step_count
        BCLIBC_V3dT gravity_vector
        BCLIBC_Config config
        BCLIBC_ShotProps shot
        BCLIBC_IntegrateCallable integrate_func

        BCLIBC_BaseEngine() except+

        # Every method below now returns a BCLIBC_(Engine)Result instead of throwing;
        # Cython has no convenient std::variant binding, so each is called only through
        # the py_engine_*() wrappers declared below, never directly.


# bclibc's BCLIBC_BaseEngine methods all return a Result (std::variant<BCLIBC_EngineError, T>)
# instead of throwing. This shim gives Cython a plain, non-template signature per method:
# a bint success flag (checked with "except 0"/"except NULL"), the success value written to
# an out-param, and a PyEngineError out-param describing the failure otherwise -- Cython then
# raises the matching Python exception itself (see exceptions.pxd's raise_engine_error()),
# the same rich exceptions "except +raise_solver_exception" used to dispatch via dynamic_cast.
#
# Self-contained here (not in py_bind.cpp): every extension that uses BCLIBC_BaseEngine also
# already compiles engine.cpp (see setup.py's _ENGINE_DEPS), but py_bind.cpp is also compiled
# into extensions that do NOT (e.g. "bind" itself), where these symbols would be unresolved.
cdef extern from * nogil:
    """
    #include "bclibc/engine.hpp"
    #include <Python.h>
    #include <variant>
    #include <type_traits>

    namespace {
        // 0 = generic/runtime (BCLIBC_LogicError, DomainError, RuntimeError, OutOfRangeError,
        //     InvalidArgumentError -- the same catch-all bucket "SolverRuntimeError" used before).
        // 1 = BCLIBC_SolverOutOfRangeError, 2 = BCLIBC_SolverZeroFindingError,
        // 3 = BCLIBC_SolverInterceptionError.
        struct PyEngineError
        {
            int kind = 0;
            const char *message = "";
            double f0 = 0.0, f1 = 0.0, f2 = 0.0;
            int i0 = 0;
            bclibc::BCLIBC_BaseTrajData raw_data;
            bclibc::BCLIBC_TrajectoryData full_data;
        };

        template <class ErrorVariant>
        void fill_engine_error(PyEngineError &out, const ErrorVariant &error)
        {
            std::visit([&out](const auto &e)
            {
                using T = std::decay_t<decltype(e)>;
                out.message = e.what();
                if constexpr (std::is_same_v<T, bclibc::BCLIBC_SolverOutOfRangeError>)
                {
                    out.kind = 1;
                    out.f0 = e.requested_distance_ft; out.f1 = e.max_range_ft; out.f2 = e.look_angle_rad;
                }
                else if constexpr (std::is_same_v<T, bclibc::BCLIBC_SolverZeroFindingError>)
                {
                    out.kind = 2;
                    out.f0 = e.zero_finding_error; out.i0 = e.iterations_count; out.f1 = e.last_barrel_elevation_rad;
                }
                else if constexpr (std::is_same_v<T, bclibc::BCLIBC_SolverInterceptionError>)
                {
                    out.kind = 3;
                    out.raw_data = e.raw_data; out.full_data = e.full_data;
                }
                else
                {
                    out.kind = 0;
                }
            }, error);
        }

        static bool py_engine_integrate(
            bclibc::BCLIBC_BaseEngine &eng, double range_limit_ft,
            bclibc::BCLIBC_BaseTrajDataHandlerInterface &handler, bclibc::BCLIBC_TerminationReason &reason,
            PyEngineError &err)
        {
            auto result = eng.integrate(range_limit_ft, handler, reason);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_engine_integrate_at(
            bclibc::BCLIBC_BaseEngine &eng, bclibc::BCLIBC_BaseTrajData_InterpKey key, double target_value,
            bclibc::BCLIBC_BaseTrajData &raw_data, bclibc::BCLIBC_TrajectoryData &full_data, PyEngineError &err)
        {
            auto result = eng.integrate_at(key, target_value, raw_data, full_data);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_engine_integrate_filtered(
            bclibc::BCLIBC_BaseEngine &eng, double range_limit_ft, double range_step_ft, double time_step,
            bclibc::BCLIBC_TrajFlag filter_flags, std::vector<bclibc::BCLIBC_TrajectoryData> &records,
            bclibc::BCLIBC_TerminationReason &reason, bclibc::BCLIBC_BaseTrajSeq *dense_trajectory, PyEngineError &err)
        {
            auto result = eng.integrate_filtered(range_limit_ft, range_step_ft, time_step, filter_flags,
                                                  records, reason, dense_trajectory);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_BaseError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_engine_find_apex(
            bclibc::BCLIBC_BaseEngine &eng, bclibc::BCLIBC_BaseTrajData &apex_out, PyEngineError &err)
        {
            auto result = eng.find_apex(apex_out);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_engine_error_at_distance(
            bclibc::BCLIBC_BaseEngine &eng, double angle_rad, double target_x_ft, double target_y_ft,
            double &value_out, PyEngineError &err)
        {
            auto result = eng.error_at_distance(angle_rad, target_x_ft, target_y_ft);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            value_out = std::get<double>(result);
            return 1;
        }

        static bool py_engine_find_max_range(
            bclibc::BCLIBC_BaseEngine &eng, double low_angle_deg, double high_angle_deg,
            double apex_is_max_range_radians, bclibc::BCLIBC_MaxRangeResult &out, PyEngineError &err)
        {
            auto result = eng.find_max_range(low_angle_deg, high_angle_deg, apex_is_max_range_radians);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            out = std::get<bclibc::BCLIBC_MaxRangeResult>(result);
            return 1;
        }

        static bool py_engine_init_zero_calculation(
            bclibc::BCLIBC_BaseEngine &eng, double distance, double apex_is_max_range_radians,
            double allowed_zero_error_feet, bclibc::BCLIBC_ZeroInitialData &out, PyEngineError &err)
        {
            auto result = eng.init_zero_calculation(distance, apex_is_max_range_radians, allowed_zero_error_feet, out);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            return 1;
        }

        static bool py_engine_zero_angle_with_fallback(
            bclibc::BCLIBC_BaseEngine &eng, double distance, double apex_is_max_range_radians,
            double allowed_zero_error_feet, double &angle_out, PyEngineError &err)
        {
            auto result = eng.zero_angle_with_fallback(distance, apex_is_max_range_radians, allowed_zero_error_feet);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            angle_out = std::get<double>(result);
            return 1;
        }

        static bool py_engine_zero_angle(
            bclibc::BCLIBC_BaseEngine &eng, double distance, double apex_is_max_range_radians,
            double allowed_zero_error_feet, double &angle_out, PyEngineError &err)
        {
            auto result = eng.zero_angle(distance, apex_is_max_range_radians, allowed_zero_error_feet);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            angle_out = std::get<double>(result);
            return 1;
        }

        static bool py_engine_find_zero_angle(
            bclibc::BCLIBC_BaseEngine &eng, double distance, int lofted, double apex_is_max_range_radians,
            double allowed_zero_error_feet, double &angle_out, PyEngineError &err)
        {
            auto result = eng.find_zero_angle(distance, lofted, apex_is_max_range_radians, allowed_zero_error_feet);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            angle_out = std::get<double>(result);
            return 1;
        }

        static bool py_engine_zero_point_with_fallback(
            bclibc::BCLIBC_BaseEngine &eng, double distance, double apex_is_max_range_radians,
            double allowed_zero_error_feet, bclibc::BCLIBC_ZeroPointResult &out, PyEngineError &err)
        {
            auto result = eng.zero_point_with_fallback(distance, apex_is_max_range_radians, allowed_zero_error_feet);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            out = std::get<bclibc::BCLIBC_ZeroPointResult>(result);
            return 1;
        }

        static bool py_engine_find_zero_point(
            bclibc::BCLIBC_BaseEngine &eng, double distance, int lofted, double apex_is_max_range_radians,
            double allowed_zero_error_feet, bclibc::BCLIBC_ZeroPointResult &out, PyEngineError &err)
        {
            auto result = eng.find_zero_point(distance, lofted, apex_is_max_range_radians, allowed_zero_error_feet);
            if (bclibc::has_error(result))
            {
                fill_engine_error(err, std::get<bclibc::BCLIBC_EngineError>(result));
                return 0;
            }
            out = std::get<bclibc::BCLIBC_ZeroPointResult>(result);
            return 1;
        }
    }
    """
    cdef struct PyEngineError:
        int kind
        const char *message
        double f0
        double f1
        double f2
        int i0
        BCLIBC_BaseTrajData raw_data
        BCLIBC_TrajectoryData full_data

    bint py_engine_integrate(
        BCLIBC_BaseEngine&, double, BCLIBC_BaseTrajDataHandlerInterface&, BCLIBC_TerminationReason&,
        PyEngineError&) noexcept
    bint py_engine_integrate_at(
        BCLIBC_BaseEngine&, BCLIBC_BaseTrajData_InterpKey, double, BCLIBC_BaseTrajData&, BCLIBC_TrajectoryData&,
        PyEngineError&) noexcept
    bint py_engine_integrate_filtered(
        BCLIBC_BaseEngine&, double, double, double, BCLIBC_TrajFlag, vector[BCLIBC_TrajectoryData]&,
        BCLIBC_TerminationReason&, BCLIBC_BaseTrajSeq*, PyEngineError&) noexcept
    bint py_engine_find_apex(BCLIBC_BaseEngine&, BCLIBC_BaseTrajData&, PyEngineError&) noexcept
    bint py_engine_error_at_distance(
        BCLIBC_BaseEngine&, double, double, double, double&, PyEngineError&) noexcept
    bint py_engine_find_max_range(
        BCLIBC_BaseEngine&, double, double, double, BCLIBC_MaxRangeResult&, PyEngineError&) noexcept
    bint py_engine_init_zero_calculation(
        BCLIBC_BaseEngine&, double, double, double, BCLIBC_ZeroInitialData&, PyEngineError&) noexcept
    bint py_engine_zero_angle_with_fallback(
        BCLIBC_BaseEngine&, double, double, double, double&, PyEngineError&) noexcept
    bint py_engine_zero_angle(
        BCLIBC_BaseEngine&, double, double, double, double&, PyEngineError&) noexcept
    bint py_engine_find_zero_angle(
        BCLIBC_BaseEngine&, double, int, double, double, double&, PyEngineError&) noexcept
    bint py_engine_zero_point_with_fallback(
        BCLIBC_BaseEngine&, double, double, double, BCLIBC_ZeroPointResult&, PyEngineError&) noexcept
    bint py_engine_find_zero_point(
        BCLIBC_BaseEngine&, double, int, double, double, BCLIBC_ZeroPointResult&, PyEngineError&) noexcept


cdef class CythonizedBaseIntegrationEngine:

    cdef double _DEFAULT_TIME_STEP

    cdef:
        public object _config
        list[object] _table_data  # list[object]
        BCLIBC_BaseEngine _this

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef void _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        BCLIBC_ZeroInitialData &out,
    )
    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance,
        bint lofted
    )
    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance
    )
    cdef BCLIBC_MaxRangeResult _find_max_range(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double low_angle_deg,
        double high_angle_deg,
    )
    cdef BCLIBC_TrajectoryData _find_apex(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        double angle_rad,
        double target_x_ft,
        double target_y_ft
    )

    cdef void _integrate_raw_at(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        BCLIBC_BaseTrajData_InterpKey key,
        double target_value,
        BCLIBC_BaseTrajData &raw_data,
        BCLIBC_TrajectoryData &full_data
    )

    cdef void _integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double range_limit_ft,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    )
