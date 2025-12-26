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


# ============================================================================
# C++11 Exception Dispatch Mechanism
# ============================================================================
#
# Efficiently converts C++ exceptions to Python exceptions using a single
# rethrow and dynamic type checking.
#
# Architecture Overview:
# ----------------------
#
# 1. exception_dispatch<Handlers...>(...):
#    Entry point that captures and rethrows the current exception exactly once.
#    Delegates type checking to the handler chain.
#
# 2. try_handle_chain<HandlerT, Rest...>(...):
#    Recursive template that walks through handlers until one matches.
#    Uses dynamic_cast for safe runtime type identification.
#    Short-circuits on first successful match.
#
# 3. try_single_handler<ExceptionT>(...):
#    Attempts to match a specific exception type via dynamic_cast.
#    Calls the Cython handler if types match.
#    Verifies Python exception was set via PyErr_Occurred().
#
# Performance Characteristics:
# ---------------------------
# - Single std::rethrow_exception call (O(1))
# - Linear scan through handlers (O(n) where n = handler count)
# - Early exit on first match
# - No heap allocations in dispatch path
#
# Error Handling:
# --------------
# - Matched exceptions → converted to Python exceptions via handlers
# - Unmatched std::exception → rethrown for Cython's "except +" handling
# - Non-std exceptions → rethrown immediately
#
# Thread Safety:
# -------------
# Handlers must acquire GIL before touching Python objects.
# The dispatch mechanism itself is thread-safe.

cdef extern from *:
    """
    #include <exception>
    #include <utility>

    namespace {
        /**
         * Attempts to handle a specific exception type.
         *
         * Uses dynamic_cast to safely identify the exception type at runtime.
         * If the cast succeeds, invokes the corresponding Cython handler and
         * verifies that a Python exception was properly set.
         *
         * @tparam ExceptionT The C++ exception type to match
         * @param e The caught std::exception reference
         * @param handler Function pointer to Cython handler
         * @return true if exception type matched and handler was invoked
         *
         * @note The handler is responsible for setting Python exception state
         * @note Returns false if dynamic_cast fails (type mismatch)
         */
        template <typename ExceptionT>
        bool try_single_handler(const std::exception& e, void (*handler)(const ExceptionT&)) {
            if (auto specific = dynamic_cast<const ExceptionT*>(&e)) {
                handler(*specific);
                return PyErr_Occurred() != nullptr;
            }
            return false;
        }

        /**
         * Base case: No handlers matched, rethrow original exception.
         *
         * This allows Cython's default "except +" mechanism to handle
         * the exception, typically converting it to a RuntimeError.
         */
        inline void try_handle_chain(const std::exception& e) {
            throw;
        }

        /**
         * Recursive case: Try current handler, then remaining handlers.
         *
         * Implements a linear search through the handler chain with early exit.
         * If current handler matches, stops immediately. Otherwise, recurses
         * with remaining handlers.
         *
         * @tparam HandlerT Type of current handler function pointer
         * @tparam Rest Types of remaining handler function pointers
         * @param e The exception to dispatch
         * @param handler Current handler to try
         * @param rest Remaining handlers (unpacked recursively)
         */
        template <typename HandlerT, typename... Rest>
        void try_handle_chain(const std::exception& e, HandlerT&& handler, Rest&&... rest) {
            if (try_single_handler(e, std::forward<HandlerT>(handler))) {
                return;  // Handler matched, stop recursion
            }
            try_handle_chain(e, std::forward<Rest>(rest)...);
        }

        /**
         * Main exception dispatch entry point.
         *
         * Captures the current C++ exception (if any) and rethrows it exactly once.
         * Delegates type-specific handling to the recursive handler chain.
         *
         * This design ensures minimal overhead:
         * - Single rethrow operation (not O(n) rethrows)
         * - Dynamic type checking only when exception is caught
         * - No additional try/catch blocks per handler
         *
         * @tparam Handlers Variadic template accepting any number of handler functions
         * @param handlers Function pointers to exception handlers
         *
         * @note Handlers should be ordered from most specific to most general
         * @note Non-std::exception types are rethrown immediately
         * @note If no handler matches, exception is rethrown for Cython handling
         */
        template <typename... Handlers>
        void exception_dispatch(Handlers&&... handlers) {
            auto e_ptr = std::current_exception();
            if (!e_ptr) return;

            try {
                std::rethrow_exception(e_ptr);
            } catch (const std::exception& e) {
                try_handle_chain(e, std::forward<Handlers>(handlers)...);
            } catch (...) {
                throw;  // Rethrow non-std::exception types
            }
        }
    }
    """
    # Cython declaration: variadic function accepting any number of handlers
    void exception_dispatch(...) except +*


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
    """
    Converts BCLIBC_OutOfRangeError to Python OutOfRangeError.

    Extracts distance and angle information from the C++ exception and
    constructs an equivalent Python exception with converted units.
    """
    from py_ballisticcalc.exceptions import OutOfRangeError
    raise OutOfRangeError(
        feet_from_c(e.requested_distance_ft),
        feet_from_c(e.max_range_ft),
        rad_from_c(e.look_angle_rad),
        e.what().decode("utf-8")
    )


