import ctypes
import os

# Load library
if os.name == "posix":
    lib = ctypes.CDLL("./libtest.so")
else:
    lib = ctypes.CDLL("testlib.dll")

# Define structure
class TrajectoryTable(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_double)),
        ("length", ctypes.c_size_t)
    ]

# Define C function signatures
lib.f1.argtypes = [ctypes.POINTER(TrajectoryTable)]
lib.f1.restype = ctypes.c_int

lib.f2.argtypes = [ctypes.POINTER(TrajectoryTable)]
lib.f2.restype = ctypes.c_int

lib.free_table.argtypes = [ctypes.POINTER(TrajectoryTable)]
lib.free_table.restype = None

# Python wrapper
class TableWrapper:
    def __init__(self):
        self._table = TrajectoryTable()
    
    def call_f2(self):
        res = lib.f2(ctypes.byref(self._table))
        return res
    
    def get_data(self):
        if not bool(self._table.data) or self._table.length == 0:
            return []
        return [self._table.data[i] for i in range(self._table.length)]
    
    def free(self):
        lib.free_table(ctypes.byref(self._table))

    def __del__(self):
        self.free()

# --- Test ---
if __name__ == "__main__":
    wrapper = TableWrapper()
    status = wrapper.call_f2()
    print("status:", status)
    data = wrapper.get_data()
    print("data:", data)
    wrapper.free()
