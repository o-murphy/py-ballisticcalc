#include <cstddef> // For size_t
#include <cstdlib>
#include <cmath>
#include <stdexcept>
#include "bclibc/base_types.hpp"

namespace bclibc
{

    // Constants for unit conversions and atmospheric calculations
    /**
     * @brief Earth's angular velocity in radians per second.
     */
    const double BCLIBC_cEarthAngularVelocityRadS = 7.2921159e-5;
    /**
     * @brief Conversion factor from degrees Fahrenheit to degrees Rankine.
     */
    const double BCLIBC_cDegreesFtoR = 459.67;
    /**
     * @brief Conversion factor from degrees Celsius to Kelvin.
     */
    const double BCLIBC_cDegreesCtoK = 273.15;
    /**
     * @brief Constant for speed of sound calculation in Imperial units (fps).
     *
     * (Approx. $\sqrt{\gamma R}$)
     */
    const double BCLIBC_cSpeedOfSoundImperial = 49.0223;
    /**
     * @brief Constant for speed of sound calculation in Metric units.
     *
     * (Approx. $\sqrt{\gamma R}$)
     */
    const double BCLIBC_cSpeedOfSoundMetric = 20.0467;
    /**
     * @brief Standard lapse rate in Kelvin per foot in the troposphere.
     */
    const double BCLIBC_cLapseRateKperFoot = -0.0019812;
    /**
     * @brief Standard lapse rate in Imperial units (degrees per foot).
     */
    const double BCLIBC_cLapseRateImperial = -0.00356616;
    /**
     * @brief Exponent used in the barometric formula for pressure calculation.
     *
     * (Approx. $g / (L \cdot R)$)
     */
    const double BCLIBC_cPressureExponent = 5.255876;
    /**
     * @brief Lowest allowed temperature in Fahrenheit for atmospheric model.
     */
    const double BCLIBC_cLowestTempF = -130.0;
    /**
     * @brief Conversion factor from meters to feet.
     */
    const double BCLIBC_mToFeet = 3.280839895;
    /**
     * @brief Maximum distance in feet for a wind segment (used as a sentinel value).
     */
    const double BCLIBC_cMaxWindDistanceFeet = 1e8;

    const double BCLIBC_cGravityImperial = 32.17405;

    BCLIBC_Config::BCLIBC_Config(
        double cStepMultiplier,
        double cZeroFindingAccuracy,
        double cMinimumVelocity,
        double cMaximumDrop,
        int cMaxIterations,
        double cGravityConstant,
        double cMinimumAltitude)
        : cStepMultiplier(cStepMultiplier),
          cZeroFindingAccuracy(cZeroFindingAccuracy),
          cMinimumVelocity(cMinimumVelocity),
          cMaximumDrop(cMaximumDrop),
          cMaxIterations(cMaxIterations),
          cGravityConstant(cGravityConstant),
          cMinimumAltitude(cMinimumAltitude) {};

    BCLIBC_CurvePoint::BCLIBC_CurvePoint(
        double a, double b, double c, double d) : a(a), b(b), c(c), d(d) {};

    BCLIBC_ShotProps::BCLIBC_ShotProps(
        double bc,
        double look_angle,
        double twist,
        double length,
        double diameter,
        double weight,
        double barrel_elevation,
        double barrel_azimuth,
        double sight_height,
        double cant_cosine,
        double cant_sine,
        double alt0,
        double calc_step,
        double muzzle_velocity,
        double stability_coefficient,
        BCLIBC_Curve curve,
        BCLIBC_MachList mach_list,
        BCLIBC_Atmosphere atmo,
        BCLIBC_Coriolis coriolis,
        BCLIBC_WindSock wind_sock,
        BCLIBC_TrajFlag filter_flags)
        : bc(bc),
          look_angle(look_angle),
          twist(twist),
          length(length),
          diameter(diameter),
          weight(weight),
          barrel_elevation(barrel_elevation),
          barrel_azimuth(barrel_azimuth),
          sight_height(sight_height),
          cant_cosine(cant_cosine),
          cant_sine(cant_sine),
          alt0(alt0),
          calc_step(calc_step),
          muzzle_velocity(muzzle_velocity),
          stability_coefficient(stability_coefficient),
          curve(curve),
          mach_list(mach_list),
          atmo(atmo),
          coriolis(coriolis),
          wind_sock(wind_sock),
          filter_flags(filter_flags)
    {
        // Assume can return only ZERO_DIVISION_ERROR or NO_ERROR
        if (this->update_stability_coefficient() != BCLIBC_ErrorType::NO_ERROR)
        {
            throw std::runtime_error("Zero division detected in BCLIBC_ShotProps.update_stability_coefficient");
        };
    };

