from py_ballisticcalc import (DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot,
                              Angular, Calculator, logger)
from py_ballisticcalc.helpers import must_fire

drag_model = DragModel(bc=0.03,
                       drag_table=TableG1,
                       diameter=Distance.Millimeter(23),
                       weight=Weight.Gram(188.5),
                       length=Distance.Millimeter(108.2))
ammo = Ammo(drag_model, Velocity.MPS(930))
weapon = Weapon()

zero = Shot(weapon=weapon,
            ammo=ammo,
            relative_angle=Angular.Degree(1.0))

calc = Calculator(config={
    "cMinimumVelocity": 0,
    # "cMinimumAltitude": -1410.748, # have this value by default
})

hit_result, err = must_fire(calc, zero, Distance.Meter(1600.2437248702522), extra_data=True)

if err:
    logger.warning("%s, trajectory incomplete", err)

# display hit result
from py_ballisticcalc.visualize.plot import show_hit_result_plot
import matplotlib

matplotlib.use('TkAgg')
p = hit_result.plot()
show_hit_result_plot()
