import logging
import re
from math import isinf
from typing import Any
import os

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import py_ballisticcalc
from py_ballisticcalc import (
    basicConfig, Unit, Weapon, logger, Atmo, AbstractUnitType, Ammo, DragModel,
    get_drag_tables_names, BCPoint, DragModelMultiBC, Wind, DragDataPoint, Distance
)

__all__ = ('ProfileLoadingError', 'load_multiple_toml', 'load_profile')

logger.setLevel(logging.INFO)


class ProfileLoadingError(Exception):
    pass


def check_expected_props(props: dict, expected_props: [list, tuple], section=None, required=False) -> set:
    if len(not_provided := (expected_props - props.keys())) > 0:
        if required:
            raise ValueError(f"Required properties {not_provided} are not presented for {section=}")
        logger.debug(f"Not provided: {not_provided} for {section=}, defaults will be loaded")
        return not_provided


def get_prop(props: dict, key_: Any, default=None, section: str = './', required: bool = False, msg: str = '') -> ():
    if (ret := props.get(key_)) is default:
        _msg = (f"property '{key_}' not found in '{section}' "
                f"or returns {default}") + (f", {msg}" if msg else '')
        if required:
            raise KeyError(f"Required {_msg}")
        logger.warning(_msg)
    return ret


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
    required = ('barrel_twist', 'sight_height')
    check_expected_props(weapon, required, 'weapon', required=True)

    barrel_twist = load_dimension(weapon['barrel_twist'], 'barrel_twist', 'weapon.barrel_twist')
    sight_height = load_dimension(weapon['sight_height'], 'sight_height', 'weapon.barrel_twist')

    if _zero_elevation := get_prop(weapon, 'zero_elevation', section="weapon"):
        zero_elevation = load_dimension(_zero_elevation, 'angular', 'weapon.zero_elevation')
        return Weapon(sight_height, barrel_twist, zero_elevation)

    logger.debug("weapon.zero_elevation not provided, default will be loaded")
    return Weapon(sight_height, barrel_twist)


def parse_bc(bc: [list, float, int, str]) -> [list[BCPoint], float]:
    if isinstance(bc, list):
        multi_bc = []

        for i, item in enumerate(bc):
            section = f"drag.bc[{i}]"
            _v = get_prop(item, "v", section=section, required=True)
            _bc = get_prop(item, "bc", section=section, required=True)
            _v_value = load_dimension(_v, 'velocity', f'{section}.v')
            try:
                _bc_value = float(_bc)
            except ValueError:
                raise ValueError(f"could not convert string to float: {section}.bc={_bc}")

            multi_bc.append(BCPoint(BC=_bc_value, V=_v_value))
        return multi_bc

    elif isinstance(bc, (float, int, str)):
        return float(bc)
    raise TypeError(f"bc have be a list of BCPoints or number")


def parse_custom_table(custom_table: list) -> list[DragDataPoint]:
    def parse_row(row_: dict, idx: int = 0) -> DragDataPoint:

        section = f'drag.custom_table[{idx}]'

        required = ("mach", "cd")

        # check_expected_props(row_, required, f"{section}.{custom_table[idx]=}", required=True)

        mach = get_prop(row_, "mach", section=section, required=True)
        cd = get_prop(row_, "cd", section=section, required=True)

        if mach is not None and mach >= 0:
            if not isinstance(mach, (str, float, int)):
                raise TypeError(
                    f"Mach value have to be parsed as float {section}.mach={custom_table[idx]['mach']})"
                )
        else:
            raise ValueError(f"Mach value have to be >= 0 {section}={custom_table[idx]}")

        if mach >= 0:
            if not isinstance(cd, (str, float, int)):
                raise TypeError(
                    f"CD value have to be parsed as float {section}.cd={custom_table[idx]['cd']=})"
                )
        else:
            raise ValueError(f"CD value have to be >= 0 {section}={custom_table[idx]}")

        return DragDataPoint(float(mach), float(cd))

    if not isinstance(custom_table, list) or len(custom_table) == 0:
        raise TypeError(f"drag.custom_table have to be a list and not be empty")

    drag_data_points = []

    for i, row in enumerate(custom_table):
        drag_data_points.append(parse_row(row))
    return drag_data_points


