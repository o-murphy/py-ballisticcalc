import sys
sys.path.insert(0, "scripts")
from benchmark import _build_shot
from py_ballisticcalc import Calculator, Distance
import bcy
c = Calculator(engine="bcy:NativeDormandPrinceIntegrationEngine"); e = c._engine_factory(c.config)
shot = _build_shot(False)
ft = Distance.Meter(10)._feet
for dense in (1, 0):
    print(f"dense={dense}")
    for what in ("fill", "call"):
        best = min(bcy._probe(e, shot, 3000, what, ft, dense) for _ in range(7))
        print(f"  {what:5} {best*1e6:7.2f} us")
    conv = min((bcy._probe(e, shot, 3000, "conv", ft, dense) for _ in range(7)), key=lambda x: x[0])
    print(f"  conv  {conv[0]*1e6:7.2f} us   ({conv[1]} records, {conv[2]} dense steps)")