cdef inline void handle_ZeroFindingError(const BCLIBC_ZeroFindingError &e):
    """
    Converts BCLIBC_ZeroFindingError to Python ZeroFindingError.

    Extracts convergence metrics from the C++ exception (error magnitude,
    iteration count, last barrel elevation) and constructs equivalent
    Python exception.
    """
    from py_ballisticcalc.exceptions import ZeroFindingError
    raise ZeroFindingError(
        e.zero_finding_error,
        e.iterations_count,
        rad_from_c(e.last_barrel_elevation_rad),
        e.what().decode("utf-8")
    )


cdef inline void handle_InterceptError(const BCLIBC_InterceptionError &e):
    """
    Converts BCLIBC_InterceptionError to Python InterceptionError.

    Wraps trajectory data (both raw and processed) from the C++ exception
    into Python objects for inspection and debugging.
    """
    from py_ballisticcalc.exceptions import InterceptionError
    cdef CythonizedBaseTrajData raw_data = CythonizedBaseTrajData()
    cdef object py_full_data = TrajectoryData_from_cpp(e.full_data)
    raw_data._this = e.raw_data
    raise InterceptionError(e.what().decode("utf-8"), (raw_data, py_full_data))


cdef inline void handle_SolverRuntimeError(const BCLIBC_SolverRuntimeError &e):
    """
    Converts BCLIBC_SolverRuntimeError to Python SolverRuntimeError.

    Base handler for generic solver errors. Acts as a catch-all for
    solver exceptions that don't have more specific handlers.
    """
    from py_ballisticcalc.exceptions import SolverRuntimeError
    raise SolverRuntimeError(e.what().decode("utf-8"))


cdef inline void raise_solver_exception():
    """
    Raises appropriate Python exception from current C++ solver exception.

    Dispatches the active C++ exception to the appropriate Python exception
    handler based on runtime type identification. Handlers are ordered from
    most specific to most general:

    1. OutOfRangeError - Trajectory calculation exceeded valid distance range
    2. ZeroFindingError - Barrel elevation convergence failed during zeroing
    3. InterceptionError - Target interception calculation failed
    4. SolverRuntimeError - Generic solver error (catch-all)

    Usage:
        try:
            cpp_solver.calculate()
        except:
            raise_solver_exception()

    Note:
        This function should only be called from an except block where a
        C++ exception is active. Calling it without an active exception
        is a no-op.
    """
    exception_dispatch(
        handle_OutOfRangeError,
        handle_ZeroFindingError,
        handle_InterceptError,
        handle_SolverRuntimeError,
    )
