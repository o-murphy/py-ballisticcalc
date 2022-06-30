from .bmath import unit
import math


class Timespan(object):
    """ Timespan object keeps the amount of time spent """

    def __init__(self, time: float):
        self._time = time

    @property
    def total_seconds(self) -> float:
        """
        :return: the total number of seconds
        """
        return self._time

    @property
    def seconds(self) -> float:
        """
        :return: the whole number of the seconds
        """
        return math.fmod(math.floor(self._time), 60)

    @property
    def minutes(self) -> float:
        """
        :return: the whole number of minutes
        """
        return math.fmod(math.floor(self._time / 60), 60)


class TrajectoryData(object):
    """ TrajectoryData object keeps information about one point of the trajectory """

    def __init__(self, time: Timespan,
                 travel_distance: unit.Distance,
                 velocity: unit.Velocity,
                 mach: float,
                 drop: unit.Distance,
                 drop_adjustment: unit.Angular,
                 windage: unit.Distance,
                 windage_adjustment: unit.Angular,
                 energy: unit.Energy,
                 optimal_game_weight: unit.Weight):
        self._time = time
        self._travel_distance = travel_distance
        self._velocity = velocity
        self._mach = mach
        self._drop = drop
        self._drop_adjustment = drop_adjustment
        self._windage = windage
        self._windage_adjustment = windage_adjustment
        self._energy = energy
        self._optimal_game_weight = optimal_game_weight

    @property
    def time(self) -> Timespan:
        """
        :return: the amount of time spent since the shot moment
        """
        return self._time

    @property
    def travelled_distance(self) -> unit.Distance:
        """
        :return: the distance measured between the muzzle and the projection of the current bullet position to
        the line between the muzzle and the target
        """
        return self._travel_distance

    @property
    def velocity(self) -> unit.Velocity:
        """
        :return: the current projectile velocity
        """
        return self._velocity

    @property
    def mach_velocity(self) -> float:
        """
        :return: the proportion between the current projectile velocity and the speed of the sound
        """
        return self._mach

    @property
    def drop(self) -> unit.Distance:
        """
        :return: the shorted distance between the projectile and the shot line
        The positive value means the the projectile is above this line and the negative value means that the projectile
        is below this line
        """
        return self._drop

    @property
    def drop_adjustment(self) -> unit.Angular:
        """
        :return: the angle between the shot line and the line from the muzzle to the current projectile position
        in the plane perpendicular to the ground
        """
        return self._drop_adjustment

    @property
    def windage(self) -> unit.Distance:
        """
        :return: the distance to which the projectile is displaced by wind
        """
        return self._windage

    @property
    def windage_adjustment(self) -> unit.Angular:
        """
        :return: the angle between the shot line and the line from the muzzle to the current projectile position
        in the place parallel to the ground
        """
        return self._windage_adjustment

    @property
    def energy(self) -> unit.Energy:
        """
        :return: the kinetic energy of the projectile
        """
        return self._energy

    @property
    def optimal_game_weight(self) -> unit.Weight:
        """
        :return: the weight of game to which a kill shot is
        probable with the kinetic energy that the projectile currently  have
        """
        return self._optimal_game_weight
