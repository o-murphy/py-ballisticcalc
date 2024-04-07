import logging

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from py_ballisticcalc import basicConfig, Unit, Weapon, logger, Atmo

logger.setLevel(logging.DEBUG)


def check_expected_props(props, expected_props, section=None):
    # just for debug
    if len(not_provided := (expected_props - props.keys())):
        logger.debug(f"Not provided: {not_provided} for {section=}, defaults will be loaded")


def load_dimension(dimension: [dict, int, str, float],
                   preferred: str, key: str = None):
    if isinstance(dimension, (str, int, float)):
        return Unit.parse_value(dimension, preferred)
    if isinstance(dimension, dict):
        value = dimension.get('value')
        units = dimension.get('units')
        if value and units:
            return Unit.parse_value(value, units)
        if value:
            return Unit.parse_value(value, preferred)
        raise ValueError(f"Neither value and units provided for {key=}")
    raise TypeError(f"dimension of {key=} have to be an instance of dict, str, float or int, not {type(dimension)}")


def parse_weapon(weapon: dict):
    expected = ('barrel_twist', 'sight_height')
    required = ('barrel_twist', 'sight_height')

    check_expected_props(weapon, expected, 'weapon')

    if len(not_presented := (required - weapon.keys())):
        raise ValueError(f"Required properties {not_presented} are not presented for weapon")

    barrel_twist = load_dimension(weapon['barrel_twist'], 'barrel_twist', 'weapon.barrel_twist')
    sight_height = load_dimension(weapon['sight_height'], 'sight_height', 'weapon.barrel_twist')

    if _zero_elevation := weapon.get('zero_elevation'):
        zero_elevation = load_dimension(_zero_elevation, 'angular', 'weapon.zero_elevation')
        return Weapon(sight_height, barrel_twist, zero_elevation)

    logger.debug("weapon.zero_elevation not provided, default will be loaded")
    return Weapon(sight_height, barrel_twist)


def parse_ammo(ammo: dict):
    ...


def parse_zero_atmo(zero_atmo: dict):

    # just for debug
    expected = ('altitude', 'pressure', 'temperature', 'humidity')
    check_expected_props(zero_atmo, expected, 'zero_atmo')

    atmo_kwargs = {}

    if _altitude := zero_atmo.get('altitude'):
        atmo_kwargs['altitude'] = load_dimension(_altitude, 'distance', 'zero_atmo.altitude')

    if _pressure := zero_atmo.get('pressure'):
        atmo_kwargs['pressure'] = load_dimension(_pressure, 'pressure', 'zero_atmo.pressure')

    if _temperature := zero_atmo.get('temperature'):
        atmo_kwargs['temperature'] = load_dimension(_temperature, 'temperature', 'zero_atmo.temperature')\

    if _humidity := zero_atmo.get('humidity'):
        try:
            atmo_kwargs['humidity'] = float(_humidity)
        except ValueError as err:
            logger.warning(f"Humidity load warning for humidity={_humidity}: {err}")

    return Atmo(**atmo_kwargs)


def load_toml(path):
    with open(path, 'rb') as fp:
        data = tomllib.load(fp)

    if pybc := data.get("pybc"):
        basicConfig(path)

        if _weapon := pybc.get('weapon'):
            weapon = parse_weapon(_weapon)
            logger.debug(f"Loaded: {weapon=}")
        else:
            raise ValueError("pybc.weapon section not provided")

        if _ammo := pybc.get("ammo"):
            ammo = parse_ammo(_ammo)
        else:
            raise ValueError("pybc.ammo section not provided")

        if _zero_atmo := pybc.get("zero_atmo"):
            zero_atmo = parse_zero_atmo(_zero_atmo)
            logger.debug(f"Loaded: {zero_atmo=}")

    else:
        raise ValueError("pybc section not provided")


if __name__ == '__main__':
    import os
    tomlpath = os.path.join(
        # os.path.dirname(os.getcwd()),
        os.path.dirname(os.path.dirname(__file__)),
        'examples', 'myammo.toml'
    )
    load_toml(tomlpath)


