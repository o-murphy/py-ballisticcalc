"""Global settings of the py_ballisticcalc library"""
import logging
from .unit import Distance

__all__ = ('Settings',)


class Settings:  # pylint: disable=too-few-public-methods
    """Global settings class of the py_ballisticcalc library"""

    _MAX_CALC_STEP_SIZE: float = 0.5
    USE_POWDER_SENSITIVITY: bool = False

    @classmethod
    def set_max_calc_step_size(cls, value: [float, Distance]):
        """
        _MAX_CALC_STEP_SIZE setter
        :param value: [float, Distance] maximum calculation step (used internally)
        """

        logging.warning("Settings._MAX_CALC_STEP_SIZE: change this property "
                        "only if you know what you are doing; "
                        "too big step can corrupt calculation accuracy")

        if not isinstance(value, (Distance, float, int)):
            raise ValueError("MAX_CALC_STEP_SIZE has to be a type of 'Distance'")
        cls._MAX_CALC_STEP_SIZE = cls.Units.distance(value) >> Distance.Foot

    @classmethod
    def get_max_calc_step_size(cls) -> [float, Distance]:
        return cls._MAX_CALC_STEP_SIZE
