#include "v3d.h"
#include "tflag.h"
#include "tdatafilter.h"
#include <stdio.h>   // Для fprintf
#include <stdlib.h>  // Для malloc, free
#include <stdbool.h> // Для використання типу bool
#include <string.h>  // Для memset (для обнулення структури)
#include <math.h>    // Для tan, можливо, для mag, якщо вона не в v3d.h
// #include <assert.h> // Розкоментувати для використання assert у "for prod" режимі

// Оголошення статичних функцій, оскільки вони використовуються лише в цьому файлі.
static void TDataFilter_checkNextTime(TDataFilter *tdf, double time);
static void TDataFilter_checkMachCrossing(TDataFilter *tdf, double velocity_magnitude, double mach);
static void TDataFilter_checkZeroCrossing(TDataFilter *tdf, const V3dT *range_vector);

// TDataFilter_init: Встановлює tdf->data = NULL
bool TDataFilter_init(
    TDataFilter *tdf,
    enum TFlag filterFlags,
    double rangeStep,
    const V3dT *initialPosition,
    const V3dT *initialVelocity,
    double timeStep
) {
    tdf->filter = filterFlags;
    tdf->currentFlag = TRAJ_NONE;
    tdf->seenZero = TRAJ_NONE;
    tdf->timeStep = timeStep;
    tdf->rangeStep = rangeStep;
    tdf->timeOfLastRecord = 0.0;
    tdf->nextRecordDistance = 0.0;
    tdf->previousMach = 0.0;
    tdf->previousTime = 0.0;
    tdf->previousPosition = *initialPosition;
    tdf->previousVelocity = *initialVelocity;
    tdf->previousVMach = 0.0;
    tdf->lookAngle = 0.0;

    // Виділення пам'яті для BaseTData під час ініціалізації
    tdf->data = (BaseTData *)malloc(sizeof(BaseTData));
    if (tdf->data == NULL) {
        // ОБРОБКА ПОМИЛКИ: Не вдалося виділити пам'ять.
        return false;
    }

    // Обнуляємо виділену пам'ять для BaseTData
    memset(tdf->data, 0, sizeof(BaseTData));
    return true; // Додано крапку з комою
}

// TDataFilter_initWithDefaultTimeStep: Делегує TDataFilter_init
bool TDataFilter_initWithDefaultTimeStep( // Змінено тип повернення на int
    TDataFilter *tdf,
    enum TFlag filterFlags,
    double rangeStep,
    const V3dT *initialPosition,
    const V3dT *initialVelocity
) {
    return TDataFilter_init(
        tdf,
        filterFlags,
        rangeStep,
        initialPosition,
        initialVelocity,
        0.0
    );
}

// TDataFilter_free: Звільняє tdf->data, якщо воно не NULL
void TDataFilter_free(
    TDataFilter *tdf
) {
    if (tdf != NULL) {
        if (tdf->data != NULL) {
            free(tdf->data);
            tdf->data = NULL;
        }
    }
}

// TDataFilter_shouldRecord: Тепер повертає bool, сигналізуючи про необхідність запису
bool TDataFilter_shouldRecord(
    TDataFilter *tdf,
    const V3dT *position,
    const V3dT *velocity,
    double mach,
    double time
) {
    // for debug
    if (tdf == NULL) {
        fprintf(stderr, "ERROR: TDataFilter_shouldRecord received NULL tdf pointer.\n");
        return false;
    }
    if (tdf->data == NULL) {
        fprintf(stderr, "ERROR: TDataFilter_shouldRecord called with uninitialized tdf->data (NULL pointer).\n");
        return false;
    }

    //    // for prod
    //    assert(tdf != NULL && "TDataFilter_shouldRecord: tdf pointer is NULL");
    //    assert(tdf->data != NULL && "TDataFilter_shouldRecord: tdf->data pointer is NULL (not initialized)");

    // Змінні для інтерполяції
    double ratio;
    V3dT temp_position;
    V3dT temp_velocity;
    V3dT temp_sub_position;
    V3dT temp_mul_position;
    V3dT temp_sub_velocity;
    V3dT temp_mul_velocity;

    // Прапор, що вказує, чи був зроблений запис
    bool record_made = false;

    // Початково скидаємо прапор поточних подій
    tdf->currentFlag = TRAJ_NONE;

    // --- Логіка запису за ДІАПАЗОНОМ (RANGE) ---
    // Перевірка, чи active range_step > 0 і ми пройшли наступну дистанцію запису
    if ((tdf->rangeStep > 0) && (position->x >= tdf->nextRecordDistance)) {
        // Обробка випадку, коли ми пройшли більше ніж одну дистанцію запису
        while (tdf->nextRecordDistance + tdf->rangeStep < position->x) {
            tdf->nextRecordDistance += tdf->rangeStep;
        }

        // Перевірка, чи рух відбувається вперед по осі X
        if (position->x > tdf->previousPosition.x) {
            // Інтерполяція для отримання BaseTData на дистанції запису
            ratio = (tdf->nextRecordDistance - tdf->previousPosition.x) / (position->x - tdf->previousPosition.x);

            // Інтерполяція позиції
            temp_sub_position = sub(position, &tdf->previousPosition);
            temp_mul_position = mulS(&temp_sub_position, ratio);
            temp_position = add(&tdf->previousPosition, &temp_mul_position);

            // Інтерполяція швидкості
            temp_sub_velocity = sub(velocity, &tdf->previousVelocity);
            temp_mul_velocity = mulS(&temp_sub_velocity, ratio);
            temp_velocity = add(&tdf->previousVelocity, &temp_mul_velocity);

            // Оновлюємо tdf->data з інтерпольованими значеннями
            tdf->data->time = tdf->previousTime + (time - tdf->previousTime) * ratio;
            tdf->data->position = temp_position;
            tdf->data->velocity = temp_velocity;
            tdf->data->mach = tdf->previousMach + (mach - tdf->previousMach) * ratio;

            record_made = true; // Запис зроблено
        }
        tdf->currentFlag |= TRAJ_RANGE; // Встановлюємо прапор RANGE
        tdf->nextRecordDistance += tdf->rangeStep; // Оновлюємо наступну дистанцію запису
        tdf->timeOfLastRecord = time; // Оновлюємо час останнього запису
    }
    // --- Кінець логіки запису за ДІАПАЗОНОМ ---

    // --- Логіка запису за ЧАСОМ (TIME) ---
    // Якщо кроку діапазону немає, але є крок часу, перевіряємо його
    else if (tdf->timeStep > 0) {
        TDataFilter_checkNextTime(tdf, time);
    }
    // --- Кінець логіки запису за ЧАСОМ ---

    // --- Перевірки перетину нуля та Маха ---
    TDataFilter_checkZeroCrossing(tdf, position);
    TDataFilter_checkMachCrossing(tdf, mag(velocity), mach);
    // --- Кінець перевірок ---

    // Якщо спрацював будь-який з фільтрів (і, можливо, запис за діапазоном не був зроблений раніше)
    // і ми не зробили запис вже (наприклад, через Range)
    if ((tdf->currentFlag & tdf->filter) != 0 && !record_made) {
        // Якщо `tdf->filter` спрацював і запис ще не був зроблений іншим способом
        // Оновлюємо tdf->data поточними значеннями
        tdf->data->time = time;
        tdf->data->position = *position;
        tdf->data->velocity = *velocity;
        tdf->data->mach = mach;

        tdf->timeOfLastRecord = time; // Оновлюємо час останнього запису
        record_made = true; // Запис зроблено
    }

    // Оновлюємо "попередні" стани для наступних викликів
    tdf->previousTime = time;
    tdf->previousPosition = *position;
    tdf->previousVelocity = *velocity;
    tdf->previousMach = mach;

    // Повертаємо, чи був зроблений запис
    return record_made;
}