def parse_drag(drag: dict) -> DragModel:
    required = ('bullet_weight', 'bullet_diameter', 'bullet_length')

    check_expected_props(drag, required, "ammo.drag", required=True)

    drag_kwargs = {}

    # bullet dimensions load
    if _bullet_weight := get_prop(drag, 'bullet_weight', section="drag", required=True):
        drag_kwargs['weight'] = load_dimension(
            _bullet_weight, 'weight', 'drag.bullet_weight')

    if _bullet_diameter := get_prop(drag, 'bullet_diameter', section="drag", required=True):
        drag_kwargs['diameter'] = load_dimension(
            _bullet_diameter, 'diameter', 'drag.bullet_diameter')

    if _bullet_length := get_prop(drag, 'bullet_length', section="drag", required=True):
        drag_kwargs['length'] = load_dimension(
            _bullet_length, 'length', 'drag.bullet_length')

    _model = get_prop(drag, 'model', section="drag")
    _bc = get_prop(drag, 'bc', section="drag")
    _custom_table = get_prop(drag, 'custom_table', section="drag")

    if any((_model, _bc)) and _custom_table:
        raise ValueError(
            "You cannot specify all at same time: bc, model and custom_table "
            "Please use (model + bc) or custom_table instead"
        )

    if all((_model, _bc)):

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

    elif _custom_table:
        if _drag_table := parse_custom_table(_custom_table):
            return DragModel(bc=1, drag_table=_drag_table, **drag_kwargs)
        else:
            raise ValueError("Wrong custom drag table")

    else:
        raise TypeError("Unrecognized drag data provided")


def parse_ammo(ammo: dict) -> Ammo:
    required = ('muzzle_velocity', 'drag', 'powder_temp', 'powder_temp_modifier')

    check_expected_props(ammo, required, 'ammo', required=True)

    ammo_kwargs = {}

    if _muzzle_velocity := get_prop(ammo, 'muzzle_velocity', section="ammo"):
        ammo_kwargs['mv'] = load_dimension(
            _muzzle_velocity, 'velocity', 'ammo.muzzle_velocity')

    if _powder_temp := get_prop(ammo, 'powder_temp', section="ammo"):
        ammo_kwargs['powder_temp'] = load_dimension(
            _powder_temp, 'temperature', 'ammo.powder_temp')

    if _powder_temp_modifier := get_prop(ammo, 'powder_temp_modifier', section="ammo"):
        try:
            ammo_kwargs['temp_modifier'] = float(_powder_temp_modifier)
        except ValueError as err:
            logger.warning(f"Powder temp modifier load "
                           f"warning for value={_powder_temp_modifier}: {err}")

    if _drag := get_prop(ammo, 'drag', section="ammo", required=True):
        ammo_kwargs['dm'] = parse_drag(_drag)
        logger.debug(f"Loaded: dm={ammo_kwargs['dm']}")

    return Ammo(**ammo_kwargs)


def parse_zero_atmo(zero_atmo: dict) -> Atmo:
    # just for debug
    expected = ('altitude', 'pressure', 'temperature', 'humidity')
    check_expected_props(zero_atmo, expected, 'zero_atmo')

    atmo_kwargs = {}

    if _altitude := get_prop(zero_atmo, 'altitude', section="zero_atmo"):
        atmo_kwargs['altitude'] = load_dimension(
            _altitude, 'distance', 'zero_atmo.altitude')

    if _pressure := get_prop(zero_atmo, 'pressure', section="zero_atmo"):
        atmo_kwargs['pressure'] = load_dimension(
            _pressure, 'pressure', 'zero_atmo.pressure')

    if _temperature := get_prop(zero_atmo, 'temperature', section="zero_atmo"):
        atmo_kwargs['temperature'] = load_dimension(
            _temperature, 'temperature', 'zero_atmo.temperature')

    if _humidity := get_prop(zero_atmo, 'humidity', section="zero_atmo"):
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

    def parse_single_wind(_wind: dict, requires_until_distance=False, idx=0) -> Wind:
        section = f"wind[{idx}]"
        expected = ('until_distance',)
        required = ['velocity', 'direction_from']
        if requires_until_distance:
            required += ['until_distance']

        check_expected_props(_wind, expected, f"{section}")
        check_expected_props(_wind, required, f"{section}", required=True)

        wind_kwargs = {}

        if _velocity := get_prop(_wind, 'velocity', section=section, required=True):
            wind_kwargs['velocity'] = load_dimension(
                _velocity, 'velocity', f'{section}.velocity')

        if _direction_from := get_prop(_wind, 'direction_from', section=section, required=True):
            wind_kwargs['direction_from'] = load_dimension(
                _direction_from, 'angular', f'{section}.direction_from')

        if _until_distance := get_prop(_wind, 'until_distance', section=section):
            wind_kwargs['until_distance'] = load_dimension(
                _until_distance, 'distance', f'{section}.until_distance')

        if not ('velocity' and 'direction_from') in wind_kwargs:
            raise ValueError(f"Wrong wind[{i}]")

        return Wind(**wind_kwargs)

    if isinstance(wind, dict):
        return [parse_single_wind(wind)]
    elif isinstance(wind, list):
        if not len(wind):
            return [Wind()]
        winds = [parse_single_wind(w, True, i) for i, w in enumerate(wind)]
        return winds
    raise ValueError(f"Wrong wind provided: {wind}")


