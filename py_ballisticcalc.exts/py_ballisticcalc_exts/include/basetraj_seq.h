#ifndef BASETRAJ_SEQ_H
#define BASETRAJ_SEQ_H

#include <stddef.h>


/**
 * Simple C struct for trajectory data points used in the contiguous buffer.
 */
typedef struct {
    double time;  /* Time of the data point */
    double px;    /* Position x-coordinate */
    double py;    /* Position y-coordinate */
    double pz;    /* Position z-coordinate */
    double vx;    /* Velocity x-component */
    double vy;    /* Velocity y-component */
    double vz;    /* Velocity z-component */
    double mach;  /* Mach number */
} BaseTrajC;

/**
 * Keys used to look up specific values within a BaseTrajC struct.
 */
typedef enum {
    KEY_TIME,
    KEY_MACH,
    KEY_POS_X,
    KEY_POS_Y,
    KEY_POS_Z,
    KEY_VEL_X,
    KEY_VEL_Y,
    KEY_VEL_Z
} InterpKey;

/**
 * Internal view structure for a sequence (buffer) of BaseTrajC points.
 */
typedef struct {
    BaseTrajC* _buffer;
    size_t _length;
    size_t _capacity;
} _CBaseTrajSeq_cview;

/**
 * Retrieves a specific double value from a BaseTrajC struct using an InterpKey.
 * This function is defined as static inline for performance.
 *
 * @param p A pointer to the BaseTrajC struct.
 * @param key_kind The InterpKey indicating which value to retrieve.
 * @return The corresponding double value, or 0.0 if the key is unrecognized.
 */
static inline double _key_val_from_kind_buf(const BaseTrajC* p, int key_kind) {
    // Note: In C, accessing a struct member via a pointer uses '->' instead of '.'
    switch (key_kind) {
        case KEY_TIME:
            return p->time;
        case KEY_MACH:
            return p->mach;
        case KEY_POS_X:
            return p->px;
        case KEY_POS_Y:
            return p->py;
        case KEY_POS_Z:
            return p->pz;
        case KEY_VEL_X:
            return p->vx;
        case KEY_VEL_Y:
            return p->vy;
        case KEY_VEL_Z:
            return p->vz;
        default:
            return 0.0;
    }
}

#endif /* BASETRAJ_SEQ_H */
