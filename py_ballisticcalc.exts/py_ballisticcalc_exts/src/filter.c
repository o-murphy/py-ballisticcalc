#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "bclib.h"

#define EPSILON 1e-6
#define SEPARATE_ROW_TIME_DELTA 1e-9

typedef struct {
    double time;
    double distanse_ft;
    double velocity_fps;
    double mach;
    double height_ft;
    double slant_height_ft;
    double drop_angle_rad;
    double windage_ft;
    double windage_angle_rad;
    double drag;
    double energy_ft_lb;
    double ogw_lb;
    BCLIBC_TrajFlag flag;

} TrajectoryDataRaw_t;

typedef struct
{
    BCLIBC_BaseTrajData data;
    BCLIBC_TrajFlag flag;
} TrajDataRecord_t;

typedef struct
{
    TrajDataRecord_t *records;
    size_t count;
    size_t capacity;
} TrajDataRecordList_t;

typedef struct
{
    TrajDataRecordList_t records;
    const ShotProps_t *props;
    BCLIBC_TrajFlag filter;
    BCLIBC_TrajFlag seen_zero;
    double time_of_last_record;
    double time_step;
    double range_step;
    double range_limit;
    BCLIBC_BaseTrajData prev_data;
    BCLIBC_BaseTrajData prev_prev_data;
    double next_record_distance;
    double look_angle_rad;
    double look_angle_tangent;
    bool has_prev_data;
    bool has_prev_prev_data;
} TrajectoryDataFilter_t;

static inline TrajectoryDataRaw_t TrajectoryDataRaw_t_from_props(
    const ShotProps_t *props,
    double time,
    BCLIBC_V3dT range_vector,
    BCLIBC_V3dT velocity_vector,
    double mach,
    BCLIBC_TrajFlag flag
) {

}

static inline TrajectoryDataRaw_t TrajectoryDataRaw_t_from_base_data(
    const ShotProps_t *props,
    const BCLIBC_BaseTrajData *data,
    BCLIBC_TrajFlag flag
) {
    return TrajectoryDataRaw_t_from_props(props, data->time, data->position, data->velocity, data->mach, flag);
}

// Швидке порівняння double з epsilon
static inline bool double_equals(double a, double b, double epsilon)
{
    return fabs(a - b) < epsilon;
}

// Ініціалізація динамічного списку записів
static void TrajDataRecordList_init(TrajDataRecordList_t *list)
{
    list->capacity = 64;
    list->count = 0;
    list->records = (TrajDataRecord_t *)malloc(list->capacity * sizeof(TrajDataRecord_t));
}

static void TrajDataRecordList_ensure_capacity(TrajDataRecordList_t *list, size_t needed)
{
    if (needed > list->capacity)
    {
        size_t new_capacity = list->capacity * 2;
        while (new_capacity < needed)
        {
            new_capacity *= 2;
        }
        list->records = (TrajDataRecord_t *)realloc(list->records, new_capacity * sizeof(TrajDataRecord_t));
        list->capacity = new_capacity;
    }
}

static void TrajDataRecordList_free(TrajDataRecordList_t *list)
{
    free(list->records);
    list->records = NULL;
    list->count = 0;
    list->capacity = 0;
}

// Бінарний пошук для вставки (повертає індекс для вставки)
static size_t binary_search_insert_position(const TrajDataRecord_t *records, size_t count, double time)
{
    if (count == 0)
        return 0;

    size_t left = 0;
    size_t right = count;

    while (left < right)
    {
        size_t mid = left + (right - left) / 2;
        if (records[mid].data.time < time)
        {
            left = mid + 1;
        }
        else
        {
            right = mid;
        }
    }

    return left;
}

