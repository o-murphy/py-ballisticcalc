from py_ballisticcalc import DragModel, TableG1, Distance, Weight, Ammo, Velocity, Weapon, Shot, Angular, Calculator, \
    Unit

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
calc = Calculator(_config={
    "cMinimumVelocity": 0,
    # "cMinimumAltitude": -1410.748,
})
shot = calc.fire(zero, Distance.Meter(1600.2437248702522), extra_data=True)

from py_ballisticcalc.visualize.plot import show_hit_result_plot

import matplotlib
matplotlib.use('TkAgg')
p = shot.plot()
show_hit_result_plot()

v_prev = 0
for p in shot:
    cur_v = p.velocity.raw_value
    if abs(cur_v - v_prev) > 0.5:
        print(p.velocity << Unit.MPS, p.distance << Unit.Meter)
        v_prev = cur_v
