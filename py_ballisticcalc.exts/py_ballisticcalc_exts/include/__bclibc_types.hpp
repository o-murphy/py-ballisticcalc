#ifndef BCLIBC_TYPES_HPP
#define BCLIBC_TYPES_HPP

#include "bclibc_bclib.h"

namespace bclibc
{
    struct Atmosphere : BCLIBC_Atmosphere
    {
    public:
        void update_density_factor_and_mach_for_altitude(
            double altitude,
            double *density_ratio_ptr,
            double *mach_ptr) const
        {
            BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
                this, altitude, density_ratio_ptr, mach_ptr);
        }
    };

    struct Wind : BCLIBC_Wind
    {
        Wind();
    };

    class WindSock : BCLIBC_WindSock
    {
    public:
        WindSock(size_t length, BCLIBC_Wind *winds)
        {
            BCLIBC_WindSock_init(this, length, winds);
        };
        ~WindSock()
        {
            BCLIBC_WindSock_release(this);
        };
        BCLIBC_V3dT current_vector() const
        {
            return BCLIBC_WindSock_currentVector(this);
        };
        BCLIBC_ErrorType update_cache()
        {
            return BCLIBC_WindSock_updateCache(this);
        };
        BCLIBC_V3dT vector_for_range(double next_range_param)
        {
            return BCLIBC_WindSock_vectorForRange(this, next_range_param);
        };
    };

    struct Coriolis : BCLIBC_Coriolis
    {
    public:
        BCLIBC_V3dT adjust_range_from_coriolis(double time, const BCLIBC_V3dT *range_vector) const
        {
            return BCLIBC_adjustRangeFromCoriolis(this, time, range_vector);
        };
        void coriolis_acceleration_local(const BCLIBC_V3dT *velocity_ptr, BCLIBC_V3dT *accel_ptr) const
        {
            return BCLIBC_Coriolis_coriolisAccelerationLocal(this, velocity_ptr, accel_ptr);
        };
        void flat_fire_offsets(double time, double distance_ft, double drop_ft, double *delta_y, double *delta_z) const
        {
            BCLIBC_Coriolis_flatFireOffsets(this, time, distance_ft, drop_ft, delta_y, delta_z);
        };
        BCLIBC_V3dT adjust_range(double time, const BCLIBC_V3dT *range_vector) const
        {
            return BCLIBC_Coriolis_adjustRange(this, time, range_vector);
        };
    };

    struct ShotProps : BCLIBC_ShotProps
    {
    public:
        ShotProps();
        ~ShotProps()
        {
            BCLIBC_ShotProps_release(this);
        };
        double spin_drift(double time) const
        {
            return BCLIBC_ShotProps_spinDrift(this, time);
        };
        BCLIBC_ErrorType update_stability_coefficient()
        {
            return BCLIBC_ShotProps_updateStabilityCoefficient(this);
        };
        double drag_by_mach(double mach) const
        {
            return BCLIBC_ShotProps_dragByMach(this, mach);
        };
    };
};

#endif // BCLIBC_TYPES_HPP