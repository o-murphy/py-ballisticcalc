from .bmath import unit


class ShotParameters(object):
    def __init__(self, sight_angle: unit.Angular, maximum_distance: unit.Distance, step: unit.Distance):
        """
        Creates parameters of the shot
        :param sight_angle: the angle between scope center line and the barrel center line
        :param maximum_distance:
        :param step:
        """
        self._sight_angle = sight_angle
        self._shot_angle = unit.Angular(0, unit.AngularRadian).validate()
        self._cant_angle = unit.Angular(0, unit.AngularRadian).validate()
        self._maximum_distance: unit.Distance = maximum_distance
        self._step: unit.Distance = step

    @property
    def sight_angle(self) -> unit.Angular:
        """
        :return: the angle of the sight
        """
        return self._sight_angle

    @property
    def shot_angle(self) -> unit.Angular:
        """
        :return: the angle of the shot
        """
        return self._shot_angle

    @property
    def cant_angle(self):
        """
        :return: the cant angle (the angle between centers of scope and the barrel projection and zenith line)
        """
        return self._cant_angle

    @property
    def maximum_distance(self) -> unit.Distance:
        """
        :return: the maximum distance to be calculated
        """
        return self._maximum_distance

    @property
    def step(self) -> unit.Distance:
        """
        :return: the step between calculation results
        """
        return self._step


class ShotParameterUnlevel(ShotParameters):
    def __init__(self, sight_angle: unit.Angular, maximum_distance: unit.Distance,
                 step: unit.Distance, shot_angle: unit.Angular, cant_angle: unit.Angular):
        super(ShotParameterUnlevel, self).__init__(sight_angle, maximum_distance, step)
        self._sight_angle = sight_angle
        self._shot_angle = shot_angle
        self._cant_angle = cant_angle
        self._maximum_distance: unit.Distance = maximum_distance
        self._step: unit.Distance = step
