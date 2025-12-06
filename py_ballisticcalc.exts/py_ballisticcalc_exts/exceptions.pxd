from libcpp.string cimport string
from libcpp.exception cimport exception_ptr

from py_ballisticcalc_exts.traj_data cimport (
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
    CythonizedBaseTrajData,
    TrajectoryData_from_cpp,
)
from py_ballisticcalc_exts.bind cimport (
    feet_from_c,
    rad_from_c,
)


# Import C++ standard library components
cdef extern from "<stdexcept>" namespace "std" nogil:
    cppclass exception:
        exception(const char* s)
        const char* what() const

    cppclass runtime_error(exception):
        runtime_error(const char* s)

    cppclass logic_error(exception):
        logic_error(const char* s)

    exception_ptr current_exception() noexcept


# C++11 Recursive template dispatcher for exception handling
# Uses template recursion instead of C++17 fold expressions
#
# Architecture:
# 1. call_exception_handler<ExceptionT>():
#    - Template function that attempts to catch specific exception type
#    - Receives exception by const reference (no heap allocation)
#    - Returns true if handled
#
# 2. many_exception_handler(...):
#    - Recursive variadic template
#    - Base case: try single handler, rethrow if not handled
#    - Recursive case: try first handler, recurse with rest if not handled
#    - Short-circuits on first successful handler match
#
# Template Expansion Example (C++11):
# ------------------------------------
# Given:
#     many_exception_handler(handler1, handler2, handler3)
#
# Expands to:
#     if (call_exception_handler(eptr, handler1))
#         return;
#     else
#         many_exception_handler(handler2, handler3)
#         // which then expands to:
#         if (call_exception_handler(eptr, handler2))
#             return;
#         else
#             many_exception_handler(handler3)
#             // which then expands to:
#             if (call_exception_handler(eptr, handler3))
#                 return;
#             else
#                 rethrow_exception(eptr);
cdef extern from *:
    """
    namespace {
        // Template function to handle a specific exception type
        // Returns true if exception was caught and handler was called
        template <typename ExceptionT>
        bool call_exception_handler(std::exception_ptr e_ptr, void (*handler)(ExceptionT&)) {
            try {
                std::rethrow_exception(e_ptr);
            } catch(ExceptionT &ex) {
                handler(ex);  // Call Cython handler with exception reference
                return static_cast<bool>(PyErr_Occurred());  // Verify Python exception set
            } catch (...) {
                return false;  // Not the expected type, continue to next handler
            }
        }

        // Base case: single handler (terminal case in recursion)
        template <typename HandlerT>
        void many_exception_handler(HandlerT&& handler) {
            auto e_ptr = std::current_exception();
            bool handled = call_exception_handler(e_ptr, std::forward<HandlerT>(handler));
            if (!handled)
                std::rethrow_exception(e_ptr);  // No handler matched, rethrow
        }

        // Recursive case: try first handler, then recurse with remaining handlers
        // This is the C++11 equivalent of C++17 fold expressions
        template <typename HandlerT, typename... RestHandlerTs>
        void many_exception_handler(HandlerT&& handler, RestHandlerTs&&... rest) {
            auto e_ptr = std::current_exception();
            bool handled = call_exception_handler(e_ptr, std::forward<HandlerT>(handler));
            if (!handled) {
                // Try remaining handlers recursively
                many_exception_handler(std::forward<RestHandlerTs>(rest)...);
            }
        }
    }
    """
    # Cython declaration: variadic function accepting any number of handlers
    void many_exception_handler(...) except +*


cdef extern from "bclibc/exceptions.hpp" namespace "bclibc" nogil:
    cdef cppclass BCLIBC_SolverRuntimeError(runtime_error):
        BCLIBC_SolverRuntimeError(const string &message) except+

    cdef cppclass BCLIBC_OutOfRangeError(BCLIBC_SolverRuntimeError):
        double requested_distance_ft
        double max_range_ft
        double look_angle_rad

        BCLIBC_OutOfRangeError(
            const string &message,
            double requested_distance_ft,
            double max_range_ft,
            double look_angle_rad) except+

    cdef cppclass BCLIBC_ZeroFindingError(BCLIBC_SolverRuntimeError):
        double zero_finding_error
        int iterations_count
        double last_barrel_elevation_rad

        BCLIBC_ZeroFindingError(
            const string &message,
            double zero_finding_error,
            int iterations_count,
            double last_barrel_elevation_rad) except+

    cdef cppclass BCLIBC_InterceptionError(BCLIBC_SolverRuntimeError):
        BCLIBC_BaseTrajData raw_data
        BCLIBC_TrajectoryData full_data

        BCLIBC_InterceptionError(
            const string &message,
            const BCLIBC_BaseTrajData &raw_data,
            const BCLIBC_TrajectoryData &full_data,
        ) except+


cdef inline void handle_OutOfRangeError(const BCLIBC_OutOfRangeError &e):
    from py_ballisticcalc.exceptions import OutOfRangeError
    raise OutOfRangeError(
        feet_from_c(e.requested_distance_ft),
        feet_from_c(e.max_range_ft),
        rad_from_c(e.look_angle_rad),
        e.what().decode("utf-8")
    )


cdef inline void handle_ZeroFindingError(const BCLIBC_ZeroFindingError &e):
    from py_ballisticcalc.exceptions import ZeroFindingError
    raise ZeroFindingError(
        e.zero_finding_error,
        e.iterations_count,
        rad_from_c(e.last_barrel_elevation_rad),
        e.what().decode("utf-8")
    )


cdef inline void handle_InterceptError(const BCLIBC_InterceptionError &e):
    from py_ballisticcalc.exceptions import InterceptionError
    cdef CythonizedBaseTrajData raw_data = CythonizedBaseTrajData()
    cdef object py_full_data = TrajectoryData_from_cpp(e.full_data)
    raw_data._this = e.raw_data
    raise InterceptionError(e.what().decode("utf-8"), (raw_data, py_full_data))


cdef inline void handle_SolverRuntimeError(const BCLIBC_SolverRuntimeError &e):
    from py_ballisticcalc.exceptions import SolverRuntimeError
    raise SolverRuntimeError(e.what().decode("utf-8"))


cdef inline void raise_solver_exception():
    many_exception_handler(
        handle_ZeroFindingError,
        handle_OutOfRangeError,
        handle_InterceptError,
        handle_SolverRuntimeError,
    )