// Вставка або злиття запису за часом
static void insert_or_merge_record(TrajDataRecordList_t *list, const BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag)
{
    double new_time = data->time;

    // Оптимізація: перевірка останнього елемента (найчастіший випадок)
    if (list->count > 0)
    {
        size_t last_idx = list->count - 1;
        double last_time = list->records[last_idx].data.time;

        if (double_equals(last_time, new_time, SEPARATE_ROW_TIME_DELTA))
        {
            list->records[last_idx].flag |= flag;
            return;
        }
    }

    size_t idx = binary_search_insert_position(list->records, list->count, new_time);

    // Перевірка сусідів на співпадіння часу
    if (idx < list->count && double_equals(list->records[idx].data.time, new_time, SEPARATE_ROW_TIME_DELTA))
    {
        list->records[idx].flag |= flag;
        return;
    }

    if (idx > 0 && double_equals(list->records[idx - 1].data.time, new_time, SEPARATE_ROW_TIME_DELTA))
    {
        list->records[idx - 1].flag |= flag;
        return;
    }

    // Вставка нового запису
    TrajDataRecordList_ensure_capacity(list, list->count + 1);

    // Зсув елементів вправо
    if (idx < list->count)
    {
        memmove(&list->records[idx + 1], &list->records[idx],
                (list->count - idx) * sizeof(TrajDataRecord_t));
    }

    list->records[idx].data = *data;
    list->records[idx].flag = flag;
    list->count++;
}

// Вставка або злиття TrajectoryData запису за часом
static void insert_or_merge_trajectory_record(
    TrajDataRecordList_t *list,
    const ShotProps_t *props,
    const BCLIBC_BaseTrajData *base_data,
    BCLIBC_TrajFlag flag)
{
    double new_time = base_data->time;

    // Оптимізація: перевірка останнього елемента
    if (list->count > 0)
    {
        size_t last_idx = list->count - 1;
        double last_time = list->records[last_idx].data.time;

        if (double_equals(last_time, new_time, SEPARATE_ROW_TIME_DELTA))
        {
            list->records[last_idx].flag |= flag;
            return;
        }
    }

    size_t idx = binary_search_insert_position(list->records, list->count, new_time);

    // Перевірка сусідів на співпадіння часу
    if (idx < list->count && double_equals(list->records[idx].data.time, new_time, SEPARATE_ROW_TIME_DELTA))
    {
        list->records[idx].flag |= flag;
        return;
    }

    if (idx > 0 && double_equals(list->records[idx - 1].data.time, new_time, SEPARATE_ROW_TIME_DELTA))
    {
        list->records[idx - 1].flag |= flag;
        return;
    }

    // Вставка нового запису
    TrajDataRecordList_ensure_capacity(list, list->count + 1);

    if (idx < list->count)
    {
        memmove(&list->records[idx + 1], &list->records[idx],
                (list->count - idx) * sizeof(TrajDataRecord_t));
    }

    list->records[idx].data = *base_data;
    list->records[idx].flag = flag;
    list->count++;
}

// Ініціалізація фільтру
void TrajectoryDataFilter_init(
    TrajectoryDataFilter_t *filter,
    const ShotProps_t *props,
    BCLIBC_TrajFlag filter_flags,
    const BCLIBC_V3dT *initial_position,
    const BCLIBC_V3dT *initial_velocity,
    double barrel_angle_rad,
    double look_angle_rad,
    double range_limit,
    double range_step,
    double time_step)
{
    TrajDataRecordList_init(&filter->records);
    filter->props = props;
    filter->filter = filter_flags;
    filter->seen_zero = BCLIBC_TRAJ_FLAG_NONE;
    filter->time_step = time_step;
    filter->range_step = range_step;
    filter->range_limit = range_limit;
    filter->time_of_last_record = 0.0;
    filter->next_record_distance = 0.0;
    filter->has_prev_data = false;
    filter->has_prev_prev_data = false;
    filter->look_angle_rad = look_angle_rad;
    filter->look_angle_tangent = tan(look_angle_rad);

    // MACH перевірка
    if (filter->filter & BCLIBC_TRAJ_FLAG_MACH)
    {
        double density_ratio, mach;
        Atmosphere_t_updateDensityFactorAndMachForAltitude(&props->atmo, initial_position->y, &density_ratio, &mach);
        double velocity_mag = BCLIBC_V3dT_mag(initial_velocity);
        if (velocity_mag < mach)
        {
            filter->filter &= ~BCLIBC_TRAJ_FLAG_MACH;
        }
    }

    // ZERO перевірка
    if (filter->filter & BCLIBC_TRAJ_FLAG_ZERO)
    {
        if (initial_position->y >= 0)
        {
            filter->filter &= ~BCLIBC_TRAJ_FLAG_ZERO_UP;
        }
        else if (initial_position->y < 0 && barrel_angle_rad <= look_angle_rad)
        {
            filter->filter &= ~(BCLIBC_TRAJ_FLAG_ZERO | BCLIBC_TRAJ_FLAG_MRT);
        }
    }
}