    BCLIBC_ShotProps::~BCLIBC_ShotProps() {
        BCLIBC_DEBUG("Approx size of shotprops in memory: %zu bytes", this->size());
    };

    /**
     * @brief Litz spin-drift approximation
     *
     * Calculates the lateral displacement (windage) due to spin drift using
     * Litz's approximation formula. This formula provides an estimate based on
     * the stability coefficient and time of flight.
     *
     * Formula used (converted to feet):
     * $\text{Spin Drift (ft)} = \text{sign} \cdot \frac{1.25 \cdot (S_g + 1.2) \cdot \text{time}^{1.83}}{12.0}$
     * where $S_g$ is the stability coefficient.
     *
     * @param time Time of flight in seconds.
     * @return Windage due to spin drift, in feet. Returns 0.0 if twist or stability_coefficient is zero.
     */
    double BCLIBC_ShotProps::spin_drift(double time) const
    {
        double sign;

        // Check if twist and stability_coefficient are non-zero.
        // In C, comparing doubles directly to 0 can sometimes be problematic due to
        // floating-point precision. However, for typical use cases here, direct
        // comparison with 0 is often acceptable if the values are expected to be
        // exactly 0 or significantly non-zero. If extreme precision is needed for
        // checking "effectively zero", you might use an epsilon (e.g., fabs(val) > EPSILON).
        if (this->twist != 0 && this->stability_coefficient != 0)
        {
            // Determine the sign based on twist direction.
            if (this->twist > 0)
            {
                sign = 1.0;
            }
            else
            {
                sign = -1.0;
            }
            // Calculate the spin drift using the Litz approximation formula.
            // The division by 12 converts the result from inches (implied by Litz formula) to feet.
            return sign * (1.25 * (this->stability_coefficient + 1.2) * std::pow(time, 1.83)) / 12.0;
        }
        // If either twist or stability_coefficient is zero, return 0.
        return 0.0;
    }

    /**
     * @brief Updates the Miller stability coefficient ($S_g$) for the projectile.
     *
     * Calculates the Miller stability coefficient based on bullet dimensions, weight,
     * muzzle velocity, and atmospheric conditions ($\text{temperature, pressure}$).
     * The result is stored in `this->stability_coefficient`.
     *
     * Formula components:
     * - $\text{sd}$ (Stability Divisor)
     * - $\text{fv}$ (Velocity Factor)
     * - $\text{ftp}$ (Temperature/Pressure Factor)
     * - $S_g = \text{sd} \cdot \text{fv} \cdot \text{ftp}$
     *
     * @return BCLIBC_ErrorType::NO_ERROR on success, BCLIBC_ErrorType::INPUT_ERROR for NULL input, BCLIBC_ErrorType::ZERO_DIVISION_ERROR if a division by zero occurs during calculation.
     */
    BCLIBC_ErrorType BCLIBC_ShotProps::update_stability_coefficient()
    {
        /* Miller stability coefficient */
        double twist_rate, length, sd, fv, ft, pt, ftp;

        // Check for non-zero or valid input values before calculation
        if (this->twist != 0.0 &&
            this->length != 0.0 &&
            this->diameter != 0.0 &&
            this->atmo._p0 != 0.0)
        {
            twist_rate = std::fabs(this->twist) / this->diameter;
            length = this->length / this->diameter;

            // Ensure denominator components are non-zero to avoid division by zero
            // This check is crucial for robustness in C
            double denom_part1 = std::pow(twist_rate, 2);
            double denom_part2 = std::pow(this->diameter, 3);
            double denom_part3 = length;
            double denom_part4 = (1 + std::pow(length, 2));

            if (denom_part1 != 0.0 && denom_part2 != 0.0 && denom_part3 != 0.0 && denom_part4 != 0.0)
            {
                sd = 30.0 * this->weight / (denom_part1 * denom_part2 * denom_part3 * denom_part4);
            }
            else
            {
                this->stability_coefficient = 0.0;
                BCLIBC_ERROR("Division by zero in stability coefficient calculation.");
                return BCLIBC_ErrorType::ZERO_DIVISION_ERROR; // Exit if denominator is zero
            }

            fv = std::pow(this->muzzle_velocity / 2800.0, 1.0 / 3.0);
            ft = (this->atmo._t0 * 9.0 / 5.0) + 32.0; // Convert from Celsius to Fahrenheit
            pt = this->atmo._p0 / 33.863881565591;    // Convert hPa to inHg

            // Ensure pt is not zero before division
            if (pt != 0.0)
            {
                ftp = ((ft + 460.0) / (59.0 + 460.0)) * (29.92 / pt);
            }
            else
            {
                this->stability_coefficient = 0.0;
                BCLIBC_ERROR("Division by zero in ftp calculation.");
                return BCLIBC_ErrorType::ZERO_DIVISION_ERROR; // Exit if pt is zero
            }

            this->stability_coefficient = sd * fv * ftp;
        }
        else
        {
            // If critical parameters are zero, stability coefficient is meaningless or zero
            this->stability_coefficient = 0.0;
        }
        BCLIBC_DEBUG("Updated stability coefficient: %.6f", this->stability_coefficient);
        return BCLIBC_ErrorType::NO_ERROR;
    };

