from .bmath import unit


class WindInfo(object):
    """ WindInfo structure keeps information about wind """

    def __init__(self, until_distance: unit.Distance = None,
                 velocity: unit.Velocity = None, direction: unit.Angular = None):
        self._until_distance = until_distance
        self._velocity = velocity
        self._direction = direction

    def __str__(self):
        """
        :return: formatted Wind data
        """
        return f'Until distance: {self._until_distance}, Velocity: {self._velocity}, Direction: {self._direction}'

    @property
    def until_distance(self) -> unit.Distance:
        """
        :return: the distance from the shooter until which the wind blows
        """
        return self._until_distance

    @property
    def velocity(self) -> unit.Velocity:
        """
        :return: the wind velocity
        """
        return self._velocity

    @property
    def direction(self) -> unit.Angular:
        """
        0 degrees means wind blowing into the face
        90 degrees means wind blowing from the left
        -90 or 270 degrees means wind blowing from the right
        180 degrees means wind blowing from the back
        :return: the wind direction
        """
        return self._direction

    @staticmethod
    def create_no_wind() -> list['WindInfo']:
        """
        Creates wind description with no wind
        :return: list[WindInfo]
        """
        return [WindInfo()]

    @staticmethod
    def create_only_wind_info(wind_velocity: unit.Velocity, direction: unit.Angular) -> list['WindInfo']:
        """
        Creates the wind information for the constant wind for the whole distance of the shot
        :param wind_velocity: unit.Velocity instance
        :param direction: unit.Angular instance
        :return: list[WindInfo]
        """
        until_distance = unit.Distance(9999, unit.DistanceKilometer)
        return [WindInfo(until_distance, wind_velocity, direction)]

    @staticmethod
    def add_wind_info(until_distance: unit.Distance,
                      velocity: unit.Velocity, direction: unit.Angular) -> 'WindInfo':
        """
        Creates description of one wind
        :param until_distance: unit.Distance instance
        :param velocity: unit.Velocity instance
        :param direction: unit.Angular instance
        :return: WindInfo instance
        """
        return WindInfo(until_distance, velocity, direction)

    @staticmethod
    def create_wind_info(*winds: 'WindInfo') -> list['WindInfo']:
        """
        Creates a wind descriptor from multiple winds
        winds must be ordered from the closest to the muzzle point to the farthest to the muzzle point
        :param winds: *parsed list or ruple of WindInfo instances
        :return: list[WindInfo]
        """
        return list(winds)


if __name__ == '__main__':
    wind = WindInfo(
        unit.Distance(500, unit.DistanceMeter),
        unit.Velocity(15, unit.VelocityKMH),
        unit.Angular(10, unit.AngularRadian)
    )