def read_toml(path: [str, os.PathLike]) -> dict:
    with open(path, 'rb') as fp:
        basicConfig(path)
        return tomllib.load(fp)


def load_profile(data: dict) -> [[None], (Weapon, Ammo, Atmo, [Wind], Distance)]:
    pybc = get_prop(data, "pybc", None, "<file>", required=True)

    weapon, ammo, zero_atmo, winds, zero_distance = None, None, None, None, None

    # _weapon = get_prop(pybc, "weapon", None, "<file>.pybc", required=True)
    if _weapon := get_prop(pybc, "weapon", None, "<file>.pybc"):
        weapon = parse_weapon(_weapon)
        logger.debug(f"Loaded: {weapon=}")
        _zero_distance = get_prop(_weapon, "zero_distance")
        zero_distance = load_dimension(_zero_distance, "weapon.zero_distance")

    # _ammo = get_prop(pybc, "ammo", None, "<file>.pybc", required=True)
    if _ammo := get_prop(pybc, "ammo", None, "<file>.pybc"):
        ammo = parse_ammo(_ammo)
        logger.debug(f"Loaded: {ammo=}")

    if _zero_atmo := get_prop(pybc, "zero_atmo", None, "<file>.zero_atmo",
                              # required=True, msg='ICAO Atmo will be loaded'):
                              msg='ICAO Atmo will be loaded'):
        zero_atmo = parse_zero_atmo(_zero_atmo)
        logger.debug(f"Loaded: {zero_atmo=}")

    if _winds := get_prop(pybc, "wind", None, "<file>.wind",
                          msg="empty Wind will be loaded"):
        winds = parse_winds(_winds)
        logger.debug(f"Loaded: {winds=}")

    return weapon, ammo, zero_atmo, winds, zero_distance


def load_multiple_toml(*toml_files: [str, os.PathLike]) -> (Weapon, Ammo, Atmo, [Wind], Distance):
    if len(toml_files) > 0:
        logger.warning(f"Last presented config overloads previous. Be care to provide valid data")

    weapon, ammo, zero_atmo, winds, zero_distance = None, None, None, None, None

    for toml_file in toml_files:
        try:
            logger.info(f"Loading {toml_file}")
            data = read_toml(toml_file)
            _weapon, _ammo, _zero_atmo, _winds, _zero_distance = load_profile(data)
            if _weapon:
                weapon = _weapon
            if _ammo:
                ammo = _ammo
            if _zero_atmo:
                zero_atmo = _zero_atmo
            if _winds:
                winds = _winds
            if _zero_distance:
                zero_distance = _zero_distance
        except Exception as err:
            if logger.level <= logging.DEBUG:
                logger.exception(err)
            raise ValueError(f"Error occurred in {toml_file}")

    if all((weapon, ammo, zero_atmo, winds, )):
        logger.info(f"weapon, ammo, zero_atmo, winds, zero_distance load successful")
        return weapon, ammo, zero_atmo, winds, zero_distance
    raise ValueError(f"No valid data provided in {toml_files}")
