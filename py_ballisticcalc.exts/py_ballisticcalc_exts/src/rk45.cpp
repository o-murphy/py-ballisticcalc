#include <cmath>
#include <array>
#include "bclibc/rk45.hpp"
#include "bclibc/base_types.hpp"

namespace bclibc
{

    // --- RUNGE-KUTTA-FEHLBERG COEFFICIENTS (RKF45) ---
    constexpr std::array<double, 6> A_RKF = {
        0.0, 1.0 / 4.0, 3.0 / 8.0, 12.0 / 13.0, 1.0, 1.0 / 2.0};
    constexpr std::array<std::array<double, 6>, 6> B_RKF = {{{0.0, 0.0, 0.0, 0.0, 0.0, 0.0},
                                                             {1.0 / 4.0, 0.0, 0.0, 0.0, 0.0, 0.0},
                                                             {3.0 / 32.0, 9.0 / 32.0, 0.0, 0.0, 0.0, 0.0},
                                                             {1932.0 / 2197.0, -7200.0 / 2197.0, 7200.0 / 2197.0, 0.0, 0.0, 0.0},
                                                             {439.0 / 216.0, -8.0, 3680.0 / 513.0, -845.0 / 4104.0, 0.0, 0.0},
                                                             {-8.0 / 27.0, 2.0, -3544.0 / 2565.0, 1859.0 / 4104.0, -11.0 / 40.0, 0.0}}};
    constexpr std::array<double, 6> C_RKF_5 = {
        16.0 / 135.0, 0.0, 6656.0 / 12825.0, 28561.0 / 56430.0, -9.0 / 50.0, 2.0 / 55.0};
    constexpr std::array<double, 6> C_RKF_4 = {
        25.0 / 216.0, 0.0, 1408.0 / 2565.0, 2197.0 / 4104.0, -1.0 / 5.0, 0.0};

    constexpr double cRK45Tolerance = 1e-6;

    static inline void BCLIBC_calculate_dvdt(
        const BCLIBC_V3dT &v,
        const BCLIBC_V3dT &gravity_vector,
        double km_coeff,
        const BCLIBC_ShotProps &shot_props,
        const BCLIBC_V3dT &ground_velocity,
        BCLIBC_V3dT &acceleration)
    {
        double v_mag = v.mag();
        acceleration.linear_combination(gravity_vector, 1.0, v, -km_coeff * v_mag);

        if (!shot_props.coriolis.flat_fire_only)
        {
            BCLIBC_V3dT coriolis_acceleration;
            shot_props.coriolis.coriolis_acceleration_local(
                ground_velocity,
                coriolis_acceleration);
            acceleration += coriolis_acceleration;
        }
    }

