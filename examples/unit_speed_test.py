from py_ballisticcalc import Distance, Unit
from timeit import timeit

N = 100

def init():
    for i in range(N):
        d = Distance(i, Unit.Meter)
    return d

def new():
    for i in range(N):
        d = object.__new__(Distance)
        d._value = i / 25.4 * 1000
        d._defined_units = Unit.Meter
    return d



def init_feet(v=100):
    return Distance(v, Unit.Foot)


def new_feet(v=100):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


print(timeit(init, number=1))
print(timeit(new, number=1))
print()
print(timeit(init_feet, number=1))
print(timeit(new_feet, number=1))
assert init() == new()
print(init(), new())