"""Run first to ensure binary is run if selected"""
import unittest
#import pyximport; pyximport.install(language_level=3)

class TestImports(unittest.TestCase):

    def test_bin_import(self):
        try:
            import py_ballisticcalc_exts
        except ImportError as err:
            print(err)
            py_ballisticcalc_exts = None
