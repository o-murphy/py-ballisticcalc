import logging

from py_ballisticcalc.profile_loader import load_multiple_toml, ProfileLoadingError
from py_ballisticcalc import logger
import argparse
from importlib import metadata


version = metadata.metadata("py_ballisticcalc")['Version']


def add_general_arguments(parser):
    general = parser.add_argument_group('General')
    general.add_argument("-zd", "--shot-dist", action="store_true", help="Zero distance")
    general.add_argument("-sd", "--zero-dist", action="store_true", help="Shot distance")


def add_zero_atmo_group(parser):
    zero_atmo = parser.add_argument_group('Zero atmo', 'Zero atmosphere parameters')
    zero_atmo.add_argument("-zt", "--zero-t", action="store", help="Zero temperature")
    zero_atmo.add_argument("-zh", "--zero-h", action="store", help="Zero humidity")
    zero_atmo.add_argument("-zp", "--zero-p", action="store", help="Zero pressure")
    zero_atmo.add_argument("-za", "--zero-a", action="store", help="Zero altitude")


def add_shot_atmo_group(parser):
    shot_atmo = parser.add_argument_group('Atmosphere', 'Current atmosphere parameters')
    shot_atmo.add_argument("-at", "--atmo-t", action="store", help="Current temperature")
    shot_atmo.add_argument("-ah", "--atmo-h", action="store", help="Current humidity")
    shot_atmo.add_argument("-ap", "--atmo-p", action="store", help="Current pressure")
    shot_atmo.add_argument("-aa", "--atmo-a", action="store", help="Current altitude")


def add_wind_group(parser):
    wind = parser.add_argument_group('Wind', 'Shot wind data')
    wind.add_argument("-wv", "--wind-v", action="store", help="Wind velocity")
    wind.add_argument("-wd", "--wind-d", action="store", help="Wind direction")


def get_arg_parser():
    parser = argparse.ArgumentParser(
        prog=f'pybc v{version}',
        description="Tool for small arms ballistics calculations"
    )
    parser.add_argument('files', help="List of .toml files to configure calculator",
                        nargs='+', type=str)
    parser.add_argument("-v", "--version", action='version',
                        version=f'pybc v{version}', help="Show version")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug messages")

    add_general_arguments(parser)
    add_zero_atmo_group(parser)
    add_shot_atmo_group(parser)
    add_wind_group(parser)
    return parser


def main():
    try:
        parser = get_arg_parser()
        argv = parser.parse_args()

        if argv.debug:
            logger.setLevel(logging.DEBUG)
            logger.info("Debug messages enabled")

        weapon, ammo, zero_atmo, winds, zero_distance = load_multiple_toml(*argv.files)
        from pprint import pprint
        pprint(weapon)
        pprint(zero_distance)
        pprint(ammo)
        pprint(zero_atmo)
        pprint(winds)
    except ProfileLoadingError as exc:
        logger.exception(exc)
    except Exception as exc:
        logger.exception(exc)


if __name__ == '__main__':
    main()
