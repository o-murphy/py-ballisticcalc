#include <math.h>
#include "rk45.h"  // assumes Engine_t, V3dT, StatusCode, TerminationReason, TrajFlag_t, BaseTrajSeq_t, etc.

/* ----------------------
   Value-returning V3 helpers
   ---------------------- */
static inline V3dT V3d_add(V3dT a, V3dT b)
{
    V3dT r; r.x = a.x + b.x; r.y = a.y + b.y; r.z = a.z + b.z; return r;
}
static inline V3dT V3d_sub(V3dT a, V3dT b)
{
    V3dT r; r.x = a.x - b.x; r.y = a.y - b.y; r.z = a.z - b.z; return r;
}
static inline V3dT V3d_mulS(V3dT a, double s)
{
    V3dT r; r.x = a.x * s; r.y = a.y * s; r.z = a.z * s; return r;
}
static inline double V3d_mag(const V3dT *a)
{
    return sqrt(a->x * a->x + a->y * a->y + a->z * a->z);
}

/* ----------------------
   Helper function — compute acceleration at (pos, vel),
   returns acceleration, optionally fills density_ratio and mach
   ---------------------- */
static inline V3dT _accel_for_state(Engine_t *eng, const V3dT *pos, const V3dT *vel, double *density_ratio_out, double *mach_out, V3dT *wind_out)
{
    V3dT wind;
    // get wind for current range (same rules as Euler)
    wind = WindSock_t_vectorForRange(&eng->shot.wind_sock, pos->x);
    if (wind_out) *wind_out = wind;

    V3dT rel_v = V3d_sub(*vel, wind);
    double rel_speed = V3d_mag(&rel_v);

    double density_ratio = 1.0;
    double mach = 1.0;
    Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, eng->shot.alt0 + pos->y, &density_ratio, &mach);
    if (mach <= 0.0) mach = 1e-6;

    double km = density_ratio * ShotProps_t_dragByMach(&eng->shot, rel_speed / mach);
    double drag = km * rel_speed; /* effective drag coefficient * speed -> acceleration term multiplier */

    V3dT drag_term = V3d_mulS(rel_v, drag); /* drag_term = rel_v * drag */
    V3dT gravity = {0.0, eng->config.cGravityConstant, 0.0};
    V3dT accel = V3d_sub(gravity, drag_term);

    if (!eng->shot.coriolis.flat_fire_only)
    {
        V3dT cor;
        Coriolis_t_coriolis_acceleration_local(&eng->shot.coriolis, vel, &cor);
        accel = V3d_add(accel, cor);
    }

    if (density_ratio_out) *density_ratio_out = density_ratio;
    if (mach_out) *mach_out = mach;
    return accel;
}

/* ----------------------
   RK45 integrator — compatible signature
   ---------------------- */
