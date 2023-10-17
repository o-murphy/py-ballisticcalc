"""LGPL library for small arms ballistic calculations (Python 3.8+)"""

__author__ = "o-murphy"
__copyright__ = ("",)

__credits__ = ["o-murphy"]
__version__ = "1.1.0b9"

import logging
try:
    from .drag_model import *  # pylint: disable=import-error
    from .trajectory_calc import *  # pylint: disable=import-error
except ImportError:
    logging.warning("Package installed in --no-binary (pure python) mode, "
                    "use .whl packages to get better performance")
    from .pure import *
from .drag_tables import *
from .settings import *
from .multiple_bc import *
from .interface import *
from .trajectory_data import *
from .conditions import *
from .munition import *
from .unit import *
