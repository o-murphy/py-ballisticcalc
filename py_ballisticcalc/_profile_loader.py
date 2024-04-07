import logging
import re
from math import isinf

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import py_ballisticcalc
from py_ballisticcalc import basicConfig, Unit, Weapon, logger, Atmo, AbstractUnitType, Ammo, DragModel, \
    get_drag_tables_names, BCPoint, DragModelMultiBC, Wind

logger.setLevel(logging.DEBUG)


def check_expected_props(props: dict, expected_props: [list, tuple], section=None) -> set:
    # just for debug
    if logger.level <= logging.DEBUG:
        if len(not_provided := (expected_props - props.keys())):
            logger.debug(f"Not provided: {not_provided} for {section=}, defaults will be loaded")
            return not_provided


def check_required_props(props: dict, required_props: [list, tuple], section=None) -> None:
    if len(not_presented := (required_props - props.keys())):
        raise ValueError(f"Required properties {not_presented} are not presented for {section=}")


def load_dimension(dimension: [dict, int, str, float],
                   preferred: str, key: str = None) -> AbstractUnitType:
    if isinstance(dimension, (str, int, float)):
        if isinstance(dimension, (float, int)) and isinf(dimension):
            dimension = 9999

        return Unit.parse_value(dimension, preferred)
    if isinstance(dimension, dict):
        value = dimension.get('value')
        units = dimension.get('units')
        if isinstance(dimension, (float, int)) and isinf(dimension):
            value = 9999
        if value and units:
            return Unit.parse_value(value, units)
        if value:
            return Unit.parse_value(value, preferred)
        raise ValueError(f"Neither value and units provided for {key=}")
    raise TypeError(f"dimension of {key=} have to be an instance of dict, str, float or int, not {type(dimension)}")


def parse_weapon(weapon: dict) -> Weapon:
    expected = ('barrel_twist', 'sight_height')
    required = ('barrel_twist', 'sight_height')

    check_expected_props(weapon, expected, 'pybc.weapon')
    check_required_props(weapon, required, 'pybc.weapon')

    barrel_twist = load_dimension(weapon['barrel_twist'], 'barrel_twist', 'weapon.barrel_twist')
    sight_height = load_dimension(weapon['sight_height'], 'sight_height', 'weapon.barrel_twist')

    if _zero_elevation := weapon.get('zero_elevation'):
        zero_elevation = load_dimension(_zero_elevation, 'angular', 'weapon.zero_elevation')
        return Weapon(sight_height, barrel_twist, zero_elevation)

    logger.debug("weapon.zero_elevation not provided, default will be loaded")
    return Weapon(sight_height, barrel_twist)


def parse_bc(bc: [list, float, int, str]) -> [list[BCPoint], float]:

    if isinstance(bc, list):
        multi_bc = []

        for i, item in enumerate(bc):
            _v = item.get("v")
            _bc = item.get('bc')
            if not _v or not _bc:
                raise ValueError("Each item of list of bc have been a mapping {v: <velocity>, bc: <float>}")
            _v_value = load_dimension(_v, 'velocity', f'drag.bc[{i}].v')
            try:
                _bc_value = float(_bc)
            except ValueError:
                raise ValueError(f"could not convert string to float: drag.bc[{i}].bc={_bc}")

            multi_bc.append(BCPoint(BC=_bc_value, V=_v_value))
        return multi_bc

    elif isinstance(bc, (float, int, str)):
        return float(bc)
    raise TypeError(f"bc have be a list of BCPoints or number")


def parse_drag(drag: dict) -> DragModel:
    expected = ('bullet_weight', 'bullet_diameter', 'bullet_length')
    required = ('bullet_weight', 'bullet_diameter', 'bullet_length')

    check_expected_props(drag, expected, "ammo.drag")
    check_required_props(drag, required, "ammo.drag")

    drag_kwargs = {}

    # bullet dimensions load
    if _bullet_weight := drag.get('bullet_weight'):
        drag_kwargs['weight'] = load_dimension(
            _bullet_weight, 'weight', 'ammo.drag.bullet_weight')

    if _bullet_diameter := drag.get('bullet_diameter'):
        drag_kwargs['diameter'] = load_dimension(
            _bullet_diameter, 'diameter', 'ammo.drag.bullet_diameter')

    if _bullet_length := drag.get('bullet_length'):
        drag_kwargs['length'] = load_dimension(
            _bullet_length, 'length', 'ammo.drag.bullet_length')

    _model = drag.get('model')
    _bc = drag.get('bc')
    _custom_table = drag.get('custom_table')

    if all((_model, _bc, _custom_table)):
        raise ValueError(
            "You cannot specify all at same time: bc, model and custom_table "
            "Please use (model + bc) or custom_table instead"
        )

    if _custom_table:
        raise NotImplementedError

    if not all((_model, _bc)):
        raise ValueError(f"Expected both (model and bc) is not None: model={_model}, bc={_bc}")

    model_match = ''
    for pattern in (r"^table(g\w)$", r"^(g\w)$"):
        if _model_match := re.match(pattern, _model, re.IGNORECASE):
            model_match = _model_match.group(1).upper()
            break

    if not hasattr(py_ballisticcalc, f"Table{model_match}"):
        raise ValueError(f"Unrecognized model: {_model}, "
                         f"use one of the following: {get_drag_tables_names()}")

    drag_kwargs['drag_table'] = getattr(py_ballisticcalc, f"Table{model_match}")
    bc = parse_bc(_bc)

    if isinstance(bc, float):
        drag_kwargs['bc'] = bc
        return DragModel(**drag_kwargs)
    elif isinstance(bc, list):
        drag_kwargs['bc_points'] = bc
        return DragModelMultiBC(**drag_kwargs)
    else:
        raise TypeError("Unrecognized bc")


