from cpython.object cimport PyObject
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

cdef extern from "Python.h":
    void Py_INCREF(PyObject *o)

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


cdef extern from *:
    """
    #pragma once
    #include <Python.h>
    #include <exception>
    #include <string>

    namespace exception_bridge {

        /**
        * Holds the mapping between a C++ exception type and a Python exception class.
        */
        template <typename T>
        struct ExceptionRule {
            typedef PyObject* (*extractor_t)(const T&);

            PyObject* py_class;
            extractor_t extract;

            /**
            * Attempts to handle the exception. Returns true if the exception matches type T.
            */
            bool try_handle(const std::exception& e) const {
                // Using dynamic_cast for safe runtime type checking.
                // Requires the C++ exception to have at least one virtual method (usually destructor).
                if (auto specific_ex = dynamic_cast<const T*>(&e)) {
                    PyObject* args = extract(*specific_ex);
                    if (args) {
                        // PyErr_SetObject sets the exception and uses the tuple as constructor arguments.
                        PyErr_SetObject(py_class, args);
                        Py_DECREF(args);
                        return true;
                    }
                }
                return false;
            }
        };

        /**
        * Default extractor: creates a 1-element tuple containing the exception message.
        */
        template <typename T>
        PyObject* default_extractor(const T& e) {
            PyObject* msg = PyUnicode_FromString(e.what());
            PyObject* args = PyTuple_Pack(1, msg);
            Py_XDECREF(msg);
            return args;
        }

        /**
        * Factory for custom rules with specific field extraction logic.
        */
        template <typename T>
        ExceptionRule<T> bind(PyObject* cls, PyObject* (*ext)(const T&)) {
            return {cls, ext};
        }

        /**
        * Factory for simple rules that only pass the exception message to Python.
        */
        template <typename T>
        ExceptionRule<T> bind(PyObject* cls) {
            return {cls, &default_extractor<T>};
        }

        /**
        * Variadic dispatcher that iterates through all provided rules.
        */
        template <typename... Rules>
        void dispatch(const Rules&... rules) {
            auto e_ptr = std::current_exception();
            if (!e_ptr) return;

            try {
                std::rethrow_exception(e_ptr);
            } catch (const std::exception& e) {
                bool handled = false;
                // C++11 Parameter pack expansion trick to iterate over rules
                int dummy[] = { 0, (handled ? 0 : (handled = rules.try_handle(e), 0))... };
                (void)dummy;

                if (!handled) throw; // Rethrow if no rule matches
            } catch (...) {
                throw; // Fallback for non-std::exception types
            }
        }
    }
    """


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


cdef extern from * namespace "exception_bridge":
    cppclass ExceptionRule[T]:
        pass

    # Note: Using PyObject* explicitly to avoid Cython auto-conversion issues in templates
    ExceptionRule[T] bind[T](PyObject* cls)
    ExceptionRule[T] bind[T](PyObject* cls, PyObject* (*f)(const T&))

    # except +* allows Cython to handle any rethrown exceptions
    # that weren't caught by our dispatcher
    void dispatch(...) except +*
    void Py_INCREF(PyObject *o)


# --- ZeroFindingError Extractor ---
cdef inline PyObject* extract_zero_finding_error(const BCLIBC_ZeroFindingError& e) noexcept:
    cdef tuple args = (
        e.zero_finding_error,
        e.iterations_count,
        rad_from_c(e.last_barrel_elevation_rad),
        e.what().decode('utf-8')
    )
    cdef PyObject* ptr = <PyObject*>args
    Py_INCREF(ptr)  # Ми кажемо Python: "цей об'єкт потрібен комусь ще"
    return ptr


# --- OutOfRangeError Extractor ---
cdef inline PyObject* extract_out_of_range_error(const BCLIBC_OutOfRangeError& e) noexcept:
    cdef tuple args = (
        feet_from_c(e.requested_distance_ft),
        feet_from_c(e.max_range_ft),
        rad_from_c(e.look_angle_rad),
        e.what().decode("utf-8")
    )
    cdef PyObject* ptr = <PyObject*>args
    Py_INCREF(ptr)  # Ми кажемо Python: "цей об'єкт потрібен комусь ще"
    return ptr


# --- InterceptionError Extractor ---
cdef inline PyObject* extract_interception_error(const BCLIBC_InterceptionError& e) noexcept:
    # 1. Prepare data wrappers
    cdef CythonizedBaseTrajData raw_data = CythonizedBaseTrajData()
    raw_data._this = e.raw_data

    # 2. Convert full trajectory data using your helper
    cdef object py_full_data = TrajectoryData_from_cpp(e.full_data)

    # 3. Pack as per expected signature: InterceptionError(message, (raw_data, full_data))
    cdef tuple args = (
        e.what().decode("utf-8"),
        (raw_data, py_full_data)
    )
    cdef PyObject* ptr = <PyObject*>args
    Py_INCREF(ptr)  # Ми кажемо Python: "цей об'єкт потрібен комусь ще"
    return ptr


cdef inline void raise_solver_exception():
    from py_ballisticcalc.exceptions import (
        ZeroFindingError,
        OutOfRangeError,
        InterceptionError,
        SolverRuntimeError
    )

    dispatch(
        bind[BCLIBC_ZeroFindingError](<PyObject*>ZeroFindingError, extract_zero_finding_error),
        bind[BCLIBC_OutOfRangeError](<PyObject*>OutOfRangeError, extract_out_of_range_error),
        bind[BCLIBC_InterceptionError](<PyObject*>InterceptionError, extract_interception_error),
        bind[BCLIBC_SolverRuntimeError](<PyObject*>SolverRuntimeError)
    )
