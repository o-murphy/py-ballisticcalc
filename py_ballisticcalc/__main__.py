import logging
import sys

from py_ballisticcalc.profile_loader import load_multiple_toml
from py_ballisticcalc import logger
import argparse
from importlib import metadata


version = metadata.metadata("py_ballisticcalc")['Version']


def main(argv):
    try:
        parser = argparse.ArgumentParser(
            prog=f'pybc v{version}',
            description="Tool for small arms ballistics calculations"
        )
        parser.add_argument('files', help="List of .toml files to configure calculator",
                            nargs='+', type=str)
        parser.add_argument("-v", "--version", action='version',
                            version=f'pybc v{version}', help="Show version")
        parser.add_argument("-d", "--debug", action="store_true", help="Enable debug messages")

        parser.add_argument("-sd", "--shot-dist", action="store_true", help="Shot distance")

        zero_atmo = parser.add_argument_group('Zero atmo', 'Zero atmosphere parameters')
        zero_atmo.add_argument("-zt", "--zero-t", action="store", help="Zero temperature")
        zero_atmo.add_argument("-zh", "--zero-h", action="store", help="Zero humidity")
        zero_atmo.add_argument("-zp", "--zero-p", action="store", help="Zero pressure")
        zero_atmo.add_argument("-za", "--zero-a", action="store", help="Zero altitude")

        wind = parser.add_argument_group('Wind', 'Shot wind data')
        wind.add_argument("-wv", "--wind-v", action="store", help="Wind velocity")
        wind.add_argument("-wd", "--wind-d", action="store", help="Wind direction")

        argv = parser.parse_args()
        print(argv)
        if argv.debug:
            logger.setLevel(logging.DEBUG)
            logger.info("Debug messages enabled")

        weapon, ammo, zero_atmo, winds = load_multiple_toml(*argv.files)
        from pprint import pprint
        pprint(weapon)
        print(ammo)
        print(zero_atmo)
        print(winds)
    except Exception as exc:
        logger.exception(exc)


if __name__ == '__main__':
    main(sys.argv)
