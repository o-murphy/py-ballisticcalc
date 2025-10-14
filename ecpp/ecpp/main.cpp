#include "v3d.hpp"
#include <iostream>

using namespace std;

int main() {
    // Vector creation (Immutable)
    V3d a(1.0, 2.0, 3.0);
    V3d b(4.0, -1.0, 0.5);
    V3d zero; // (0, 0, 0)

    cout << "A: " << a << endl;
    cout << "B: " << b << endl;
    cout << "Zero: " << zero << endl;
    
    // --- Arithmetic Operations (Immutable) ---

    // Addition (a + b, uses V3d::operator+)
    V3d c = a + b;
    cout << "\nC = A + B: " << c << endl; // (5.0, 1.0, 3.5)

    // Subtraction (a - b, uses V3d::operator-)
    V3d d = a - b;
    cout << "D = A - B: " << d << endl; // (-3.0, 3.0, 2.5)

    // Negation (-a, uses V3d::operator-())
    V3d e = -a;
    cout << "E = -A: " << e << endl; // (-1.0, -2.0, -3.0)

    // V * S (a * 2.5, uses V3d::operator*)
    V3d f = a * 2.5;
    cout << "F = A * 2.5: " << f << endl; // (2.5, 5.0, 7.5)
    
    // S * V (3.0 * b, uses free operator*)
    V3d f_rev = 3.0 * b;
    cout << "F_rev = 3.0 * B: " << f_rev << endl; // (12.0, -3.0, 1.5)

    // --- Vector Algebra ---

    // Dot product (a.dot(b))
    double dot_prod = a.dot(b);
    cout << "\nDot(A, B): " << dot_prod << endl; // 1*4 + 2*(-1) + 3*0.5 = 3.5

    // Magnitude (a.mag())
    double magnitude = a.mag();
    cout << "Mag(A): " << magnitude << " (~3.74)" << endl; 

    // Normalization (a.norm(), immutable)
    V3d a_norm = a.norm();
    cout << "A_norm (A.norm()): " << a_norm << endl; 
    cout << "Mag(A_norm): " << a_norm.mag() << endl; // Should be ~1.0

    // Check immutability (A should be unchanged)
    cout << "A (unchanged): " << a << endl;

    return 0;
}