    /**
     * @brief Interpolates a value from a Mach list and a curve using the PCHIP method.
     *
     * This function performs an optimized binary search to find the correct segment
     * in the `mach_list_ptr` and then uses the corresponding cubic polynomial segment
     * from `curve_ptr` (Horner's method) to interpolate the value at the given Mach number.
     *
     * The curve is assumed to represent the ballistic coefficient or a drag curve.
     *
     * @param mach_list_ptr Pointer to the BCLIBC_MachList containing the Mach segment endpoints (x values).
     * @param curve_ptr Pointer to the BCLIBC_Curve containing the PCHIP cubic segment coefficients (a, b, c, d).
     * @param mach The Mach number at which to interpolate.
     * @return The interpolated value (e.g., drag coefficient or BC factor). Returns 0.0 if insufficient data or out of range.
     */
    static inline double calculateByCurveAndMachList(
        const BCLIBC_MachList *mach_list_ptr, // const std::vector<double>*
        const BCLIBC_Curve *curve_ptr,        // const std::vector<BCLIBC_CurvePoint>*
        double mach)
    {
        // Curve has (n-1) segments. MachList has n nodes.
        const size_t nm1_size_t = curve_ptr->size(); // number of segments (n-1)
        if (nm1_size_t == 0)
        {
            // insufficient curve data
            return 0.0;
        }

        const size_t n_size_t = mach_list_ptr->size(); // number of Mach nodes (n)
        if (n_size_t != nm1_size_t + 1)
        {
            // data mismatch; cannot interpolate safely
            return 0.0;
        }

        const int nm1 = (int)nm1_size_t; // n-1
        const int n = nm1 + 1;           // n

        const double *xs = mach_list_ptr->data();

        if (n < 2)
        {
            // insufficient Mach data
            return 0.0;
        }

        // Determine segment index i such that xs[i] <= mach <= xs[i+1]
        int i;

        // Clamp to range endpoints
        if (mach <= xs[0])
        {
            i = 0; // use first segment
        }
        else if (mach >= xs[n - 1])
        {
            i = nm1 - 1; // last valid segment index = (n-1)-1 = n-2
        }
        else
        {
            // Optimized binary search
            int lo = 0, hi = n - 1;
            while (lo < hi)
            {
                int mid = lo + ((hi - lo) >> 1);
                if (xs[mid] < mach)
                    lo = mid + 1;
                else
                    hi = mid;
            }
            i = lo - 1;

            // Ensure index in valid segment range
            if (i < 0)
                i = 0;
            else if (i > nm1 - 1)
                i = nm1 - 1;
        }

        // Access the corresponding segment safely
        const BCLIBC_CurvePoint seg = (*curve_ptr)[i];

        const double dx = mach - xs[i];

        // Horner's method for PCHIP interpolation:
        // y = d + dx * (c + dx * (b + dx * a))
        return seg.d + dx * (seg.c + dx * (seg.b + dx * seg.a));
    }

