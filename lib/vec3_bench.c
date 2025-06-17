#include <stdio.h>
#include <math.h>
#include <time.h> // For clock_gettime and struct timespec

// Define a large number of iterations for benchmarking
#define NUM_ITERATIONS 1000000 // 100 million iterations, adjust as needed

// A common way to create an optimization barrier in GCC/Clang
// This tells the compiler that memory could have changed and it can't reorder operations across this point.
#define COMPILER_FENCE() asm volatile("" ::: "memory")

typedef struct {
    float x;
    float y;
    float z;
} Vec3;

// Function Prototypes (same as before)
Vec3 set(float x, float y, float z);
Vec3 add(Vec3 v1, Vec3 v2);
Vec3 sub(Vec3 v1, Vec3 v2);
Vec3 mulS(Vec3 v, float scalar);
float dot(Vec3 v1, Vec3 v2);
float mag(Vec3 v);
void norm(Vec3 *v);

// Function Implementations (same as before)
Vec3 set(float x, float y, float z) {
    Vec3 v = {x, y, z};
    return v;
}

Vec3 add(Vec3 v1, Vec3 v2) {
    Vec3 result;
    result.x = v1.x + v2.x;
    result.y = v1.y + v2.y;
    result.z = v1.z + v2.z;
    return result;
}

Vec3 sub(Vec3 v1, Vec3 v2) {
    Vec3 result;
    result.x = v1.x - v2.x;
    result.y = v1.y - v2.y;
    result.z = v1.z - v2.z;
    return result;
}

Vec3 mulS(Vec3 v, float scalar) {
    Vec3 result;
    result.x = v.x * scalar;
    result.y = v.y * scalar;
    result.z = v.z * scalar;
    return result;
}

float dot(Vec3 v1, Vec3 v2) {
    return (v1.x * v2.x) + (v1.y * v2.y) + (v1.z * v2.z);
}

float mag(Vec3 v) {
    return sqrtf((v.x * v.x) + (v.y * v.y) + (v.z * v.z));
}

void norm(Vec3 *v) {
    float m = mag(*v);
    if (fabsf(m) < 1e-10f) {
        v->x = 0.0f;
        v->y = 0.0f;
        v->z = 0.0f;
    } else {
        v->x /= m;
        v->y /= m;
        v->z /= m;
    }
}

// Helper to calculate time difference in seconds
double diff_timespec(struct timespec start, struct timespec end) {
    return (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
}

int main() {
    printf("--- Running C Vector Benchmarks ---\n");
    printf("Number of iterations: %d\n\n", NUM_ITERATIONS);

    struct timespec start_time, end_time;
    double elapsed_time;
    long long i; // Use long long for loop counter for very large NUM_ITERATIONS

    // Declare input vectors as volatile to prevent compiler from optimizing away their usage
    volatile Vec3 vA_vol = {1.0f, 2.0f, 3.0f};
    volatile Vec3 vB_vol = {4.0f, 5.0f, 6.0f};
    volatile Vec3 vF_initial_vol = {1.0f, 1.0f, 0.0f};

    // Use dummy sum variables which are ALSO volatile to ensure their writes are not optimized away.
    // We'll increment these in each loop.
    volatile double dummy_sum_x = 0.0;
    volatile double dummy_sum_val = 0.0;


    // Benchmark set
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        // Use volatile inputs for set to ensure the function call isn't skipped
        // and assign to a volatile variable to ensure the result is 'used'.
        volatile Vec3 temp_result = set(vA_vol.x, vA_vol.y, vA_vol.z);
        dummy_sum_x += temp_result.x; // Make sure result is touched in an 'observable' way
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("set       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark add
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile Vec3 temp_result = add(vA_vol, vB_vol);
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("add       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark sub
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile Vec3 temp_result = sub(vA_vol, vB_vol);
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("sub       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark mulS
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile Vec3 temp_result = mulS(vA_vol, 2.5f);
        dummy_sum_x += temp_result.x;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("mulS      : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark dot
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile float temp_val = dot(vA_vol, vB_vol);
        dummy_sum_val += temp_val;
    }
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    elapsed_time = diff_timespec(start_time, end_time);
    printf("dot       : %.6f seconds for %d runs (%.3f ns per operation)\n",
           elapsed_time, NUM_ITERATIONS, (elapsed_time / NUM_ITERATIONS) * 1e9);

    // Benchmark mag
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < NUM_ITERATIONS; ++i) {
        volatile float temp_val = mag(vA_vol);
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
        Vec3 temp_vF_copy = vF_initial_vol;
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
    // You can even print it, but just touching a volatile variable is often enough.
    // printf("Final dummy sum check: %f\n", final_check_sum);


    printf("\n--- Benchmark Complete ---\n");

    return 0;
}