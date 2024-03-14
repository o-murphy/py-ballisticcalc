"""LGPL library for small arms ballistic calculations (Python 3.8+)"""

__author__ = "o-murphy"
__copyright__ = (
    "Copyright 2023 Dmytro Yaroshenko (https://github.com/o-murphy)",
    "Copyright 2024 David Bookstaber (https://github.com/dbookstaber)"
)

__credits__ = ["o-murphy", "dbookstaber"]

from .backend import *
from .drag_tables import *
from .settings import *
from .multiple_bc import *
from .interface import *
from .trajectory_data import *
from .conditions import *
from .munition import *
from .unit import *