    /**
     * @brief Computes the scaled drag force coefficient ($C_d$) for a projectile at a given Mach number.
     *
     * This function calculates the drag coefficient using a cubic spline interpolation
     * (via `calculateByCurveAndMachList`) and scales it by a constant factor and the
     * bullet's ballistic coefficient (BC). The result is $\frac{C_d}{\text{BC} \cdot \text{scale\_factor}}$.
     *
     * The constant $2.08551\text{e-}04$ is a combination of standard air density,
     * cross-sectional area conversion, and mass conversion factors.
     *
     * Formula used:
     * $\text{Scaled } C_d = \frac{C_d(\text{Mach}) \cdot 2.08551\text{e-}04}{\text{BC}}$
     *
     * @param mach Mach number at which to evaluate the drag.
     * @return Drag coefficient $C_d$ scaled by $\text{BC}$ and conversion factors, in units suitable for the trajectory calculation.
     */
    double BCLIBC_ShotProps::drag_by_mach(double mach) const
    {
        double cd = calculateByCurveAndMachList(
            &this->mach_list,
            &this->curve,
            mach);
        return cd * 2.08551e-04 / this->bc;
    }

    size_t BCLIBC_ShotProps::size() const
    {
        size_t total_size = sizeof(*this);
        total_size += curve.size() * sizeof(BCLIBC_CurvePoint);
        total_size += mach_list.size() * sizeof(double);
        total_size += wind_sock.winds.size() * sizeof(BCLIBC_Wind);
        return total_size;
    }

    BCLIBC_Atmosphere::BCLIBC_Atmosphere(
        double _t0,
        double _a0,
        double _p0,
        double _mach,
        double density_ratio,
        double cLowestTempC)
        : _t0(_t0),
          _a0(_a0),
          _p0(_p0),
          _mach(_mach),
          density_ratio(density_ratio),
          cLowestTempC(cLowestTempC) {};

    /**
     * @brief Updates the density ratio and speed of sound (Mach 1) for a given altitude.
     *
     * This function calculates the new atmospheric pressure, temperature, and resulting
     * density ratio and speed of sound (Mach 1) at a given altitude using the
     * Standard Atmosphere model for the troposphere, adjusted for base conditions ($\text{atmo\_ptr->_t0, atmo\_ptr->_p0, atmo\_ptr->_a0}$).
     *
     * The barometric formula is used for pressure, and the lapse rate for temperature.
     *
     * @param altitude The new altitude in feet.
     * @param density_ratio_ptr Pointer to store the calculated density ratio ($\rho / \rho_{\text{std}}$).
     * @param mach_ptr Pointer to store the calculated speed of sound (Mach 1) in feet per second (fps).
     */
    void BCLIBC_Atmosphere::update_density_factor_and_mach_for_altitude(
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr) const
    {
        const double alt_diff = altitude - this->_a0;

        // Fast check: if altitude is close to base altitude, use stored values
        if (std::fabs(alt_diff) < 30.0)
        {
            // Close enough to base altitude, use stored values
            *density_ratio_ptr = this->density_ratio;
            *mach_ptr = this->_mach;
            return;
        }

        double celsius = alt_diff * BCLIBC_cLapseRateKperFoot + this->_t0;

        if (altitude > 36089.0)
        {
            // Warning: altitude above standard troposphere height
            BCLIBC_WARN("Density request for altitude above troposphere. Atmospheric model not valid here.");
        }

        // Clamp temperature to prevent non-physical results
        const double min_temp = -BCLIBC_cDegreesCtoK;
        if (celsius < min_temp)
        {
            BCLIBC_WARN("Invalid temperature %.2f °C. Adjusted to %.2f °C.", celsius, min_temp);
            celsius = min_temp;
        }
        else if (celsius < this->cLowestTempC)
        {
            celsius = this->cLowestTempC;
            BCLIBC_WARN("Reached minimum temperature limit. Adjusted to %.2f °C.", celsius);
        }

        const double kelvin = celsius + BCLIBC_cDegreesCtoK;
        const double base_kelvin = this->_t0 + BCLIBC_cDegreesCtoK;

        // Pressure calculation using barometric formula for the troposphere
        // $P = P_0 \cdot (1 + \frac{L \cdot \Delta h}{T_0})^ {g / (L \cdot R)}$
        const double pressure = this->_p0 * std::pow(
                                                1.0 + BCLIBC_cLapseRateKperFoot * alt_diff / base_kelvin,
                                                BCLIBC_cPressureExponent);

        // Density ratio calculation: $\frac{\rho}{\rho_{\text{std}}} = \frac{\rho_0}{\rho_{\text{std}}} \cdot \frac{P \cdot T_0}{P_0 \cdot T}$
        const double density_delta = (base_kelvin * pressure) / (this->_p0 * kelvin);

        *density_ratio_ptr = this->density_ratio * density_delta;

        // Mach 1 speed at altitude (fps): $a = \sqrt{\gamma R T}$
        *mach_ptr = std::sqrt(kelvin) * BCLIBC_cSpeedOfSoundMetric * BCLIBC_mToFeet;

        BCLIBC_DEBUG("Altitude: %.2f, Base Temp: %.2f°C, Current Temp: %.2f°C, Base Pressure: %.2f hPa, Current Pressure: %.2f hPa, Density ratio: %.6f\n",
                     altitude, this->_t0, celsius, this->_p0, pressure, *density_ratio_ptr);
    };

