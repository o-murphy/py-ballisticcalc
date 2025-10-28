#include <math.h>
#include "euler.h"
// #include "bclib.h"  // for C_LOG

/* -- inline V3 helpers (avoids unnecessary copying) -- */
static inline V3dT v3_add(const V3dT *a, const V3dT *b)
{
    V3dT r;
    r.x = a->x + b->x;
    r.y = a->y + b->y;
    r.z = a->z + b->z;
    return r;
}
static inline V3dT v3_sub(const V3dT *a, const V3dT *b)
{
    V3dT r;
    r.x = a->x - b->x;
    r.y = a->y - b->y;
    r.z = a->z - b->z;
    return r;
}
static inline V3dT v3_mul_s(const V3dT *a, double s)
{
    V3dT r;
    r.x = a->x * s;
    r.y = a->y * s;
    r.z = a->z * s;
    return r;
}
static inline double v3_mag(const V3dT *a)
{
    return sqrt(a->x * a->x + a->y * a->y + a->z * a->z);
}

/* inline time step helper */
static inline double _euler_time_step(double base_step, double velocity)
{
    double divisor = velocity > 1.0 ? velocity : 1.0;
    return base_step / divisor;
}

/* Euler–Cromer Implementation (semi-implicit Euler) */
StatusCode _integrate_euler_cromer(
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

    double velocity = 0.0;
    double delta_time = 0.0;
    double density_ratio = 0.0;
    double mach = 0.0;
    double time = 0.0;
    double drag = 0.0;
    double km = 0.0;
    V3dT range_vector;
    V3dT velocity_vector;
    V3dT relative_velocity;
    V3dT gravity_vector;
    V3dT wind_vector;
    V3dT coriolis_accel;
    double calc_step = eng->shot.calc_step;

    // Early binding of configuration constants
    double _cMinimumVelocity = eng->config.cMinimumVelocity;
    double _cMinimumAltitude = eng->config.cMinimumAltitude;
    double _cMaximumDrop = -fabs(eng->config.cMaximumDrop);

    *reason = NO_TERMINATE;
    double relative_speed = 0.0;
    V3dT _dir_vector;
    V3dT _tv;
    V3dT delta_range_vector;
    eng->integration_step_count = 0;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = eng->config.cGravityConstant;
    gravity_vector.z = 0.0;

    // Initialize wind vector
    wind_vector = WindSock_t_currentVector(&eng->shot.wind_sock);

    // Initialize velocity and position vectors
    velocity = eng->shot.muzzle_velocity;

    // Set range_vector components
    range_vector.x = 0.0;
    range_vector.y = -eng->shot.cant_cosine * eng->shot.sight_height;
    range_vector.z = -eng->shot.cant_sine * eng->shot.sight_height;
    _cMaximumDrop += (range_vector.y < 0.0 ? range_vector.y : 0.0);

    /* Barrel direction (cache cos/sin) */
    double cos_elev = cos(eng->shot.barrel_elevation);
    double sin_elev = sin(eng->shot.barrel_elevation);
    double cos_az = cos(eng->shot.barrel_azimuth);
    double sin_az = sin(eng->shot.barrel_azimuth);

    // Set direction vector components
    _dir_vector.x = cos_elev * cos_az;
    _dir_vector.y = sin_elev;
    _dir_vector.z = cos_elev * sin_az;

    // Calculate velocity vector
    velocity_vector = v3_mul_s(&_dir_vector, velocity);

    // Update air density and mach at initial altitude
    double altitude = eng->shot.alt0 + range_vector.y;
    Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, altitude, &density_ratio, &mach);
    if (mach <= 0.0)
        mach = 1e-6; /* safe minimum */

    /* Setting the atmosphere refresh interval (to reduce costs) */
    const int atmos_update_interval = 4; /* can be changed; 1 = update every step */
    int atmos_step_counter = 0;

    /* Loop: Euler–Cromer (v_{n+1} = v_n + a_n * dt; x_{n+1} = x_n + v_{n+1} * dt) */
    while (range_vector.x <= range_limit_ft || eng->integration_step_count < 3)
    {
        eng->integration_step_count++;

        // Update wind reading at current point in trajectory
        if (range_vector.x >= eng->shot.wind_sock.next_range)
        {
            wind_vector = WindSock_t_vectorForRange(&eng->shot.wind_sock, range_vector.x);
        }

        // Update air density and mach at current altitude
        if (atmos_step_counter == 0)
        {
            altitude = eng->shot.alt0 + range_vector.y;
            Atmosphere_t_updateDensityFactorAndMachForAltitude(&eng->shot.atmo, altitude, &density_ratio, &mach);
            if (mach <= 0.0)
                mach = 1e-6;
        }
        atmos_step_counter = (atmos_step_counter + 1) % atmos_update_interval;

        // Store point in trajectory sequence
        BaseTrajSeq_t_append(
            traj_seq_ptr,
            time,
            range_vector.x, range_vector.y, range_vector.z,
            velocity_vector.x, velocity_vector.y, velocity_vector.z,
            mach);

        /* 1) relative velocity */
        relative_velocity = v3_sub(&velocity_vector, &wind_vector);
        relative_speed = v3_mag(&relative_velocity);

        // 2. Calculate time step (adaptive based on velocity)
        delta_time = _euler_time_step(calc_step, relative_speed);

        /* 3) drag: km = density_ratio * dragByMach; drag = km * speed */
        /* division by zero protection: mach is already protected above */
        km = density_ratio * ShotProps_t_dragByMach(&eng->shot, relative_speed / mach);
        drag = km * relative_speed;

        /* 4) acceleration calculation: a = gravity - relative_velocity * drag (+ coriolis) */
        _tv = v3_mul_s(&relative_velocity, drag); /* _tv = relative * drag (force per unit mass) */
        _tv = v3_sub(&gravity_vector, &_tv);      /* _tv = gravity - drag_term */

        if (!eng->shot.coriolis.flat_fire_only)
        {
            Coriolis_t_coriolis_acceleration_local(&eng->shot.coriolis, &velocity_vector, &coriolis_accel);
            _tv = v3_add(&_tv, &coriolis_accel);
        }

        /* 4a) Updating velocity (v_{n+1} = v_n + a_n * dt) */
        V3dT dv = v3_mul_s(&_tv, delta_time);
        velocity_vector = v3_add(&velocity_vector, &dv);

        /* 5) We update the position using the already updated speed => Euler–Cromer */
        delta_range_vector = v3_mul_s(&velocity_vector, delta_time);
        range_vector = v3_add(&range_vector, &delta_range_vector);

        // 6. Update time and velocity magnitude
        velocity = v3_mag(&velocity_vector);
        time += delta_time;

        // Check termination conditions
        if (velocity < _cMinimumVelocity)
        {
            *reason = RANGE_ERROR_MINIMUM_VELOCITY_REACHED;
        }
        else if (range_vector.y < _cMaximumDrop)
        {
            *reason = RANGE_ERROR_MAXIMUM_DROP_REACHED;
        }
        else if (velocity_vector.y <= 0.0 && (eng->shot.alt0 + range_vector.y < _cMinimumAltitude))
        {
            *reason = RANGE_ERROR_MINIMUM_ALTITUDE_REACHED;
        }

        if (*reason != NO_TERMINATE)
        {
            break;
        }
    }

    // Add final data point
    BaseTrajSeq_t_append(
        traj_seq_ptr,
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach);

    C_LOG(LOG_LEVEL_DEBUG, "Function exit, reason=%d\n", *reason);

    return STATUS_SUCCESS;
}
