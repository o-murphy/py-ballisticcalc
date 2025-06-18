#include "tData.h"
#include "bc.h"
#include <stdio.h>

#define INITIAL_TRAJECTORY_CAPACITY 10

int initTrajectoryTable(TrajectoryTableT *table) {
    if (table == NULL) {
        return -1; // Error: NULL table pointer
    }
    table->ranges = NULL;   // Important: Initialize to NULL for first realloc call
    table->length = 0;
    table->capacity = 0; // Important: Initialize to 0 so the first add will trigger reallocation
    return 0; // SUCCESS
}

// Helper to add a TrajectoryDataT to a dynamically growing array
// Returns 0 on success, -1 on reallocation failure
int addTrajectoryDataPoint(TrajectoryTableT *table, TrajectoryDataT data) {
    if (table == NULL) {
        fprintf(stderr, "Error: addTrajectoryDataPoint received NULL table.\n");
        return ERROR_NULL_ENGINE; // або інший відповідний ERROR_ код
    }

    // If this is the first point, allocate initial memory
    if (table->ranges == NULL) {
        table->ranges = (TrajectoryDataT*)malloc(INITIAL_TRAJECTORY_CAPACITY * sizeof(TrajectoryDataT));
        if (table->ranges == NULL) {
            fprintf(stderr, "Error: Initial malloc for trajectory ranges failed.\n");
            return ERROR_MALLOC_FAILED;
        }
        table->capacity = INITIAL_TRAJECTORY_CAPACITY;
    } else if (table->length >= table->capacity) {
        // Reallocate if capacity is reached
        size_t new_capacity = table->capacity * 2; // Double the capacity - common strategy
        // Захист від переповнення (необов'язково, але добре для дуже великих об'ємів)
        if (new_capacity == 0) new_capacity = INITIAL_TRAJECTORY_CAPACITY; // Handle 0 capacity if it somehow happened
        if (new_capacity < table->capacity) { // Check for overflow if capacity doubled wraps around
             fprintf(stderr, "Error: New capacity calculation overflowed.\n");
             return ERROR_REALLOC_FAILED; // Or a specific overflow error
        }
        
        TrajectoryDataT *new_ranges = (TrajectoryDataT*)realloc(table->ranges, new_capacity * sizeof(TrajectoryDataT));
        if (new_ranges == NULL) {
            fprintf(stderr, "Error: Realloc for trajectory ranges failed.\n");
            // Важливо: old table->ranges is still valid here. Don't touch table->ranges yet.
            return ERROR_REALLOC_FAILED;
        }
        table->ranges = new_ranges; // Only assign if realloc succeeded
        table->capacity = new_capacity;
    }

    table->ranges[table->length] = data; // Copy the data
    table->length++;
    return SUCCESS;
}

void freeTrajectoryTable(TrajectoryTableT *table)
{
    if (table == NULL)
    {
        return;
    }
    // Free table->ranges, which was allocated by malloc/realloc
    if (table->ranges != NULL)
    {
        free(table->ranges);
        table->ranges = NULL; // Set to NULL after freeing to prevent double-free
    }
    // Додатково: скинути довжину та ємність для повної чистоти
    table->length = 0;
    table->capacity = 0;
}