    void BCLIBC_integrateRK45(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason)
    {
        double velocity;
        double density_ratio = 0.0;
        double mach = 0.0;
        double time = 0.0;
        double km = 0.0;

        BCLIBC_V3dT range_vector;
        BCLIBC_V3dT velocity_vector;
        BCLIBC_V3dT gravity_vector;
        BCLIBC_V3dT wind_vector;

        reason = BCLIBC_TerminationReason::NO_TERMINATE;
        eng.integration_step_count = 0;

        // Adaptive step settings
        double current_step = eng.shot.calc_step;
        const double tolerance = cRK45Tolerance;
        const double max_step = 1.0;
        const double min_step = 1e-6;

        // Buffers for 6 intermediate estimates
        BCLIBC_V3dT k_v[6], k_p[6];
        BCLIBC_V3dT v_temp, r_temp;

        // Initialize gravity
        gravity_vector.x = 0.0;
        gravity_vector.y = eng.config.cGravityConstant;
        gravity_vector.z = 0.0;

        // Initialize wind
        wind_vector = eng.shot.wind_sock.current_vector();

        // Initialize projectile state
        velocity = eng.shot.muzzle_velocity;
        range_vector.x = 0.0;
        range_vector.y = -eng.shot.cant_cosine * eng.shot.sight_height;
        range_vector.z = -eng.shot.cant_sine * eng.shot.sight_height;

        const double cos_elev = std::cos(eng.shot.barrel_elevation);
        BCLIBC_V3dT _dir_vector;
        _dir_vector.x = cos_elev * std::cos(eng.shot.barrel_azimuth);
        _dir_vector.y = std::sin(eng.shot.barrel_elevation);
        _dir_vector.z = cos_elev * std::sin(eng.shot.barrel_azimuth);
        velocity_vector = _dir_vector * velocity;

        // Get initial atmospheric conditions
        eng.shot.atmo.update_density_factor_and_mach_for_altitude(
            eng.shot.alt0 + range_vector.y,
            density_ratio,
            mach);

        // Main integration loop
        while (reason == BCLIBC_TerminationReason::NO_TERMINATE)
        {
            eng.integration_step_count++;

            // Update wind if needed
            if (range_vector.x >= eng.shot.wind_sock.next_range)
            {
                wind_vector = eng.shot.wind_sock.vector_for_range(range_vector.x);
            }

            // Update atmospheric conditions at current position
            eng.shot.atmo.update_density_factor_and_mach_for_altitude(
                eng.shot.alt0 + range_vector.y,
                density_ratio,
                mach);

            // Record current trajectory point
            handler.handle(BCLIBC_BaseTrajData(time, range_vector, velocity_vector, mach));

            // Inner loop for adaptive step
            bool step_accepted = false;
            while (!step_accepted)
            {
                if (current_step < min_step)
                {
                    reason = BCLIBC_TerminationReason::HANDLER_REQUESTED_STOP;
                    break;
                }

                double h = std::min(current_step, max_step);

                // Calculate relative velocity and drag coefficient at base state
                BCLIBC_V3dT relative_velocity = velocity_vector - wind_vector;
                double relative_speed = relative_velocity.mag();
                km = density_ratio * eng.shot.drag_by_mach(relative_speed / mach);

                // K1: Evaluate at current state
                BCLIBC_calculate_dvdt(relative_velocity, gravity_vector, km, eng.shot, velocity_vector, k_v[0]);
                k_p[0] = velocity_vector;

                // K2-K6: Calculate intermediate derivatives
                for (int i = 1; i < 6; ++i)
                {
                    // Calculate intermediate state: y + h * Sum(b_ij * k_j)
                    r_temp = range_vector;
                    v_temp = velocity_vector;

                    for (int j = 0; j < i; ++j)
                    {
                        r_temp.fused_multiply_add(k_p[j], h * B_RKF[i][j]);
                        v_temp.fused_multiply_add(k_v[j], h * B_RKF[i][j]);
                    }

                    // Update atmospheric conditions for intermediate position
                    double temp_density_ratio, temp_mach;
                    eng.shot.atmo.update_density_factor_and_mach_for_altitude(
                        eng.shot.alt0 + r_temp.y, temp_density_ratio, temp_mach);

                    // Calculate k_i with intermediate state
                    BCLIBC_V3dT temp_relative_v = v_temp - wind_vector;
                    double temp_relative_speed = temp_relative_v.mag();
                    double temp_km = temp_density_ratio * eng.shot.drag_by_mach(temp_relative_speed / temp_mach);

                    BCLIBC_calculate_dvdt(temp_relative_v, gravity_vector, temp_km, eng.shot, v_temp, k_v[i]);
                    k_p[i] = v_temp; // Position derivative is the velocity at this intermediate point
                }

                // Calculate 5th order solution and error estimate
                BCLIBC_V3dT next_v_5 = velocity_vector;
                BCLIBC_V3dT next_r_5 = range_vector;
                BCLIBC_V3dT error_v = {0.0, 0.0, 0.0};
                BCLIBC_V3dT error_r = {0.0, 0.0, 0.0};

                for (int i = 0; i < 6; ++i)
                {
                    next_v_5.fused_multiply_add(k_v[i], h * C_RKF_5[i]);
                    next_r_5.fused_multiply_add(k_p[i], h * C_RKF_5[i]);

                    double error_coeff = C_RKF_5[i] - C_RKF_4[i];
                    error_v.fused_multiply_add(k_v[i], h * error_coeff);
                    error_r.fused_multiply_add(k_p[i], h * error_coeff);
                }

                // Local error estimation
                double error_e = error_v.mag();

                // Step control
                if (error_e <= tolerance)
                {
                    // Accept step
                    step_accepted = true;

                    velocity_vector = next_v_5;
                    range_vector = next_r_5;
                    velocity = velocity_vector.mag();
                    time += h;

                    // Calculate optimal next step
                    if (error_e > 1e-12)
                    {
                        double scale = std::pow(tolerance / error_e, 0.2);
                        current_step = h * std::min(5.0, std::max(0.2, scale));
                    }
                    else
                    {
                        current_step = h * 2.0; // Error is very small, increase step
                    }
                }
                else
                {
                    // Reject step and retry with smaller step
                    double scale = std::pow(tolerance / error_e, 0.25);
                    current_step = h * std::max(0.1, scale);
                }
            }

            // Check termination conditions (add your actual conditions here)
            // Example conditions from RK4:
            // - if (range_vector.x >= range_limit_ft) reason = RANGE_LIMIT;
            // - if (velocity < min_velocity) reason = MIN_VELOCITY;
            // - if (range_vector.y < min_altitude) reason = MIN_ALTITUDE;
            // etc.
        }

        // Final point
        eng.shot.atmo.update_density_factor_and_mach_for_altitude(
            eng.shot.alt0 + range_vector.y, density_ratio, mach);
        handler.handle(BCLIBC_BaseTrajData(time, range_vector, velocity_vector, mach));
    }

} // namespace bclibc
