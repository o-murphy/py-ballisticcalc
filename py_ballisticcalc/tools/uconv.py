#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]
# ///
from py_ballisticcalc.unit import Unit, UnitTypeError
from argparse import ArgumentParser

try:
    from importlib.metadata import metadata

    __version__ = metadata("py-ballisticcalc")["Version"]
except Exception:
    __version__ = "unknown"


parser = ArgumentParser("uconv")
parser.add_argument("from_unit", type=str)
parser.add_argument("to_unit", type=str)
parser.add_argument("-s", action="store_true", help="Print string")
parser.add_argument("-n", action="store_true", help="Print number")
parser.add_argument("-r", action="store_true", help="Round number")
parser.add_argument("-u", action="store_true", help="Print repr")
parser.add_argument("-V", "--version", action="version", version=__version__)


def main() -> None:
    try:
        ns = parser.parse_args()
        inp = Unit.parse(ns.from_unit)
        to_unit = Unit._parse_unit(ns.to_unit)

        if inp is None:
            parser.error(f"Could not parse from_unit: {ns.from_unit}")
            return
        if to_unit is None:
            parser.error(f"Could not parse to_unit: {ns.to_unit}")
            return

        res = inp << to_unit

        # Type guard: ensure res has the required attributes
        if not hasattr(res, "unit_value") or not hasattr(res, "units"):
            parser.error("Invalid conversion result")
            return

        outs = []
        if ns.s:
            outs.append(res)
        if ns.n:
            raw = res.unit_value  # type: ignore[union-attr]
            if ns.r:
                outs.append(round(raw, res.units.accuracy))  # type: ignore[union-attr]
            else:
                outs.append(raw)
        if ns.u:
            outs.append(res.__repr__())
        if not outs and not ns.s:
            outs.append(res)
        print(" ".join([str(i) for i in outs]))
    except UnitTypeError as exc:
        parser.error(str(exc))
    except TypeError as exc:
        parser.error(f"Invalid input: {str(exc)}")
    except Exception as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
