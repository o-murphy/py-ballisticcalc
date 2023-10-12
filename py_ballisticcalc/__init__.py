"""LGPL library for small arms ballistic calculations (Python 3.8+)"""

__author__ = "o-murphy"
__copyright__ = ("",)

__credits__ = ["o-murphy"]
__version__ = "1.1.0b8"

from .drag_model import *  # pylint: disable=import-error
from .drag_tables import *
from .settings import *
from .multiple_bc import *
from .interface import *
from .trajectory_data import *
from .trajectory_calc import *  # pylint: disable=import-error
from .conditions import *
from .munition import *
from .unit import *