    BCLIBC_Wind::BCLIBC_Wind(double velocity,
                             double direction_from,
                             double until_distance,
                             double MAX_DISTANCE_FEET)
        : velocity(velocity),
          direction_from(direction_from),
          until_distance(until_distance),
          MAX_DISTANCE_FEET(MAX_DISTANCE_FEET) {};

    /**
     * @brief Converts a BCLIBC_Wind structure to a BCLIBC_V3dT vector.
     *
     * The wind vector components are calculated assuming a standard coordinate system
     * where x is positive downrange and z is positive across-range (windage).
     * Wind direction is 'from' the specified direction (e.g., $0^\circ$ is tailwind, $90^\circ$ is wind from the right).
     *
     * @return A BCLIBC_V3dT structure representing the wind velocity vector (x=downrange, y=vertical, z=crossrange).
     */
    BCLIBC_V3dT BCLIBC_Wind::as_vector() const
    {
        const double dir = this->direction_from;
        const double vel = this->velocity;

        // Wind direction is from:
        // x = vel * cos(dir) (Downrange, positive is tailwind)
        // z = vel * sin(dir) (Crossrange, positive is wind from right)
        return BCLIBC_V3dT{
            vel * std::cos(dir), 0.0, vel * std::sin(dir)};
    }

    /**
     * @brief Default constructor for BCLIBC_WindSock.
     *
     * Initializes state variables to their defaults and calculates the initial cache.
     */
    BCLIBC_WindSock::BCLIBC_WindSock()
        // Використовуємо список ініціалізації для гарантованого встановлення значень
        : current(0),
          next_range(BCLIBC_cMaxWindDistanceFeet),
          last_vector_cache({0.0, 0.0, 0.0})
    {
        // C++ конструктори не можуть повертати значення.
        // update_cache() викликається тут для початкового стану (який буде нульовим, оскільки winds порожній).
        update_cache();
    }

    void BCLIBC_WindSock::push(BCLIBC_Wind wind)
    {
        this->winds.push_back(wind);
    }

    /**
     * @brief Returns the wind vector for the currently active wind segment.
     *
     * The vector is pre-calculated and stored in the cache.
     *
     * @return The current wind velocity vector (BCLIBC_V3dT). Returns a zero vector if the pointer is NULL.
     */
    BCLIBC_V3dT BCLIBC_WindSock::current_vector() const
    {
        return this->last_vector_cache;
    }

    /**
     * @brief Updates the internal wind vector cache and next range threshold.
     *
     * Fetches the data for the wind segment at `ws->current`, converts it to a vector,
     * and updates `ws->last_vector_cache` and `ws->next_range`.
     * If `ws->current` is out of bounds, the cache is set to a zero vector and the next range to `BCLIBC_cMaxWindDistanceFeet`.
     *
     * @return BCLIBC_ErrorType::NO_ERROR on success, BCLIBC_ErrorType::INPUT_ERROR for NULL input.
     */
    BCLIBC_ErrorType BCLIBC_WindSock::update_cache()
    {
        if (this->current < this->winds.size())
        {
            const BCLIBC_Wind &cur_wind = this->winds[this->current];
            this->last_vector_cache = cur_wind.as_vector();
            this->next_range = cur_wind.until_distance;
        }
        else
        {
            this->last_vector_cache.x = 0.0;
            this->last_vector_cache.y = 0.0;
            this->last_vector_cache.z = 0.0;
            this->next_range = BCLIBC_cMaxWindDistanceFeet;
        }
        return BCLIBC_ErrorType::NO_ERROR;
    }

