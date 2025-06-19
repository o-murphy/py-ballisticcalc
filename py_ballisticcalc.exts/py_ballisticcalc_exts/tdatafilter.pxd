# pxd file for tdatafilter.h

# Include standard C library types
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
from py_ballisticcalc_exts.tflag cimport TFlag

# Declare the TFlag enum
cdef extern from "include/tdatafilter.h":
    # Declare the BaseTData struct
    struct BaseTData:
        double time
        V3dT position
        V3dT velocity
        double mach

    # Declare the TDataFilter struct
    struct TDataFilter:
        TFlag filter
        TFlag currentFlag
        TFlag seenZero
        double timeStep
        double rangeStep
        double timeOfLastRecord
        double nextRecordDistance
        double previousMach
        double previousTime
        V3dT previousPosition
        V3dT previousVelocity
        double previousVMach
        double lookAngle
        BaseTData *data  # Pointer to BaseTData

    # Declare the public functions
    # bool maps to bint in Cython
    bint TDataFilter_init(
        TDataFilter *tdf,
        TFlag filterFlags,
        double rangeStep,
        const V3dT *initialPosition,
        const V3dT *initialVelocity,
        double timeStep
    )

    bint TDataFilter_initWithDefaultTimeStep(
        TDataFilter *tdf,
        TFlag filterFlags,
        double rangeStep,
        const V3dT *initialPosition,
        const V3dT *initialVelocity
    )

    void TDataFilter_free(
        TDataFilter *tdf
    )

    void TDataFilter_setupSeenZero(
        TDataFilter *tdf,
        double height,
        double barrelElevation,
        double lookAngle
    )

    bool TDataFilter_shouldRecord(
        TDataFilter *tdf,
        const V3dT *position,
        const V3dT *velocity,
        double mach,
        double time
    )