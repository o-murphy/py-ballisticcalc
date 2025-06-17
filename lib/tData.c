#include "tData.h"
#include <stdio.h>

#define INITIAL_TRAJECTORY_CAPACITY 10

int initTrajectoryTable(TrajectoryTableT *table) {
    if (table == NULL) {
        return -1; // Error: NULL table pointer
    }
    table->ranges = NULL;   // Important: Initialize to NULL for first realloc call
    table->length = 0;
    table->capacity = 0; // Important: Initialize to 0 so the first add will trigger reallocation
    return 0;
}

// Helper to add a TrajectoryDataT to a dynamically growing array
// Returns 0 on success, -1 on reallocation failure
int addTrajectoryDataPoint(TrajectoryTableT *TrajectoryTableTable, TrajectoryDataT newData)
{
    // 1. Basic NULL check for the table pointer
    if (TrajectoryTableTable == NULL)
    {
        fprintf(stderr, "Error: TrajectoryTableTable is NULL in addTrajectoryDataPoint.\\n");
        return -1; // Indicate error
    }

    // 2. Check if reallocation is needed
    if (TrajectoryTableTable->length >= TrajectoryTableTable->capacity)
    {
        size_t new_capacity;
        // Determine new capacity: if current capacity is 0, set to initial, else double it
        if (TrajectoryTableTable->capacity == 0)
        {
            new_capacity = INITIAL_TRAJECTORY_CAPACITY;
        }
        else
        {
            new_capacity = TrajectoryTableTable->capacity * 2;
        }

        // Allocate or reallocate memory
        TrajectoryDataT *temp = (TrajectoryDataT *)realloc(TrajectoryTableTable->ranges, new_capacity * sizeof(TrajectoryDataT));

        if (temp == NULL)
        {
            fprintf(stderr, "Error: Failed to reallocate memory for TrajectoryTableT.ranges.\\n");
            // Optionally, try to free existing memory if realloc failed.
            // free(TrajectoryTableTable->ranges); // Only if you want to clear on failure
            // TrajectoryTableTable->ranges = NULL;
            return -1; // Indicate error
        }
        TrajectoryTableTable->ranges = temp;
        TrajectoryTableTable->capacity = new_capacity;
        // For debugging:
        // fprintf(stderr, "Reallocated TrajectoryTableT to new capacity: %zu\\n", TrajectoryTableTable->capacity);
    }

    // 3. Add the new data point
    TrajectoryTableTable->ranges[TrajectoryTableTable->length] = newData;
    TrajectoryTableTable->length++;

    // For debugging:
    // fprintf(stderr, "Added data point. Current length: %zu, Capacity: %zu\\n", TrajectoryTableTable->length, TrajectoryTableTable->capacity);

    return 0; // Indicate success
}

void freeTrajectoryTable(TrajectoryTableT *table)
{
    if (table == NULL)
    {
        return;
    }
    // Free table->ranges, which was allocated by realloc
    if (table->ranges != NULL)
    {
        free(table->ranges);
        table->ranges = NULL; // Set to NULL after freeing to prevent double-free
    }
    table->length = 0;   // Reset length
    table->capacity = 0; // Reset capacity
}