#include <stdio.h>
#include <math.h>

typedef struct {
    float x;
    float y;
    float z;
} Vec3; // Simplified type name

// Function Prototypes
Vec3 set(float x, float y, float z);
Vec3 add(Vec3 v1, Vec3 v2);
Vec3 sub(Vec3 v1, Vec3 v2);
Vec3 mulS(Vec3 v, float scalar);
float dot(Vec3 v1, Vec3 v2);
float mag(Vec3 v);
void norm(Vec3 *v); // Takes a pointer, modifies in place
void print_vec(const char* name, Vec3 v);

// Function Implementations
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
    if (m == 0.0f) {
        printf("Warning: Cannot normalize a zero vector.\n");
        v->x = 0.0f;
        v->y = 0.0f;
        v->z = 0.0f;
    } else {
        v->x /= m;
        v->y /= m;
        v->z /= m;
    }
}

void print_vec(const char* name, Vec3 v) {
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v.x, v.y, v.z);
}

// Main function for demonstration
int main() {
    printf("--- 3D Vector Operations ---\n\n");

    Vec3 a = set(1.0f, 2.0f, 3.0f);
    Vec3 b = set(4.0f, -1.0f, 2.0f);
    Vec3 c = set(0.0f, 0.0f, 0.0f);

    print_vec("a", a);
    print_vec("b", b);
    print_vec("c", c);
    printf("\n");

    Vec3 sum = add(a, b);
    print_vec("a + b", sum);
    printf("\n");

    Vec3 diff = sub(a, b);
    print_vec("a - b", diff);
    printf("\n");

    float s = 2.5f;
    Vec3 scaled_a = mulS(a, s);
    printf("Scalar: %.2f\n", s);
    print_vec("a * scalar", scaled_a);
    printf("\n");

    float d = dot(a, b);
    printf("Dot product (a . b): %.2f\n", d);
    printf("\n");

    float m = mag(a);
    printf("Magnitude of a: %.2f\n", m);
    printf("\n");

    Vec3 norm_a = a; // Make a copy if you want to keep 'a' unchanged
    norm(&norm_a); // Normalize 'norm_a' in place
    print_vec("Normalized a", norm_a);
    printf("Magnitude of Normalized a: %.2f\n", mag(norm_a));

    printf("\n");
    norm(&c); // Normalize zero vector 'c' in place
    print_vec("Normalized c (zero)", c);
    printf("Magnitude of Normalized c: %.2f\n", mag(c));

    return 0;
}

