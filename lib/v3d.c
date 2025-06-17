#include <stdio.h>
#include <math.h>

typedef struct {
    double x;
    double y;
    double z;
} V3d; // Simplified type name

// Function Prototypes
V3d set(double x, double y, double z);
V3d add(V3d v1, V3d v2);
V3d sub(V3d v1, V3d v2);
V3d mulS(V3d v, double scalar);
double dot(V3d v1, V3d v2);
double mag(V3d v);
void norm(V3d *v); // Takes a pointer, modifies in place
void print_vec(const char* name, V3d v);

// Function Implementations
V3d set(double x, double y, double z) {
    V3d v = {x, y, z};
    return v;
}

V3d add(V3d v1, V3d v2) {
    V3d result;
    result.x = v1.x + v2.x;
    result.y = v1.y + v2.y;
    result.z = v1.z + v2.z;
    return result;
}

V3d sub(V3d v1, V3d v2) {
    V3d result;
    result.x = v1.x - v2.x;
    result.y = v1.y - v2.y;
    result.z = v1.z - v2.z;
    return result;
}

V3d mulS(V3d v, double scalar) {
    V3d result;
    result.x = v.x * scalar;
    result.y = v.y * scalar;
    result.z = v.z * scalar;
    return result;
}

double dot(V3d v1, V3d v2) {
    return (v1.x * v2.x) + (v1.y * v2.y) + (v1.z * v2.z);
}

double mag(V3d v) {
    return sqrtf((v.x * v.x) + (v.y * v.y) + (v.z * v.z));
}

void norm(V3d *v) {
    double m = mag(*v);
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

void print_vec(const char* name, V3d v) {
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v.x, v.y, v.z);
}

// // Main function for demonstration
// int main() {
//     printf("--- 3D Vector Operations ---\n\n");

//     V3d a = set(1.0f, 2.0f, 3.0f);
//     V3d b = set(4.0f, -1.0f, 2.0f);
//     V3d c = set(0.0f, 0.0f, 0.0f);

//     print_vec("a", a);
//     print_vec("b", b);
//     print_vec("c", c);
//     printf("\n");

//     V3d sum = add(a, b);
//     print_vec("a + b", sum);
//     printf("\n");

//     V3d diff = sub(a, b);
//     print_vec("a - b", diff);
//     printf("\n");

//     double s = 2.5f;
//     V3d scaled_a = mulS(a, s);
//     printf("Scalar: %.2f\n", s);
//     print_vec("a * scalar", scaled_a);
//     printf("\n");

//     double d = dot(a, b);
//     printf("Dot product (a . b): %.2f\n", d);
//     printf("\n");

//     double m = mag(a);
//     printf("Magnitude of a: %.2f\n", m);
//     printf("\n");

//     V3d norm_a = a; // Make a copy if you want to keep 'a' unchanged
//     norm(&norm_a); // Normalize 'norm_a' in place
//     print_vec("Normalized a", norm_a);
//     printf("Magnitude of Normalized a: %.2f\n", mag(norm_a));

//     printf("\n");
//     norm(&c); // Normalize zero vector 'c' in place
//     print_vec("Normalized c (zero)", c);
//     printf("Magnitude of Normalized c: %.2f\n", mag(c));

//     return 0;
// }