// Основна функція запису даних
void TrajectoryDataFilter_record(TrajectoryDataFilter_t *filter, const BCLIBC_BaseTrajData *new_data)
{
    TrajDataRecordList_t local_rows;
    TrajDataRecordList_init(&local_rows);

    // Кешування часто використовуваних значень
    double new_time = new_data->time;
    double pos_x = new_data->position.x;
    double pos_y = new_data->position.y;
    double velocity_mag = BCLIBC_V3dT_mag(&new_data->velocity);
    bool has_prev = filter->has_prev_data && filter->has_prev_prev_data;

    if (new_time == 0.0)
    {
        // Завжди записуємо початкову точку
        BCLIBC_TrajFlag flag = (filter->range_step > 0 || filter->time_step > 0) ? BCLIBC_TRAJ_FLAG_RANGE : BCLIBC_TRAJ_FLAG_NONE;
        insert_or_merge_record(&local_rows, new_data, flag);
    }
    else
    {
        // RANGE кроки
        if (filter->range_step > 0)
        {
            while (filter->next_record_distance + filter->range_step <= pos_x)
            {
                double record_distance = filter->next_record_distance + filter->range_step;

                if (record_distance > filter->range_limit + EPSILON)
                {
                    filter->range_step = -1;
                    break;
                }

                BCLIBC_BaseTrajData new_row;
                bool have_row = false;

                if (fabs(record_distance - pos_x) < EPSILON)
                {
                    new_row = *new_data;
                    have_row = true;
                }
                else if (has_prev)
                {
                    have_row = BCLIBC_BaseTrajData_interpolate(
                        KEY_POS_X, record_distance,
                        &filter->prev_prev_data, &filter->prev_data, new_data,
                        &new_row);
                }

                if (have_row)
                {
                    filter->next_record_distance += filter->range_step;
                    insert_or_merge_record(&local_rows, &new_row, BCLIBC_TRAJ_FLAG_RANGE);
                    filter->time_of_last_record = new_row.time;
                }
                else
                {
                    break;
                }
            }
        }

        // TIME кроки
        if (filter->time_step > 0 && has_prev)
        {
            while (filter->time_of_last_record + filter->time_step <= new_time)
            {
                filter->time_of_last_record += filter->time_step;
                BCLIBC_BaseTrajData new_row;
                if (BCLIBC_BaseTrajData_interpolate(
                        KEY_TIME, filter->time_of_last_record,
                        &filter->prev_prev_data, &filter->prev_data, new_data,
                        &new_row))
                {
                    insert_or_merge_record(&local_rows, &new_row, BCLIBC_TRAJ_FLAG_RANGE);
                }
            }
        }

        // APEX перевірка
        if ((filter->filter & BCLIBC_TRAJ_FLAG_APEX) && has_prev &&
            filter->prev_data.velocity.y > 0 && new_data->velocity.y <= 0)
        {
            BCLIBC_BaseTrajData new_row;
            if (BCLIBC_BaseTrajData_interpolate(
                    KEY_VEL_Y, 0.0,
                    &filter->prev_prev_data, &filter->prev_data, new_data,
                    &new_row))
            {
                insert_or_merge_record(&local_rows, &new_row, BCLIBC_TRAJ_FLAG_APEX);
                filter->filter &= ~BCLIBC_TRAJ_FLAG_APEX;
            }
        }
    }

    // Додавання локальних записів до основного списку
    for (size_t i = 0; i < local_rows.count; i++)
    {
        insert_or_merge_record(&filter->records, &local_rows.records[i].data, local_rows.records[i].flag);
    }
    TrajDataRecordList_free(&local_rows);

    // Перевірки що потребують TrajectoryData (MACH, ZERO)
    if (has_prev)
    {
        BCLIBC_TrajFlag compute_flags = BCLIBC_TRAJ_FLAG_NONE;

        // MACH перевірка
        double density_ratio, mach;
        Atmosphere_t_updateDensityFactorAndMachForAltitude(&filter->props->atmo, new_data->position.y, &density_ratio, &mach);
        if ((filter->filter & BCLIBC_TRAJ_FLAG_MACH) && velocity_mag < mach)
        {
            compute_flags |= BCLIBC_TRAJ_FLAG_MACH;
            filter->filter &= ~BCLIBC_TRAJ_FLAG_MACH;
        }

        // ZERO перевірки
        if (filter->filter & BCLIBC_TRAJ_FLAG_ZERO)
        {
            double reference_height = pos_x * filter->look_angle_tangent;

            if (filter->filter & BCLIBC_TRAJ_FLAG_ZERO_UP)
            {
                if (pos_y >= reference_height)
                {
                    compute_flags |= BCLIBC_TRAJ_FLAG_ZERO_UP;
                    filter->filter &= ~BCLIBC_TRAJ_FLAG_ZERO_UP;
                }
            }
            else if (filter->filter & BCLIBC_TRAJ_FLAG_ZERO_DOWN)
            {
                if (pos_y < reference_height)
                {
                    compute_flags |= BCLIBC_TRAJ_FLAG_ZERO_DOWN;
                    filter->filter &= ~BCLIBC_TRAJ_FLAG_ZERO_DOWN;
                }
            }
        }

        // Інтерполяція для MACH і ZERO (якщо є compute_flags)
        if (compute_flags != BCLIBC_TRAJ_FLAG_NONE)
        {
            // Створюємо TrajectoryData для інтерполяції
            TrajectoryDataRaw_t t0, t1, t2;
            TrajectoryDataRaw_t_fromBaseTrajData(&t0, filter->props, new_data);
            TrajectoryDataRaw_t_fromBaseTrajData(&t1, filter->props, &filter->prev_data);
            TrajectoryDataRaw_t_fromBaseTrajData(&t2, filter->props, &filter->prev_prev_data);

            // MACH інтерполяція
            if (compute_flags & BCLIBC_TRAJ_FLAG_MACH)
            {
                TrajectoryDataRaw_t mach_data;
                if (TrajectoryDataRaw_t_interpolate(KEY_MACH, 1.0, &t2, &t1, &t0, &mach_data))
                {
                    insert_or_merge_trajectory_record(&filter->records, filter->props, &mach_data, BCLIBC_TRAJ_FLAG_MACH);
                }
            }

            // ZERO інтерполяція
            if (compute_flags & BCLIBC_TRAJ_FLAG_ZERO)
            {
                BCLIBC_TrajFlag zero_flag = compute_flags & BCLIBC_TRAJ_FLAG_ZERO;
                TrajectoryDataRaw_t zero_data;
                if (TrajectoryDataRaw_t_interpolate(KEY_SLANT_HEIGHT, 0.0, &t2, &t1, &t0, &zero_data))
                {
                    insert_or_merge_trajectory_record(&filter->records, filter->props, &zero_data, zero_flag);
                }
            }
        }
    }

    // Оновлення попередніх даних
    filter->prev_prev_data = filter->prev_data;
    filter->prev_data = *new_data;
    filter->has_prev_prev_data = filter->has_prev_data;
    filter->has_prev_data = true;
}

// Очищення
void TrajectoryDataFilter_free(TrajectoryDataFilter_t *filter)
{
    TrajDataRecordList_free(&filter->records);
}

// Доступ до записів
const TrajDataRecord_t *TrajectoryDataFilter_getRecords(const TrajectoryDataFilter_t *filter, size_t *count)
{
    if (count)
    {
        *count = filter->records.count;
    }
    return filter->records.records;
}