def parse_ammo(ammo: dict) -> Ammo:
    expected = ('muzzle_velocity', 'drag', 'powder_temp', 'powder_temp_modifier')
    required = ('muzzle_velocity', 'drag', 'powder_temp', 'powder_temp_modifier')

    check_expected_props(ammo, expected, 'pybc.ammo')
    check_required_props(ammo, required, 'pybc.ammo')

    ammo_kwargs = {}

    if _muzzle_velocity := ammo.get('muzzle_velocity'):
        ammo_kwargs['mv'] = load_dimension(
            _muzzle_velocity, 'velocity', 'ammo.muzzle_velocity')

    if _powder_temp := ammo.get('powder_temp'):
        ammo_kwargs['powder_temp'] = load_dimension(
            _powder_temp, 'temperature', 'ammo.powder_temp')

    if _powder_temp_modifier := ammo.get('powder_temp_modifier'):
        try:
            ammo_kwargs['temp_modifier'] = float(_powder_temp_modifier)
        except ValueError as err:
            logger.warning(f"Powder temp modifier load warning for value={_powder_temp_modifier}: {err}")

    if _drag := ammo.get('drag'):
        ammo_kwargs['dm'] = parse_drag(_drag)
        logger.debug(f"Loaded: dm={ammo_kwargs['dm']}")
    else:
        raise ValueError("pybc.ammo.drag section not provided")

    return Ammo(**ammo_kwargs)


def parse_zero_atmo(zero_atmo: dict) -> Atmo:
    # just for debug
    expected = ('altitude', 'pressure', 'temperature', 'humidity')
    check_expected_props(zero_atmo, expected, 'pybc.zero_atmo')

    atmo_kwargs = {}

    if _altitude := zero_atmo.get('altitude'):
        atmo_kwargs['altitude'] = load_dimension(
            _altitude, 'distance', 'zero_atmo.altitude')

    if _pressure := zero_atmo.get('pressure'):
        atmo_kwargs['pressure'] = load_dimension(
            _pressure, 'pressure', 'zero_atmo.pressure')

    if _temperature := zero_atmo.get('temperature'):
        atmo_kwargs['temperature'] = load_dimension(
            _temperature, 'temperature', 'zero_atmo.temperature')

    if _humidity := zero_atmo.get('humidity'):
        try:
            atmo_kwargs['humidity'] = float(_humidity)
        except ValueError as err:
            logger.warning(f"Humidity load warning for humidity={_humidity}: {err}")

    if not len(atmo_kwargs):
        logger.warning(f"No zero_atmo properties presented, ICAO atmo profile will be loaded")
        return Atmo.icao()
    return Atmo(**atmo_kwargs)


def parse_winds(wind: [dict, list]) -> list[Wind]:

    i = 0

    def parse_single_wind(_wind: dict, requires_until_distance=False) -> Wind:
        expected = ('velocity', 'direction_from', 'until_distance')
        required = ['velocity', 'direction_from']
        if requires_until_distance:
            required += ['until_distance']

        check_expected_props(_wind, expected, f"pybc.wind[{i}]")
        check_required_props(_wind, expected, f"pybc.wind[{i}]")

        wind_kwargs = {}

        if _velocity := _wind.get('velocity'):
            wind_kwargs['velocity'] = load_dimension(
                _velocity, 'velocity', f'pybc.wind[{i}].velocity')

        if _direction_from := _wind.get('direction_from'):
            wind_kwargs['direction_from'] = load_dimension(
                _direction_from, 'angular', f'pybc.wind[{i}].direction_from')

        if _until_distance := _wind.get('until_distance'):
            wind_kwargs['until_distance'] = load_dimension(
                _until_distance, 'distance', f'pybc.wind[{i}].until_distance')

        if not ('velocity' and 'direction_from') in wind_kwargs:
            raise ValueError(f"Wrong pybc.wind[{i}]")

        return Wind(**wind_kwargs)

    if isinstance(wind, dict):
        return [parse_single_wind(wind)]
    elif isinstance(wind, list):
        if not len(wind):
            return [Wind()]
        winds = [parse_single_wind(w, requires_until_distance=True) for i, w in enumerate(wind)]
        return winds
    raise ValueError(f"Wrong pybc.wind provided: {wind}")


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
            logger.debug(f"Loaded: {ammo=}")
        else:
            raise ValueError("pybc.ammo section not provided")

        if _zero_atmo := pybc.get("zero_atmo"):
            zero_atmo = parse_zero_atmo(_zero_atmo)
            logger.debug(f"Loaded: {zero_atmo=}")
        else:
            logger.debug(f"ZeroAtmo section not provided, ICAO Atmo will be loaded")

        if _winds := pybc.get("wind"):
            winds = parse_winds(_winds)
            logger.debug(f"Loaded: {winds=}")
        else:
            logger.debug(f"pybc.wind section not provided, empty Wind will be loaded")
            winds = [Wind()]
        logger.debug(f"Loaded: {winds=}")

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
