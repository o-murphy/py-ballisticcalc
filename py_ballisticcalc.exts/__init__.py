try:
	# Normal package import (when used as a subpackage)
	from .py_ballisticcalc_exts import *
except Exception:
	# pytest may import this package as a top-level module during collection;
	# fall back to absolute import of the nested extension package if needed.
	from py_ballisticcalc_exts import *
