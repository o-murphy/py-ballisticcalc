# 375 CheyTac Hornady 390gr A-Tip custom drag function
from py_ballisticcalc import PreferredUnits, Unit, DragModelMultiBC, BCPoint, TableG7

PreferredUnits.velocity = Unit.MPS
PreferredUnits.adjustment = Unit.Mil
PreferredUnits.temperature = Unit.Celsius
PreferredUnits.distance = Unit.Meter
PreferredUnits.sight_height = Unit.Centimeter
PreferredUnits.drop = Unit.Centimeter
PreferredUnits.weight = Unit.Grain
PreferredUnits.length = Unit.Inch
PreferredUnits.diameter = Unit.Inch


dm = DragModelMultiBC([
    BCPoint(V=920, BC=0.494),
    BCPoint(V=800, BC=0.478),
    BCPoint(V=610, BC=0.473),
    BCPoint(V=418, BC=0.500),
    BCPoint(V=325, BC=0.453),
], TableG7, 390, 0.375, 2.032)


cdm = [i for i in dm.drag_table]
for i in cdm:
    print(f"{i.Mach}\t{i.CD}".replace(".", ","))
