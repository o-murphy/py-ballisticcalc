#include "bclibc_ffi_ext.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fail(BCLIBCFFI_Error *err, int32_t code, const char *message, double a, double b, double c)
{
    if (err == NULL)
        return;
    memset(err, 0, sizeof(*err));
    err->code = code;
    snprintf(err->message, sizeof(err->message), "%s", message);
    err->f64_0 = a;
    err->f64_1 = b;
    err->f64_2 = c;
}

static double field(const BCLIBCFFI_BaseTrajData *p, int32_t key)
{
    switch (key)
    {
    case BCLIBCFFI_INTERP_KEY_TIME: return p->time;
    case BCLIBCFFI_INTERP_KEY_MACH: return p->mach;
    case BCLIBCFFI_INTERP_KEY_POS_X: return p->px;
    case BCLIBCFFI_INTERP_KEY_POS_Y: return p->py;
    case BCLIBCFFI_INTERP_KEY_POS_Z: return p->pz;
    case BCLIBCFFI_INTERP_KEY_VEL_X: return p->vx;
    case BCLIBCFFI_INTERP_KEY_VEL_Y: return p->vy;
    case BCLIBCFFI_INTERP_KEY_VEL_Z: return p->vz;
    default: return 0.0;
    }
}

void BCLIBCFFI_base_traj_buf_free(BCLIBCFFI_BaseTrajBuf *buf)
{
    free(buf->data);
    buf->data = NULL;
    buf->count = 0;
    buf->capacity = 0;
}

int32_t BCLIBCFFI_base_traj_buf_append(BCLIBCFFI_BaseTrajBuf *buf, const BCLIBCFFI_BaseTrajData *item, BCLIBCFFI_Error *err)
{
    if (buf->count == buf->capacity)
    {
        const int32_t capacity = buf->capacity == 0 ? 64 : buf->capacity * 2;
        BCLIBCFFI_BaseTrajData *grown = (BCLIBCFFI_BaseTrajData *)realloc(buf->data, (size_t)capacity * sizeof(*grown));
        if (capacity <= buf->capacity || grown == NULL)
        {
            fail(err, BCLIBCFFI_ERR_GENERIC, "Cannot grow the trajectory buffer: out of memory", 0, 0, 0);
            return BCLIBCFFI_ERR_GENERIC;
        }
        buf->data = grown;
        buf->capacity = capacity;
    }
    buf->data[buf->count++] = *item;
    return BCLIBCFFI_OK;
}

int32_t BCLIBCFFI_base_traj_interpolate(
    int32_t key, double value,
    const BCLIBCFFI_BaseTrajData *p0, const BCLIBCFFI_BaseTrajData *p1, const BCLIBCFFI_BaseTrajData *p2,
    BCLIBCFFI_BaseTrajData *out, BCLIBCFFI_Error *err)
{
    const double x0 = field(p0, key), x1 = field(p1, key), x2 = field(p2, key);
    if (x0 == x1 || x0 == x2 || x1 == x2)
    {
        fail(err, BCLIBCFFI_ERR_GENERIC, "Degenerate interpolation segment: duplicate key values", x0, x1, 0);
        return BCLIBCFFI_ERR_GENERIC;
    }
    out->time = key == BCLIBCFFI_INTERP_KEY_TIME ? value : BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->time, p1->time, p2->time);
    out->px = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->px, p1->px, p2->px);
    out->py = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->py, p1->py, p2->py);
    out->pz = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->pz, p1->pz, p2->pz);
    out->vx = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->vx, p1->vx, p2->vx);
    out->vy = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->vy, p1->vy, p2->vy);
    out->vz = BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->vz, p1->vz, p2->vz);
    out->mach = key == BCLIBCFFI_INTERP_KEY_MACH ? value : BCLIBCFFI_interpolate_3pt(value, x0, x1, x2, p0->mach, p1->mach, p2->mach);
    return BCLIBCFFI_OK;
}

int32_t BCLIBCFFI_base_traj_interpolate_at(
    const BCLIBCFFI_BaseTrajData *steps, int32_t count, int64_t idx, int32_t key, double value,
    BCLIBCFFI_BaseTrajData *out, BCLIBCFFI_Error *err)
{
    if (idx < 0)
        idx += count;
    if (idx < 1 || idx >= (int64_t)count - 1)
    {
        fail(err, BCLIBCFFI_ERR_OUT_OF_RANGE, "Index outside valid interpolation range [1, n-2]", (double)idx, 1.0, (double)count - 2.0);
        return BCLIBCFFI_ERR_OUT_OF_RANGE;
    }
    return BCLIBCFFI_base_traj_interpolate(key, value, &steps[idx - 1], &steps[idx], &steps[idx + 1], out, err);
}