static void TDataFilter_checkNextTime(
    TDataFilter *tdf,
    double time
) {
    // Перевіряємо, чи пройшов заданий time_step з моменту останнього запису
    if (time > tdf->timeOfLastRecord + tdf->timeStep) {
        tdf->currentFlag |= TRAJ_RANGE; // Важливо: Cython-код використовує CTrajFlag.RANGE.
                                        // Якщо це дійсно має бути TRAJ_RANGE, то залишаємо.
                                        // Якщо ж це просто сигнал, що "час настав", і це не пов'язано з Range,
                                        // то потрібно переглянути прапор або створити новий (наприклад, TRAJ_TIME).
                                        // Виходячи з назви `_check_next_time`, це може бути окремий `TRAJ_TIME`
                                        // або ж TRAJ_RANGE використовується як загальний "запис за інтервалом".
                                        // Я залишаю TRAJ_RANGE, як у вашому Cython-коді.
        tdf->timeOfLastRecord = time;   // Оновлюємо час останнього запису
    }
}

static void TDataFilter_checkMachCrossing(
    TDataFilter *tdf,
    double velocity_magnitude,
    double mach
) {
    double current_v_mach;

    // Перевірка на ділення на нуль, якщо mach може бути 0.0
    if (mach == 0.0) {
        current_v_mach = 0.0;
    } else {
        current_v_mach = velocity_magnitude / mach;
    }

    // Перевірка перетину Mach 1.0 (зверху вниз або знизу вгору)
    // Cython: if tdf.previous_v_mach > 1 >= current_v_mach:
    // Це перевіряє перехід з надзвукової швидкості (>1) до дозвукової (<=1)
    if (tdf->previousVMach > 1.0 && current_v_mach <= 1.0) {
        tdf->currentFlag |= TRAJ_MACH; // Встановлюємо прапор Mach-перетину
    }

    if (tdf->previousVMach < 1.0 && current_v_mach >= 1.0) {
       tdf->currentFlag |= TRAJ_MACH;
    }

    // Оновлюємо попереднє значення для наступного виклику
    tdf->previousVMach = current_v_mach;
}

static void TDataFilter_checkZeroCrossing(
    TDataFilter *tdf,
    const V3dT *range_vector
) {
    if (range_vector->x > 0) {
        // Лінія відліку нуля - це лінія зору, визначена look_angle
        double reference_height = range_vector->x * tan(tdf->lookAngle);

        // Якщо ми ще не бачили ZERO_UP, шукаємо його
        if (!(tdf->seenZero & TRAJ_ZERO_UP)) {
            if (range_vector->y >= reference_height) {
                tdf->currentFlag |= TRAJ_ZERO_UP;
                tdf->seenZero |= TRAJ_ZERO_UP;
            }
        }
        // Ми перетнули лінію зору вгору; тепер шукаємо перетин вниз
        else if (!(tdf->seenZero & TRAJ_ZERO_DOWN)) {
            if (range_vector->y < reference_height) {
                tdf->currentFlag |= TRAJ_ZERO_DOWN;
                tdf->seenZero |= TRAJ_ZERO_DOWN;
            }
        }
    }
}