StatusCode _integrate_rk45(
    Engine_t *eng,
    double range_limit_ft, double range_step_ft,
    double time_step, TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr,
    TerminationReason *reason)
{
    if (!eng || !traj_seq_ptr || !reason)
    {
        PUSH_ERR(&eng->err_stack, T_INPUT_ERROR, SRC_INTEGRATE, "Invalid input (NULL pointer).");
        return STATUS_ERROR;
    }

    /* Error control parameters */
    const double ABS_TOL = 1e-6;
    const double REL_TOL = 1e-6;
    const double SAFETY = 0.9;
    const double MIN_SCALE = 0.2;
    const double MAX_SCALE = 5.0;
    const double DT_MIN = 1e-6;
    const double DT_MAX = 0.05;

    /* Initialize state (taken from your Euler example) */
    double density_ratio = 0.0;
    double mach = 0.0;
    double time = 0.0;
    double km = 0.0;
    double drag = 0.0;
    V3dT range_vector;
    V3dT velocity_vector;
    V3dT wind_vector;
    V3dT coriolis_accel;

    double calc_step = eng->shot.calc_step;

    double _cMinimumVelocity = eng->config.cMinimumVelocity;
    double _cMinimumAltitude = eng->config.cMinimumAltitude;
    double _cMaximumDrop = -fabs(eng->config.cMaximumDrop);

    *reason = NO_TERMINATE;
    eng->integration_step_count = 0;

    /* Initial values */
    range_vector.x = 0.0;
    range_vector.y = -eng->shot.cant_cosine * eng->shot.sight_height;
    range_vector.z = -eng->shot.cant_sine * eng->shot.sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y);

    double cos_elev = cos(eng->shot.barrel_elevation);
    double sin_elev = sin(eng->shot.barrel_elevation);
    double cos_az = cos(eng->shot.barrel_azimuth);
    double sin_az = sin(eng->shot.barrel_azimuth);

    V3dT dir_vector;
    dir_vector.x = cos_elev * cos_az;
    dir_vector.y = sin_elev;
    dir_vector.z = cos_elev * sin_az;

    double muzzle_v = eng->shot.muzzle_velocity;
    velocity_vector = V3d_mulS(dir_vector, muzzle_v);

    /* Initial wind and atmosphere */
    wind_vector = WindSock_t_currentVector(&eng->shot.wind_sock);
    Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, eng->shot.alt0 + range_vector.y, &density_ratio, &mach);
    if (mach <= 0.0) mach = 1e-6;

    /* Additional RK variables */
    double dt = time_step > 0.0 ? time_step : calc_step; /* initial dt */
    if (dt < DT_MIN) dt = DT_MIN;
    if (dt > DT_MAX) dt = DT_MAX;

    /* Record initial point (like your Euler first append in loop) */
    BaseTrajSeq_t_append(traj_seq_ptr, time, range_vector.x, range_vector.y, range_vector.z,
                         velocity_vector.x, velocity_vector.y, velocity_vector.z, mach);

    /* Main loop: prevent "too long" execution, exit by termination conditions */
    while (range_vector.x <= range_limit_ft || eng->integration_step_count < 3)
    {
        /* RKF45 coefficients (Fehlberg)
           Stage combinations: operate on state Y = [r, v] where r' = v, v' = a(r,v)
           k_i_r = velocity estimate, k_i_v = accel estimate */

        /* Compute k1 */
        V3dT k1_r = velocity_vector;
        V3dT k1_v = _accel_for_state(eng, &range_vector, &velocity_vector, NULL, NULL, &wind_vector);

        /* k2: at t + 1/4 dt */
        V3dT r_k2 = V3d_add(range_vector, V3d_mulS(k1_r, dt * 0.25));
        V3dT v_k2 = V3d_add(velocity_vector, V3d_mulS(k1_v, dt * 0.25));
        V3dT k2_r = v_k2;
        V3dT k2_v = _accel_for_state(eng, &r_k2, &v_k2, NULL, NULL, NULL);

        /* k3: at t + 3/8 dt */
        V3dT r_k3 = V3d_add(range_vector, V3d_add(V3d_mulS(k1_r, dt * (3.0/32.0)), V3d_mulS(k2_r, dt * (9.0/32.0))));
        V3dT v_k3 = V3d_add(velocity_vector, V3d_add(V3d_mulS(k1_v, dt * (3.0/32.0)), V3d_mulS(k2_v, dt * (9.0/32.0))));
        V3dT k3_r = v_k3;
        V3dT k3_v = _accel_for_state(eng, &r_k3, &v_k3, NULL, NULL, NULL);

        /* k4: at t + 12/13 dt */
        V3dT r_k4 = V3d_add(range_vector,
                    V3d_add(V3d_mulS(k1_r, dt * (1932.0/2197.0)),
                    V3d_add(V3d_mulS(k2_r, dt * (-7200.0/2197.0)), V3d_mulS(k3_r, dt * (7296.0/2197.0)))));
        V3dT v_k4 = V3d_add(velocity_vector,
                    V3d_add(V3d_mulS(k1_v, dt * (1932.0/2197.0)),
                    V3d_add(V3d_mulS(k2_v, dt * (-7200.0/2197.0)), V3d_mulS(k3_v, dt * (7296.0/2197.0)))));
        V3dT k4_r = v_k4;
        V3dT k4_v = _accel_for_state(eng, &r_k4, &v_k4, NULL, NULL, NULL);

        /* k5: at t + 1 dt */
        V3dT r_k5 = V3d_add(range_vector,
                    V3d_add(V3d_mulS(k1_r, dt * (439.0/216.0)),
                    V3d_add(V3d_mulS(k2_r, dt * -8.0),
                    V3d_add(V3d_mulS(k3_r, dt * (3680.0/513.0)),
                            V3d_mulS(k4_r, dt * (-845.0/4104.0))))));
        V3dT v_k5 = V3d_add(velocity_vector,
                    V3d_add(V3d_mulS(k1_v, dt * (439.0/216.0)),
                    V3d_add(V3d_mulS(k2_v, dt * -8.0),
                    V3d_add(V3d_mulS(k3_v, dt * (3680.0/513.0)),
                            V3d_mulS(k4_v, dt * (-845.0/4104.0))))));
        V3dT k5_r = v_k5;
        V3dT k5_v = _accel_for_state(eng, &r_k5, &v_k5, NULL, NULL, NULL);

        /* k6: at t + 1/2 dt */
        V3dT r_k6 = V3d_add(range_vector,
                    V3d_add(V3d_mulS(k1_r, dt * (-8.0/27.0)),
                    V3d_add(V3d_mulS(k2_r, dt * 2.0),
                    V3d_add(V3d_mulS(k3_r, dt * (-3544.0/2565.0)),
                    V3d_add(V3d_mulS(k4_r, dt * (1859.0/4104.0)), V3d_mulS(k5_r, dt * (-11.0/40.0)))))));
        V3dT v_k6 = V3d_add(velocity_vector,
                    V3d_add(V3d_mulS(k1_v, dt * (-8.0/27.0)),
                    V3d_add(V3d_mulS(k2_v, dt * 2.0),
                    V3d_add(V3d_mulS(k3_v, dt * (-3544.0/2565.0)),
                    V3d_add(V3d_mulS(k4_v, dt * (1859.0/4104.0)), V3d_mulS(k5_v, dt * (-11.0/40.0)))))));
        V3dT k6_r = v_k6;
        V3dT k6_v = _accel_for_state(eng, &r_k6, &v_k6, NULL, NULL, NULL);

        /* 5th-order estimate for delta v and delta r */
        V3dT delta_v_5 = V3d_add(
                                V3d_mulS(k1_v, dt * (16.0/135.0)),
                                V3d_add(V3d_mulS(k3_v, dt * (6656.0/12825.0)),
                                V3d_add(V3d_mulS(k4_v, dt * (28561.0/56430.0)),
                                V3d_add(V3d_mulS(k5_v, dt * (-9.0/50.0)), V3d_mulS(k6_v, dt * (2.0/55.0))))));
        V3dT delta_r_5 = V3d_add(
                                V3d_mulS(k1_r, dt * (16.0/135.0)),
                                V3d_add(V3d_mulS(k3_r, dt * (6656.0/12825.0)),
                                V3d_add(V3d_mulS(k4_r, dt * (28561.0/56430.0)),
                                V3d_add(V3d_mulS(k5_r, dt * (-9.0/50.0)), V3d_mulS(k6_r, dt * (2.0/55.0))))));

        /* 4th-order estimate */
        V3dT delta_v_4 = V3d_add(
                                V3d_mulS(k1_v, dt * (25.0/216.0)),
                                V3d_add(V3d_mulS(k3_v, dt * (1408.0/2565.0)),
                                V3d_add(V3d_mulS(k4_v, dt * (2197.0/4104.0)), V3d_mulS(k5_v, dt * (-1.0/5.0)))));
        V3dT delta_r_4 = V3d_add(
                                V3d_mulS(k1_r, dt * (25.0/216.0)),
                                V3d_add(V3d_mulS(k3_r, dt * (1408.0/2565.0)),
                                V3d_add(V3d_mulS(k4_r, dt * (2197.0/4104.0)), V3d_mulS(k5_r, dt * (-1.0/5.0)))));

        /* Error estimate: combine position and velocity */
        V3dT err_r = V3d_sub(delta_r_5, delta_r_4);
        V3dT err_v = V3d_sub(delta_v_5, delta_v_4);
        double err_r_norm = sqrt(err_r.x*err_r.x + err_r.y*err_r.y + err_r.z*err_r.z);
        double err_v_norm = sqrt(err_v.x*err_v.x + err_v.y*err_v.y + err_v.z*err_v.z);

        /* combined norm: take the maximum */
        double err_norm = fmax(err_r_norm, err_v_norm);

        /* scale threshold considering state norms (absolute + relative) */
        double tol = ABS_TOL;
        /* adaptive scaling by state (can be made more complex) */
        double accept_tol = tol + REL_TOL * fmax(V3d_mag(&range_vector), V3d_mag(&velocity_vector));

        /* if error too large — reduce dt and repeat (do not accept step) */
        if (err_norm > accept_tol && dt > DT_MIN)
        {
            double scale = SAFETY * pow(accept_tol / (err_norm + 1e-30), 0.25);
            scale = fmin(fmax(scale, MIN_SCALE), MAX_SCALE);
            dt = fmax(dt * scale, DT_MIN);
            /* do not increment eng->integration_step_count, do not save point, repeat */
            continue;
        }

        /* Accept step: update state */
        range_vector = V3d_add(range_vector, delta_r_5);
        velocity_vector = V3d_add(velocity_vector, delta_v_5);
        time += dt;

        /* update mach/density for recording */
        Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, eng->shot.alt0 + range_vector.y, &density_ratio, &mach);
        if (mach <= 0.0) mach = 1e-6;

        /* Record point */
        BaseTrajSeq_t_append(traj_seq_ptr,
                             time,
                             range_vector.x, range_vector.y, range_vector.z,
                             velocity_vector.x, velocity_vector.y, velocity_vector.z,
                             mach);

        /* increment step counter (keep as in Euler: count passed steps) */
        eng->integration_step_count++;

        /* Check terminal conditions (as in original) */
        double cur_speed = V3d_mag(&velocity_vector);
        if (cur_speed < _cMinimumVelocity)
        {
            *reason = RANGE_ERROR_MINIMUM_VELOCITY_REACHED;
            break;
        }
        else if (range_vector.y < _cMaximumDrop)
        {
            *reason = RANGE_ERROR_MAXIMUM_DROP_REACHED;
            break;
        }
        else if (velocity_vector.y <= 0.0 && (eng->shot.alt0 + range_vector.y < _cMinimumAltitude))
        {
            *reason = RANGE_ERROR_MINIMUM_ALTITUDE_REACHED;
            break;
        }

        /* increase dt if error very small */
        if (err_norm < (accept_tol * 0.1) && dt < DT_MAX)
        {
            double scale = SAFETY * pow(accept_tol / (err_norm + 1e-30), 0.2); /* more conservative increase */
            scale = fmin(fmax(scale, 1.0), MAX_SCALE);
            dt = fmin(dt * scale, DT_MAX);
        }
    } /* end while */

    /* Append last point (as in Euler) */
    Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, eng->shot.alt0 + range_vector.y, &density_ratio, &mach);
    BaseTrajSeq_t_append(traj_seq_ptr,
                         time,
                         range_vector.x, range_vector.y, range_vector.z,
                         velocity_vector.x, velocity_vector.y, velocity_vector.z,
                         mach);

    C_LOG(LOG_LEVEL_DEBUG, "RK45 exit, reason=%d, steps=%u\n", *reason, (unsigned)eng->integration_step_count);
    return STATUS_SUCCESS;
}