    /**
     * @brief Gets the current wind vector, updating to the next segment if necessary.
     *
     * Compares the given `next_range_param` (the current range in the simulation)
     * against the threshold for the current wind segment (`ws->next_range`).
     * If the threshold is met or exceeded, it advances to the next wind segment
     * and updates the cache.
     *
     * @param ws Pointer to the BCLIBC_WindSock structure.
     * @param next_range_param The current range (distance from muzzle) of the projectile.
     * @return The wind velocity vector (BCLIBC_V3dT) for the current or next applicable segment. Returns a zero vector if the pointer is NULL or an update fails.
     */
    BCLIBC_V3dT BCLIBC_WindSock::vector_for_range(double next_range_param)
    {
        BCLIBC_V3dT zero_vector = {0.0, 0.0, 0.0};

        if (next_range_param >= this->next_range)
        {
            this->current += 1;

            if (this->current >= this->winds.size())
            {
                // Reached the end of the wind segments
                this->last_vector_cache = zero_vector;
                this->next_range = BCLIBC_cMaxWindDistanceFeet;
            }
            else
            {
                // Move to the next wind segment
                // If cache update fails, return zero vector
                if (this->update_cache() != BCLIBC_ErrorType::NO_ERROR)
                {
                    BCLIBC_WARN("Failed. Returning zero vector.");
                    return zero_vector;
                }
            }
        }

        return this->last_vector_cache;
    }

    // helpers
    /**
     * @brief Calculates the angular correction needed to hit a target.
     *
     * Computes the angle (in radians) to correct a shot based on the linear offset
     * at a given distance using the arc tangent function ($\arctan(\text{offset}/\text{distance})$).
     *
     * @param distance The distance to the target (or the point of offset).
     * @param offset The linear offset (e.g., vertical drop or windage).
     * @return The correction angle in radians. Returns 0.0 if distance is zero (to avoid division by zero).
     */
    double BCLIBC_getCorrection(double distance, double offset)
    {
        if (distance != 0.0)
        {
            return std::atan2(offset, distance);
        }
        BCLIBC_ERROR("Division by zero in BCLIBC_getCorrection.");
        return 0.0;
    }

    /**
     * @brief Calculates the kinetic energy of the projectile.
     *
     * Uses the formula: $\text{Energy (ft-lbs)} = \frac{\text{Weight (grains)} \cdot \text{Velocity (fps)}^2}{450400}$.
     *
     * @param bulletWeight Bullet weight in grains.
     * @param velocity Projectile velocity in feet per second (fps).
     * @return Kinetic energy in foot-pounds (ft-lbs).
     */
    double BCLIBC_calculateEnergy(double bulletWeight, double velocity)
    {
        return bulletWeight * velocity * velocity / 450400.0;
    }

    /**
     * @brief Calculates the Optimum Game Weight (OGW) factor.
     *
     * OGW is a metric that attempts to combine kinetic energy and momentum into a single number.
     * Formula used: $\text{OGW} = \text{Weight (grains)}^2 \cdot \text{Velocity (fps)}^3 \cdot 1.5\text{e-}12$.
     *
     * @param bulletWeight Bullet weight in grains.
     * @param velocity Projectile velocity in feet per second (fps).
     * @return The Optimum Game Weight (OGW) factor.
     */
    double BCLIBC_calculateOgw(double bulletWeight, double velocity)
    {
        return bulletWeight * bulletWeight * velocity * velocity * velocity * 1.5e-12;
    }

    BCLIBC_Coriolis::BCLIBC_Coriolis(
        double sin_lat,
        double cos_lat,
        double sin_az,
        double cos_az,
        double range_east,
        double range_north,
        double cross_east,
        double cross_north,
        int flat_fire_only,
        double muzzle_velocity_fps)
        : sin_lat(sin_lat),
          cos_lat(cos_lat),
          sin_az(sin_az),
          cos_az(cos_az),
          range_east(range_east),
          range_north(range_north),
          cross_east(cross_east),
          cross_north(cross_north),
          flat_fire_only(flat_fire_only),
          muzzle_velocity_fps(muzzle_velocity_fps) {};

