from .bmath import unit
from .atmosphere import Atmosphere
from .projectile import Ammunition


class ZeroInfo(object):
    """ ZeroInfo object keeps the information about zeroing of the weapon """

    def __init__(self, distance: unit.Distance,
                 has_ammunition: bool = False,
                 has_atmosphere: bool = False,
                 ammunition: Ammunition = None, atmosphere: Atmosphere = None):
        self._has_ammunition = has_ammunition
        self._has_atmosphere = has_atmosphere
        self._zero_distance = distance
        self._ammunition = ammunition
        self._zero_atmosphere = atmosphere

    @property
    def has_ammunition(self) -> bool:
        """
        :return: flag indicating whether other ammo is used to zero
        """
        return self._has_ammunition

    @property
    def ammunition(self) -> Ammunition:
        """
        :return: ammo used to zero
        """
        return self._ammunition

    @property
    def has_atmosphere(self) -> bool:
        """
        :return: flag indicating whether weapon is zeroed under different conditions
        """
        return self._has_atmosphere

    @property
    def atmosphere(self) -> Atmosphere:
        """
        :return: conditions at the time of zeroing
        """
        return self._zero_atmosphere

    @property
    def zero_distance(self) -> unit.Distance:
        """
        :return: the distance at which the weapon was zeroed
        """
        return self._zero_distance

    @staticmethod
    def create_info(distance: unit.Distance) -> 'ZeroInfo':
        return ZeroInfo(has_ammunition=False,
                        has_atmosphere=False,
                        distance=distance)

    @staticmethod
    def create_with_atmosphere(distance: unit.Distance, atmosphere: Atmosphere) -> 'ZeroInfo':
        """
        Creates zero information using distance and conditions
        :param distance: unit.Distance instance
        :param atmosphere: Atmosphere instance
        :return: ZeroInfo instance
        """
        return ZeroInfo(has_ammunition=False,
                        has_atmosphere=True,
                        distance=distance,
                        atmosphere=atmosphere)

    @staticmethod
    def create_with_another_ammo(distance: unit.Distance, ammo: Ammunition) -> 'ZeroInfo':
        """
        Creates zero information using distance and other ammunition
        :param distance: unit.Distance instance
        :param ammo: Ammunition instance
        :return: ZeroInfo instance
        """
        return ZeroInfo(has_ammunition=True,
                        has_atmosphere=False,
                        distance=distance,
                        ammunition=ammo)

    @staticmethod
    def create_with_another_ammo_and_atmosphere(distance: unit.Distance, ammo: Ammunition,
                                                atmosphere: Atmosphere) -> 'ZeroInfo':
        """
        Creates zero information using distance, other conditions and other ammunition
        :param distance: unit.Distance instance
        :param ammo: Ammunition instance
        :param atmosphere: Atmosphere instance
        :return: ZeroInfo instance
        """
        return ZeroInfo(
            has_ammunition=True,
            has_atmosphere=False,
            distance=distance,
            ammunition=ammo,
            atmosphere=atmosphere
        )


TwistRight = 1
TwistLeft = 2


class TwistInfo(object):
    def __init__(self, direction: int, twist: unit.Distance):
        """
        Creates twist information
        :param direction: Direction must be either Twist_Right or Twist_Left constant
        :param twist: unit.Distance instance
        """
        self._twist_direction = direction
        self._rifling_twist = twist

    @property
    def direction(self) -> int:
        """
        :return: the twist direction (see TwistRight and TwistLeft)
        """
        return self._twist_direction

    @property
    def twist(self) -> unit.Distance:
        """
        :return: the twist step (the distance inside the barrel at which the projectile makes one turn)
        """
        return self._rifling_twist


class Weapon(object):
    """ Weapon object contains the weapon description """

    def __init__(self, sight_height: unit.Distance, zero_info: ZeroInfo,
                 has_twist_info: bool = False, twist: TwistInfo = None, click_value: unit.Angular = None):
        """
        Ceates the weapon definition with no twist info
        :param sight_height: unit.Distance instance
        :param zero_info: ZeroInfo instance
        :param has_twist_info: bool (is twist)
        :param twist: TwistInfo instance
        :param click_value: unit.Angular instance
        """
        self._sight_height = sight_height
        self._zero_info = zero_info
        self._has_twist_info = has_twist_info
        self._twist = twist
        self._click_value = click_value

    @property
    def sight_height(self) -> unit.Distance:
        """
        :return: the height of the sight center line over the barrel center line
        """
        return self._sight_height

    @property
    def zero(self) -> ZeroInfo:
        """
        :return: the zeroing information
        """
        return self._zero_info

    @property
    def has_twist(self) -> bool:
        """
        :return: the flag indicating whether the rifling twist information is set
        """
        return self._has_twist_info

    @property
    def twist(self) -> TwistInfo:
        """
        :return: the rifling twist information
        """
        return self._twist

    @property
    def click_value(self) -> unit.Angular:
        """
        :return: the value of one click of the scope
        """
        return self._click_value

    @click_value.setter
    def click_value(self, click: unit.Angular):
        """
        Sets the value of one click of the scope
        :param click: unit.Angular instance
        :return: None
        """
        self._click_value = click

    @staticmethod
    def create_with_twist(sight_height: unit.Distance, zero_info: ZeroInfo, twist: TwistInfo) -> 'Weapon':
        """
        Creates weapon description with twist info
        :param sight_height: unit.Distance instance
        :param zero_info: ZeroInfo instance
        :param twist: TwistInfo instance
        :return: Weapon instance
        """
        return Weapon(
            sight_height=sight_height,
            zero_info=zero_info,
            has_twist_info=True,
            twist=twist
        )
