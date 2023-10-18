import unittest


class TestImports(unittest.TestCase):

    def test_bin_import(self):
        try:
            import py_ballisticcalc_exts
        except ImportError as err:
            print(err)
            py_ballisticcalc_exts = None
        if py_ballisticcalc_exts:
            from py_ballisticcalc.backend import DragModel
            print(DragModel)
