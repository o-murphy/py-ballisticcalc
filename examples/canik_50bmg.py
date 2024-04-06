from py_ballisticcalc import Unit, PreferredUnits
from py_ballisticcalc import DragModel, TableG1
from py_ballisticcalc import Ammo
from py_ballisticcalc import Weapon, Shot, Calculator


PreferredUnits.distance = Unit.METER
PreferredUnits.velocity = Unit.MPS
PreferredUnits.sight_height = Unit.CENTIMETER

dm = DragModel(0.62, TableG1, 661, 0.51)
ammo = Ammo(dm, 2.3, 837)

weapon = Weapon(9, 500, 15, Unit.DEGREE(30))
calc = Calculator(weapon, ammo)
zero_elevation = calc.elevation
print(f'Barrel elevation for zero: {zero_elevation << Unit.MIL}')

shot = Shot(3000, zero_angle=calc.elevation, relative_angle=Unit.MIL(0))
shot_result = calc.fire(shot, 100, extra_data=False)
shot_result.dataframe.to_clipboard()
