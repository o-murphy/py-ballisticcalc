"""Default logger for py_ballisticcalc library"""

import logging

__all__ = ('logger',)

formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger = logging.getLogger('py_balcalc')
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