    void BCLIBC_Coriolis::flat_fire_offsets(
        double time,
        double distance_ft,
        double drop_ft,
        double &delta_y,
        double &delta_z) const
    {
        if (!this->flat_fire_only)
        {
            delta_y = 0.0;
            delta_z = 0.0;
            return;
        }

        double horizontal = BCLIBC_cEarthAngularVelocityRadS * distance_ft * this->sin_lat * time;
        double vertical = 0.0;
        if (this->sin_az)
        {
            double vertical_factor = -2.0 * BCLIBC_cEarthAngularVelocityRadS * this->muzzle_velocity_fps * this->cos_lat * this->sin_az;
            vertical = drop_ft * (vertical_factor / BCLIBC_cGravityImperial);
        }
        delta_y = vertical;
        delta_z = horizontal;
    };

    BCLIBC_V3dT BCLIBC_Coriolis::adjust_range(
        double time, const BCLIBC_V3dT &range_vector) const
    {
        if (!this || !this->flat_fire_only)
        {
            return range_vector;
        }
        double delta_y, delta_z;
        this->flat_fire_offsets(time, range_vector.x, range_vector.y, delta_y, delta_z);
        if (delta_y == 0.0 && delta_z == 0.0)
        {
            return range_vector;
        }
        return BCLIBC_V3dT{range_vector.x, range_vector.y + delta_y, range_vector.z + delta_z};
    }

    /**
     * @brief Calculate Coriolis acceleration in local coordinates (range, up, crossrange).
     *
     * Transforms the projectile's ground velocity (local coordinates) to the
     * Earth-North-Up (ENU) coordinate system, calculates the Coriolis acceleration
     * in ENU, and then transforms the acceleration back to local coordinates.
     *
     * Coriolis acceleration formula in ENU:
     * - $\mathbf{a}_{\text{coriolis}} = -2 \cdot \mathbf{\omega}_{\text{earth}} \times \mathbf{v}_{\text{ENU}}$
     *
     * @param velocity_ptr Pointer to the projectile's ground velocity vector (local coordinates: x=range, y=up, z=crossrange).
     * @param accel_ptr Pointer to store the calculated Coriolis acceleration vector (local coordinates).
     */
    void BCLIBC_Coriolis::coriolis_acceleration_local(
        const BCLIBC_V3dT &velocity,
        BCLIBC_V3dT &accel_out) const
    {
        // Early exit for most common case (flat fire: Coriolis effect is ignored/zeroed)
        if (this->flat_fire_only)
        {
            accel_out = BCLIBC_V3dT{0.0, 0.0, 0.0};
            return;
        }

        // Cache frequently used values
        const double vx = velocity.x;
        const double vy = velocity.y;
        const double vz = velocity.z;

        const double range_east = this->range_east;
        const double range_north = this->range_north;
        const double cross_east = this->cross_east;
        const double cross_north = this->cross_north;

        // Transform velocity to ENU (East, North, Up)
        const double vel_east = vx * range_east + vz * cross_east;
        const double vel_north = vx * range_north + vz * cross_north;
        const double vel_up = vy;

        // Coriolis acceleration in ENU
        const double factor = -2.0 * BCLIBC_cEarthAngularVelocityRadS;
        const double sin_lat = this->sin_lat;
        const double cos_lat = this->cos_lat;

        // $\mathbf{a}_{\text{coriolis}} = -2 \cdot \mathbf{\omega}_{\text{earth}} \times \mathbf{v}_{\text{ENU}}$
        // $\mathbf{\omega}_{\text{earth}} = \omega_e \cdot (0, \cos(\text{lat}), \sin(\text{lat}))$
        const double accel_east = factor * (cos_lat * vel_up - sin_lat * vel_north);
        const double accel_north = factor * sin_lat * vel_east;
        const double accel_up = factor * (-cos_lat * vel_east);

        // Transform back to local coordinates (x=range, y=up, z=crossrange)
        accel_out.x = accel_east * range_east + accel_north * range_north;
        accel_out.y = accel_up;
        accel_out.z = accel_east * cross_east + accel_north * cross_north;
    }

}; // namespace bclibc