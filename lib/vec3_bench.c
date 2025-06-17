// vec3_bench.c (Your main benchmark file)

#include <stdio.h>
#include <math.h>   // For sqrt and fabs (double precision)
#include <time.h>   // For clock_gettime and struct timespec
#include "v3d.h"    // Include your custom header
// Define a large number of iterations for benchmarking
#define NUM_ITERATIONS 1000000 // 1 million iterations, adjust as needed

// A common way to create an optimization barrier in GCC/Clang
// This tells the compiler that memory could have changed and it can't reorder operations across this point.
#define COMPILER_FENCE() asm volatile("" ::: "memory")

// Helper to calculate time difference in seconds
double diff_timespec(struct timespec start, struct timespec end) {
    return (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
}

int main() {
    printf("--- Running C Vector Benchmarks (Double Precision) ---\n");
    printf("Number of iterations: %d\n\n", NUM_ITERATIONS);

    struct timespec start_time, end_time;
    double elapsed_time;
    long long i; // Use long long for loop counter for very large NUM_ITERATIONS

    // Declare input vectors as volatile to prevent compiler from optimizing away their usage
    // Initialize with double literals (default for numbers with decimal points in C)
    volatile V3d vA_vol = {1.0, 2.0, 3.0};
    volatile V3d vB_vol = {4.0, 5.0, 6.0};
    volatile V3d vF_initial_vol = {1.0, 1.0, 0.0};

    // Use dummy sum variables which are ALSO volatile to ensure their writes are not optimized away.
    // We'll increment these in each loop.
    volatile double dummy_sum_x = 0.0;
    volatile double dummy_sum_val = 0.0;


    // Benchmark set
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        // Use volatile inputs for set to ensure the function call isn't skipped
        // and assign to a volatile variable to ensure the result is 'used'.
        volatile V3d temp_result = set(vA_vol.x, vA_vol.y, vA_vol.z);
        dummy_sum_x += temp_result.x; // Make sure result is touched in an 'observable' way
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("set       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark add
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile V3d temp_result = add(vA_vol, vB_vol);
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("add       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark sub
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile V3d temp_result = sub(vA_vol, vB_vol);
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("sub       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark mulS
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile V3d temp_result = mulS(vA_vol, 2.5); // Use double literal
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("mulS      : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark dot
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile double temp_val = dot(vA_vol, vB_vol);
        dummy_sum_val += temp_val;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("dot       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark mag
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile double temp_val = mag(vA_vol);
        dummy_sum_val += temp_val;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("mag       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark norm (needs to copy from initial volatile state each iteration)
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        // Copy from the volatile initial state to a non-volatile temp for modification
        // This ensures the initial state is always read anew.
        V3d temp_vF_copy = vF_initial_vol;
        norm(&temp_vF_copy);
        // Then interact with the modified result in a volatile way
        dummy_sum_x += temp_vF_copy.x; // Access a component to force computation
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("norm      : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // A final dummy read of the volatile sums to prevent their own elimination.
    // The compiler can't assume these values are unused if they are volatile.
    // Adding them to a volatile dummy variable ensures they are truly read.
    volatile double final_check_sum = dummy_sum_x + dummy_sum_val;
    // Optionally print it to confirm it's not optimized out completely
    // printf("Final dummy sum check: %f\n", final_check_sum);


    printf("\n--- Benchmark Complete ---\n");

    return 0;
}