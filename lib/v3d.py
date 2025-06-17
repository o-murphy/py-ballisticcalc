import ctypes
import os

print(os.getcwd())

class Vec3(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
    ]

    def __repr__(self):
        return f"Vec3(x={self.x}, y={self.y}, z={self.z})"

if os.name == 'posix':
    if os.uname().sysname == 'Darwin':
        _library_extension = '.dylib'
    else:
        _library_extension = '.so'
elif os.name == 'nt':
    _library_extension = '.dll'
else:
    raise RuntimeError("Unsupported operating system")

_library_name = "./libv3d" + _library_extension
print(_library_name)
try:
    _v3d_lib = ctypes.CDLL(_library_name)
except OSError as e:
    print(f"Error loading library {_library_name}: {e}")
    print("Please ensure the C library is compiled and in the same directory as this script, or in your system's library path.")
    _v3d_lib = None

if _v3d_lib:
    _v3d_lib.set.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
    _v3d_lib.set.restype = Vec3
    def set(x: float, y: float, z: float) -> Vec3:
        return _v3d_lib.set(x, y, z)

    _v3d_lib.add.argtypes = [Vec3, Vec3]
    _v3d_lib.add.restype = Vec3
    def add(v1: Vec3, v2: Vec3) -> Vec3:
        return _v3d_lib.add(v1, v2)

    _v3d_lib.sub.argtypes = [Vec3, Vec3]
    _v3d_lib.sub.restype = Vec3
    def sub(v1: Vec3, v2: Vec3) -> Vec3:
        return _v3d_lib.sub(v1, v2)

    _v3d_lib.mulS.argtypes = [Vec3, ctypes.c_float]
    _v3d_lib.mulS.restype = Vec3
    def mulS(v: Vec3, scalar: float) -> Vec3:
        return _v3d_lib.mulS(v, scalar)

    _v3d_lib.dot.argtypes = [Vec3, Vec3]
    _v3d_lib.dot.restype = ctypes.c_float
    def dot(v1: Vec3, v2: Vec3) -> float:
        return _v3d_lib.dot(v1, v2)

    _v3d_lib.mag.argtypes = [Vec3]
    _v3d_lib.mag.restype = ctypes.c_float
    def mag(v: Vec3) -> float:
        return _v3d_lib.mag(v)

    _v3d_lib.norm.argtypes = [ctypes.POINTER(Vec3)]
    _v3d_lib.norm.restype = None
    def norm(v: Vec3) -> None:
        _v3d_lib.norm(ctypes.byref(v))

    _v3d_lib.print_vec.argtypes = [ctypes.c_char_p, Vec3]
    _v3d_lib.print_vec.restype = None
    def print_vec(name: str, v: Vec3) -> None:
        _v3d_lib.print_vec(name.encode('utf-8'), v)

if __name__ == "__main__":
    if _v3d_lib:
        print("C library loaded successfully. Demonstrating functions:")

        vA = set(1.0, 2.0, 3.0)
        vB = set(4.0, 5.0, 6.0)

        print(f"vA: {vA}")
        print(f"vB: {vB}")

        vC = add(vA, vB)
        print(f"vA + vB: {vC}")

        vD = sub(vA, vB)
        print(f"vA - vB: {vD}")

        vE = mulS(vA, 2.5)
        print(f"vA * 2.5: {vE}")

        d = dot(vA, vB)
        print(f"Dot product of vA and vB: {d}")

        m = mag(vA)
        print(f"Magnitude of vA: {m}")

        vF = set(1.0, 1.0, 0.0)
        print(f"Before normalization, vF: {vF}")
        norm(vF)
        print(f"After normalization, vF: {vF}")
        print(f"Magnitude of normalized vF: {mag(vF)}")

        print_vec("MyVector", set(7.0, 8.0, 9.0))
    else:
        print("C library was not loaded. Cannot run examples.")

