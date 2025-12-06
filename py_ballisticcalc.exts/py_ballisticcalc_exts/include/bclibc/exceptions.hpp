#ifndef BCLIBC_EXCEPTIONS_HPP
#define BCLIBC_EXCEPTIONS_HPP

#include <stdexcept>
#include "bclibc/base_types.hpp"

namespace bclibc
{
    class BCLIBC_SolverRuntimeError : public std::runtime_error
    {
    public:
        BCLIBC_SolverRuntimeError(const std::string &message)
            : std::runtime_error(message) {};
    };

    class BCLIBC_OutOfRangeError : public BCLIBC_SolverRuntimeError
    {
    public:
        double requested_distance_ft;
        double max_range_ft;
        double look_angle_rad;

        BCLIBC_OutOfRangeError(
            const std::string &message,
            double requested_distance_ft,
            double max_range_ft,
            double look_angle_rad)
            : BCLIBC_SolverRuntimeError(message),
              requested_distance_ft(requested_distance_ft),
              max_range_ft(max_range_ft),
              look_angle_rad(look_angle_rad) {};
    };

    class BCLIBC_ZeroFindingError : public BCLIBC_SolverRuntimeError
    {
    public:
        double zero_finding_error;
        int iterations_count;
        double last_barrel_elevation_rad;

        BCLIBC_ZeroFindingError(
            const std::string &message,
            double zero_finding_error,
            int iterations_count,
            double last_barrel_elevation_rad)
            : BCLIBC_SolverRuntimeError(message),
              zero_finding_error(zero_finding_error),
              iterations_count(iterations_count),
              last_barrel_elevation_rad(last_barrel_elevation_rad) {};
    };

    class BCLIBC_InterceptionError : public BCLIBC_SolverRuntimeError
    {
    public:
        BCLIBC_BaseTrajData raw_data;
        BCLIBC_TrajectoryData full_data;
        BCLIBC_InterceptionError(
            const std::string &message,
            const BCLIBC_BaseTrajData &raw_data,
            const BCLIBC_TrajectoryData &full_data)
            : BCLIBC_SolverRuntimeError(message),
              raw_data(raw_data),
              full_data(full_data) {};
    };
}; // bclibc

#endif //  BCLIBC_EXCEPTIONS_HPP
